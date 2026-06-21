from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


DEFAULT_FASTX_BASE_URL = "https://fastxotps.com"
DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///./data/bot.sqlite3"
DEFAULT_OTP_POLL_INTERVAL_SECONDS = 5
DEFAULT_API_TIMEOUT_SECONDS = 20.0
DEFAULT_LOG_LEVEL = "INFO"


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    fastx_api_key: str
    admin_id: int
    fastx_base_url: str = DEFAULT_FASTX_BASE_URL
    database_url: str = DEFAULT_DATABASE_URL
    otp_poll_interval_seconds: int = DEFAULT_OTP_POLL_INTERVAL_SECONDS
    api_timeout_seconds: float = DEFAULT_API_TIMEOUT_SECONDS
    log_level: str = DEFAULT_LOG_LEVEL

    @classmethod
    def load(cls) -> "Settings":
        load_dotenv()

        bot_token = _required_env("BOT_TOKEN")
        fastx_api_key = _required_env("FASTX_API_KEY")
        admin_id_raw = _required_env("ADMIN_ID")

        try:
            admin_id = int(admin_id_raw)
        except ValueError as exc:
            raise RuntimeError("ADMIN_ID must be a numeric Telegram user ID.") from exc

        return cls(
            bot_token=bot_token,
            fastx_api_key=fastx_api_key,
            admin_id=admin_id,
            fastx_base_url=os.getenv("FASTX_BASE_URL", DEFAULT_FASTX_BASE_URL).rstrip("/"),
            database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
            otp_poll_interval_seconds=int(
                os.getenv(
                    "OTP_POLL_INTERVAL_SECONDS",
                    str(DEFAULT_OTP_POLL_INTERVAL_SECONDS),
                )
            ),
            api_timeout_seconds=float(
                os.getenv("API_TIMEOUT_SECONDS", str(DEFAULT_API_TIMEOUT_SECONDS))
            ),
            log_level=os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper(),
        )


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value
