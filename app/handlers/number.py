from __future__ import annotations

import logging
import re
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.main import main_menu
from app.models import Number
from app.repositories import get_or_create_user
from app.services.fastx import FastXClient, FastXError
from app.utils import html_escape

logger = logging.getLogger(__name__)
router = Router(name="number")


class GetNumberState(StatesGroup):
    waiting_for_range = State()


@router.message(Command("getnum"))
@router.message(F.text == "📱 Get Number")
async def ask_range(message: Message, state: FSMContext) -> None:
    await state.set_state(GetNumberState.waiting_for_range)
    await message.answer(
        "Send the range prefix.\n\nExample:\n26134XXX",
        reply_markup=main_menu(),
    )


@router.message(GetNumberState.waiting_for_range)
async def receive_range(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    fastx: FastXClient,
) -> None:
    range_prefix = (message.text or "").strip()
    if not _valid_range(range_prefix):
        await message.answer(
            "Invalid range. Use digits and optional X placeholders, for example 26134XXX.",
            reply_markup=main_menu(),
        )
        return

    if message.from_user is None:
        await message.answer("Telegram user data was not available.")
        return

    status_message = await message.answer("Allocating number...")

    try:
        allocated = await fastx.allocate_number(range_prefix)
    except FastXError as exc:
        logger.exception(
            "number_allocation_failed",
            extra={
                "telegram_id": message.from_user.id,
                "range_prefix": range_prefix,
            },
        )
        await status_message.edit_text(f"Allocation failed: {html_escape(exc)}")
        return

    user = await get_or_create_user(session, message.from_user)
    number = Number(
        user_id=user.id,
        phone_number=allocated.phone_number,
        range_prefix=range_prefix,
    )
    session.add(number)
    await session.commit()
    await state.clear()

    await status_message.edit_text(
        "Allocated Number:\n"
        f"<b>{html_escape(allocated.phone_number)}</b>\n\n"
        "Status:\n"
        "Waiting for OTP",
        parse_mode="HTML",
    )


def _valid_range(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9Xx]{3,32}", value))

