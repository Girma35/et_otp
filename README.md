# FastX OTP Telegram Bot

Simple aiogram 3 bot for allocating FastX OTP numbers, polling incoming OTPs, saving history in SQLite, and notifying Telegram users.

## Features

- `/start`, `/help`, `/getnum`, `/mynumbers`, `/otps`, `/status`
- Main menu buttons for get number, inbox, numbers, status, and help
- Admin-only `/stats`, `/users`, `/broadcast`
- SQLite tables created automatically on startup
- FastX API client with structured error logging
- OTP polling every 5 seconds
- Render free web service deployment

## Environment

Create `.env`:

```env
BOT_TOKEN=
FASTX_API_KEY=
ADMIN_ID=
```

Optional settings:

```env
FASTX_BASE_URL=https://fastxotps.com
DATABASE_URL=sqlite+aiosqlite:///./data/bot.sqlite3
OTP_POLL_INTERVAL_SECONDS=5
API_TIMEOUT_SECONDS=20
LOG_LEVEL=INFO
```

`ADMIN_ID` is your numeric Telegram user ID, not the bot token.

## Local Development

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.bot
```

If your system command is `python3` instead of `python3.12`, use:

```bash
python3 -m venv .venv
```

## Production

### Render

Use a Render **Web Service** on the free instance type. The app exposes a tiny health endpoint for Render and runs the Telegram bot polling loop in the same process.

1. Open Render.
2. Create a new Web Service from `https://github.com/Girma35/et_otp`.
3. Use these commands if Render asks manually:
   - Build command: `pip install -r requirements.txt`
   - Start command: `python -m app.bot`
4. Set environment variables:
   - `BOT_TOKEN`
   - `FASTX_API_KEY`
   - `ADMIN_ID`
5. Deploy and open the service logs.

The repo includes `.python-version` with Python `3.12` and `render.yaml` for a native Render web service.

Free Render services can sleep after inactivity. When the service sleeps, Telegram polling stops until Render wakes it again. For always-on OTP delivery, use a paid Render instance, a VPS, or another always-on host.

### VPS

```bash
git clone https://github.com/Girma35/et_otp.git
cd et_otp
cp .env.example .env
nano .env
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.bot
```

## FastX API Mapping

FastX responses can vary. All response parsing is centralized in:

```text
app/services/fastx.py
```

Update these methods after testing real API responses:

- `_extract_phone_number`
- `_extract_items`
- `_extract_raw_message`
- `_extract_otp_code`
- `_extract_received_at`

The bot currently accepts common field names such as `number`, `phone`, `phone_number`, `message`, `otp`, and `code`.

## How To Test

1. Start the bot locally.
2. Open your Telegram bot.
3. Send `/start`.
4. Press `📱 Get Number`.
5. Send a range like `26134XXX`.
6. Check `/mynumbers`.
7. Wait for OTP polling or use `/otps`.
8. Use `/status` to confirm bot/database/FastX status.

## Logging

Logs are JSON lines written to stdout. FastX failures include:

- URL
- status code
- response body
- exception details

Secrets are passed through headers and are not logged.

## GitHub

Remote:

```bash
git remote add origin https://github.com/Girma35/et_otp.git
git branch -M main
git push -u origin main
```
