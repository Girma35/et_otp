from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import Settings
from app.database import (
    DbSessionMiddleware,
    build_engine,
    build_session_factory,
    close_db,
    init_db,
)
from app.handlers import admin, number, otp, start
from app.logging_config import configure_logging
from app.scheduler import build_scheduler
from app.services.fastx import FastXClient

logger = logging.getLogger(__name__)


async def main() -> None:
    settings = Settings.load()
    configure_logging(settings.log_level)

    bot = Bot(token=settings.bot_token)
    dispatcher = Dispatcher(storage=MemoryStorage())

    engine = build_engine(settings)
    session_factory = build_session_factory(engine)
    fastx = FastXClient(settings)
    scheduler = build_scheduler(bot, session_factory, fastx, settings)

    dispatcher.update.middleware(DbSessionMiddleware(session_factory))
    dispatcher["settings"] = settings
    dispatcher["fastx"] = fastx

    dispatcher.include_router(start.router)
    dispatcher.include_router(number.router)
    dispatcher.include_router(otp.router)
    dispatcher.include_router(admin.router)

    await init_db(engine)
    scheduler.start()
    logger.info("bot_started")

    try:
        await dispatcher.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await fastx.close()
        await close_db(engine)
        await bot.session.close()
        logger.info("bot_stopped")


if __name__ == "__main__":
    asyncio.run(main())
