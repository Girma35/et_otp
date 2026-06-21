from __future__ import annotations

from aiogram.types import User as TelegramUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def get_or_create_user(session: AsyncSession, tg_user: TelegramUser) -> User:
    result = await session.execute(
        select(User).where(User.telegram_id == tg_user.id)
    )
    user = result.scalar_one_or_none()

    username = tg_user.username
    if user is not None:
        if user.username != username:
            user.username = username
            await session.flush()
        return user

    user = User(telegram_id=tg_user.id, username=username)
    session.add(user)
    await session.flush()
    return user

