from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import Settings
from app.utils import normalize_phone, utc_now

logger = logging.getLogger(__name__)


class FastXError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class AllocatedNumber:
    phone_number: str
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class IncomingOtp:
    phone_number: str
    otp_code: str
    raw_message: str
    received_at: datetime
    raw: dict[str, Any]


class FastXClient:
    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.fastx_base_url
        self._timeout = settings.api_timeout_seconds
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(self._timeout),
            headers={"X-API-Key": settings.fastx_api_key},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def allocate_number(self, range_prefix: str) -> AllocatedNumber:
        payload = {"range": range_prefix}
        data = await self._request_json("POST", "/api/getnum", json=payload)
        phone_number = self._extract_phone_number(data)
        if not phone_number:
            raise FastXError(
                "FastX getnum response did not contain a phone number. "
                "Update FastXClient._extract_phone_number for the actual JSON shape."
            )
        return AllocatedNumber(phone_number=normalize_phone(phone_number), raw=data)

    async def fetch_otps(self) -> list[IncomingOtp]:
        data = await self._request_json("GET", "/api/otps")
        rows = self._extract_items(data)
        otps: list[IncomingOtp] = []

        for row in rows:
            phone_number = self._extract_phone_number(row)
            raw_message = self._extract_raw_message(row)
            otp_code = self._extract_otp_code(row, raw_message)

            if not phone_number or not raw_message or not otp_code:
                logger.warning(
                    "fastx_otp_row_skipped",
                    extra={"row": row},
                )
                continue

            otps.append(
                IncomingOtp(
                    phone_number=normalize_phone(phone_number),
                    otp_code=otp_code,
                    raw_message=raw_message,
                    received_at=self._extract_received_at(row),
                    raw=row,
                )
            )

        return otps

    async def ping(self) -> None:
        await self._request_json("GET", "/api/liveaccess")

    async def live_access(self) -> dict[str, Any]:
        return await self._request_json("GET", "/api/liveaccess")

    async def console(self) -> dict[str, Any]:
        return await self._request_json("GET", "/api/console")

    async def _request_json(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        try:
            response = await self._client.request(method, path, **kwargs)
            body = response.text
            if response.is_error:
                logger.error(
                    "fastx_request_failed",
                    extra={
                        "url": url,
                        "status_code": response.status_code,
                        "response_body": body,
                    },
                )
                raise FastXError(f"FastX request failed with HTTP {response.status_code}.")

            try:
                data = response.json()
            except ValueError as exc:
                logger.error(
                    "fastx_invalid_json",
                    extra={
                        "url": url,
                        "status_code": response.status_code,
                        "response_body": body,
                    },
                    exc_info=True,
                )
                raise FastXError("FastX returned invalid JSON.") from exc

            if not isinstance(data, dict):
                logger.error(
                    "fastx_unexpected_json_root",
                    extra={
                        "url": url,
                        "status_code": response.status_code,
                        "response_body": body,
                    },
                )
                raise FastXError("FastX returned an unsupported JSON shape.")

            logger.info(
                "fastx_request_ok",
                extra={"url": url, "status_code": response.status_code},
            )
            return data

        except httpx.TimeoutException as exc:
            logger.error(
                "fastx_timeout",
                extra={
                    "url": url,
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                },
                exc_info=True,
            )
            raise FastXError("FastX request timed out.") from exc
        except httpx.HTTPError as exc:
            logger.error(
                "fastx_http_error",
                extra={
                    "url": url,
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                },
                exc_info=True,
            )
            raise FastXError("FastX request failed.") from exc

    def _extract_items(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        for key in ("otps", "data", "items", "messages", "results", "records"):
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

        if all(key in data for key in ("number", "message")):
            return [data]

        return []

    def _extract_phone_number(self, data: dict[str, Any]) -> str | None:
        nested = data.get("data")
        if isinstance(nested, dict):
            nested_number = self._extract_phone_number(nested)
            if nested_number:
                return nested_number

        for key in (
            "phone_number",
            "phone",
            "number",
            "msisdn",
            "mobile",
            "receiver",
            "to",
        ):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, int):
                return str(value)

        return None

    def _extract_raw_message(self, data: dict[str, Any]) -> str | None:
        for key in ("raw_message", "message", "sms", "text", "body", "otp_text"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _extract_otp_code(self, data: dict[str, Any], raw_message: str | None) -> str | None:
        for key in ("otp_code", "otp", "code", "pin"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, int):
                return str(value)

        if raw_message:
            match = re.search(r"\b(\d{4,8})\b", raw_message)
            if match:
                return match.group(1)

        return None

    def _extract_received_at(self, data: dict[str, Any]) -> datetime:
        for key in ("received_at", "time", "timestamp", "created_at", "date"):
            value = data.get(key)
            parsed = self._parse_datetime(value)
            if parsed:
                return parsed
        return utc_now()

    def _parse_datetime(self, value: object) -> datetime | None:
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(float(value), tz=timezone.utc)
            except (OverflowError, ValueError, OSError):
                return None

        if not isinstance(value, str) or not value.strip():
            return None

        cleaned = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(cleaned)
        except ValueError:
            return None

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
