from __future__ import annotations

import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings
from app.database import SessionFactory
from app.models import Number, Otp
from app.services.fastx import FastXClient, FastXError, IncomingOtp
from app.utils import format_utc, html_escape

logger = logging.getLogger(__name__)


def build_scheduler(
    bot: Bot,
    session_factory: SessionFactory,
    fastx: FastXClient,
    settings: Settings,
) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        poll_otps,
        "interval",
        seconds=settings.otp_poll_interval_seconds,
        args=[bot, session_factory, fastx],
        id="otp_polling",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    return scheduler


async def poll_otps(
    bot: Bot,
    session_factory: SessionFactory,
    fastx: FastXClient,
) -> None:
    try:
        incoming_otps = await fastx.fetch_otps()
    except FastXError:
        logger.exception("otp_poll_failed")
        return

    if not incoming_otps:
        logger.info("otp_poll_empty")
        return

    async with session_factory() as session:
        for incoming in incoming_otps:
            try:
                await _store_and_notify(session, bot, incoming)
            except Exception:
                logger.exception(
                    "otp_processing_failed",
                    extra={"phone_number": incoming.phone_number},
                )


async def _store_and_notify(
    session: AsyncSession,
    bot: Bot,
    incoming: IncomingOtp,
) -> None:
    result = await session.execute(
        select(Number)
        .where(Number.phone_number == incoming.phone_number)
        .options(selectinload(Number.user))
        .order_by(Number.created_at.desc())
    )
    number = result.scalars().first()
    if number is None:
        logger.info(
            "otp_for_unknown_number",
            extra={"phone_number": incoming.phone_number},
        )
        return

    otp = Otp(
        number_id=number.id,
        otp_code=incoming.otp_code,
        raw_message=incoming.raw_message,
        received_at=incoming.received_at,
    )
    session.add(otp)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        logger.info(
            "duplicate_otp_skipped",
            extra={
                "phone_number": incoming.phone_number,
                "otp_code": incoming.otp_code,
            },
        )
        return
    except Exception:
        await session.rollback()
        logger.exception(
            "otp_database_write_failed",
            extra={"phone_number": incoming.phone_number},
        )
        return

    try:
        await bot.send_message(
            number.user.telegram_id,
            "🔐 <b>New OTP Received</b>\n\n"
            f"Number:\n{html_escape(number.phone_number)}\n\n"
            f"OTP:\n<b>{html_escape(incoming.otp_code)}</b>\n\n"
            f"Time:\n{format_utc(incoming.received_at)}\n\n"
            f"Message:\n{html_escape(incoming.raw_message)}",
            parse_mode="HTML",
        )
    except Exception:
        logger.exception(
            "telegram_otp_notification_failed",
            extra={
                "telegram_id": number.user.telegram_id,
                "phone_number": incoming.phone_number,
            },
        )
