from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.keyboards.main import main_menu
from app.models import Number, Otp, User
from app.repositories import get_or_create_user
from app.services.fastx import FastXClient, FastXError
from app.utils import format_utc, html_escape

logger = logging.getLogger(__name__)
router = Router(name="otp")


@router.message(Command("mynumbers"))
@router.message(F.text == "📋 My Numbers")
async def my_numbers(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        await message.answer("Telegram user data was not available.")
        return

    user = await get_or_create_user(session, message.from_user)
    result = await session.execute(
        select(Number)
        .where(Number.user_id == user.id)
        .order_by(desc(Number.created_at))
        .limit(20)
    )
    numbers = result.scalars().all()
    await session.commit()

    if not numbers:
        await message.answer(
            "You have no allocated numbers yet. Use /getnum to request one.",
            reply_markup=main_menu(),
        )
        return

    lines = ["Your allocated numbers:"]
    for number in numbers:
        lines.append(
            f"\n<b>{html_escape(number.phone_number)}</b>\n"
            f"Range: {html_escape(number.range_prefix)}\n"
            f"Created: {format_utc(number.created_at)}"
        )

    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=main_menu())


@router.message(Command("otps"))
@router.message(F.text == "📨 OTP Inbox")
async def otp_inbox(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        await message.answer("Telegram user data was not available.")
        return

    user = await get_or_create_user(session, message.from_user)
    result = await session.execute(
        select(Otp)
        .join(Number)
        .where(Number.user_id == user.id)
        .options(selectinload(Otp.number))
        .order_by(desc(Otp.received_at))
        .limit(10)
    )
    otps = result.scalars().all()
    await session.commit()

    if not otps:
        await message.answer(
            "No OTPs yet. New OTPs will be pushed here automatically.",
            reply_markup=main_menu(),
        )
        return

    lines = ["Latest OTPs:"]
    for otp in otps:
        lines.append(
            "\n🔐 <b>OTP</b>\n"
            f"Number: {html_escape(otp.number.phone_number)}\n"
            f"Code: <b>{html_escape(otp.otp_code)}</b>\n"
            f"Time: {format_utc(otp.received_at)}\n"
            f"Message: {html_escape(otp.raw_message)}"
        )

    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=main_menu())


@router.message(Command("status"))
@router.message(F.text == "📊 Status")
async def status(
    message: Message,
    session: AsyncSession,
    fastx: FastXClient,
) -> None:
    users_count = await session.scalar(select(func.count(User.id)))
    numbers_count = await session.scalar(select(func.count(Number.id)))
    otps_count = await session.scalar(select(func.count(Otp.id)))

    api_status = "OK"
    try:
        await fastx.live_access()
    except FastXError:
        logger.exception("fastx_status_check_failed")
        api_status = "FastX check failed"

    await message.answer(
        "Status:\n"
        f"Bot: OK\n"
        f"FastX: {html_escape(api_status)}\n"
        f"Users: {users_count or 0}\n"
        f"Numbers: {numbers_count or 0}\n"
        f"OTPs: {otps_count or 0}",
        reply_markup=main_menu(),
    )

