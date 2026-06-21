from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📱 Get Number"),
                KeyboardButton(text="📨 OTP Inbox"),
            ],
            [
                KeyboardButton(text="📋 My Numbers"),
                KeyboardButton(text="📊 Status"),
            ],
            [KeyboardButton(text="ℹ️ Help")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Choose an action",
    )

