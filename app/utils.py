from __future__ import annotations

import html
import re
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D+", "", value)
    if not digits:
        return value.strip()
    return f"+{digits}"


def html_escape(value: object) -> str:
    return html.escape(str(value), quote=False)


def format_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

