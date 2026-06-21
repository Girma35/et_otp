from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.main import main_menu
from app.repositories import get_or_create_user

router = Router(name="start")


HELP_TEXT = (
    "Commands:\n"
    "/start - Open main menu\n"
    "/help - Show help\n"
    "/getnum - Allocate a number by range\n"
    "/mynumbers - View your allocated numbers\n"
    "/otps - View OTP inbox\n"
    "/status - Check bot status\n\n"
    "Admin commands:\n"
    "/stats, /users, /broadcast, /fastx"
)


@router.message(Command("start"))
async def start_command(message: Message, session: AsyncSession) -> None:
    if message.from_user is not None:
        await get_or_create_user(session, message.from_user)
        await session.commit()

    await message.answer(
        "FastX OTP bot is ready.\n\nChoose an action from the menu.",
        reply_markup=main_menu(),
    )


@router.message(Command("help"))
@router.message(lambda message: message.text == "ℹ️ Help")
async def help_command(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=main_menu())
