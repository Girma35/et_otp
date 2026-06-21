from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import Number, Otp, User
from app.services.fastx import FastXClient, FastXError
from app.utils import format_utc, html_escape, utc_now

logger = logging.getLogger(__name__)
router = Router(name="admin")


def _is_admin(message: Message, settings: Settings) -> bool:
    return message.from_user is not None and message.from_user.id == settings.admin_id


@router.message(Command("stats"))
async def stats_command(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> None:
    if not _is_admin(message, settings):
        await message.answer("Admin only.")
        return

    users_count = await session.scalar(select(func.count(User.id)))
    numbers_count = await session.scalar(select(func.count(Number.id)))
    otps_count = await session.scalar(select(func.count(Otp.id)))
    recent_count = await session.scalar(
        select(func.count(Otp.id)).where(
            Otp.received_at >= utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
        )
    )

    await message.answer(
        "Stats:\n"
        f"Users: {users_count or 0}\n"
        f"Numbers: {numbers_count or 0}\n"
        f"OTPs: {otps_count or 0}\n"
        f"OTPs today UTC: {recent_count or 0}"
    )


@router.message(Command("users"))
async def users_command(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> None:
    if not _is_admin(message, settings):
        await message.answer("Admin only.")
        return

    result = await session.execute(
        select(User).order_by(desc(User.created_at)).limit(50)
    )
    users = result.scalars().all()

    if not users:
        await message.answer("No users yet.")
        return

    lines = ["Users:"]
    for user in users:
        username = f"@{user.username}" if user.username else "-"
        lines.append(
            f"{user.telegram_id} | {html_escape(username)} | {format_utc(user.created_at)}"
        )

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("broadcast"))
async def broadcast_command(
    message: Message,
    session: AsyncSession,
    settings: Settings,
    bot: Bot,
) -> None:
    if not _is_admin(message, settings):
        await message.answer("Admin only.")
        return

    text = (message.text or "").partition(" ")[2].strip()
    if not text:
        await message.answer("Usage: /broadcast message text")
        return

    result = await session.execute(select(User.telegram_id))
    telegram_ids = result.scalars().all()

    sent = 0
    failed = 0
    for telegram_id in telegram_ids:
        try:
            await bot.send_message(telegram_id, text)
            sent += 1
        except Exception:
            failed += 1
            logger.exception(
                "broadcast_delivery_failed",
                extra={"telegram_id": telegram_id},
            )

    await message.answer(f"Broadcast complete. Sent: {sent}. Failed: {failed}.")


@router.message(Command("fastx"))
async def fastx_command(
    message: Message,
    settings: Settings,
    fastx: FastXClient,
) -> None:
    if not _is_admin(message, settings):
        await message.answer("Admin only.")
        return

    try:
        await fastx.ping()
    except FastXError as exc:
        logger.exception("admin_fastx_check_failed")
        await message.answer(f"FastX check failed: {html_escape(exc)}")
        return

    await message.answer("FastX check OK.")
