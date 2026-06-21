from __future__ import annotations

import logging
import os

from aiohttp import web

logger = logging.getLogger(__name__)


async def start_health_server() -> web.AppRunner | None:
    port = os.getenv("PORT")
    if not port:
        return None

    app = web.Application()
    app.router.add_get("/", _health)
    app.router.add_get("/healthz", _health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(port))
    await site.start()

    logger.info("health_server_started", extra={"port": port})
    return runner


async def stop_health_server(runner: web.AppRunner | None) -> None:
    if runner is None:
        return

    await runner.cleanup()
    logger.info("health_server_stopped")


async def _health(_: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})
