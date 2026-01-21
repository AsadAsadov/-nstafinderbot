# InstaFinderBot

A production-ready Telegram bot that finds public Instagram profiles and posts using open web search.

## Setup

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Create a `.env` file (or set environment variables):

```bash
BOT_TOKEN=your_telegram_bot_token
ADMIN_ID=6086814445
DB_PATH=/tmp/instafinder.db
PORT=10000
```

3. Run the bot locally:

```bash
python main.py
```

## Environment Variables

- `BOT_TOKEN` (required): Telegram bot token.
- `ADMIN_ID` (optional): Telegram user ID for admin features. Defaults to `6086814445`.
- `DB_PATH` (optional): SQLite database path. Defaults to `/tmp/instafinder.db`.
- `PORT` (optional): Port for the health check server on Render.

## Render Deployment

1. Create a new **Web Service** on Render.
2. Set the **Build Command** to:

```bash
pip install -r requirements.txt
```

3. Set the **Start Command** to:

```bash
python main.py
```

4. Add the environment variables (`BOT_TOKEN`, `ADMIN_ID`, `DB_PATH`).
5. Deploy. The service uses polling and a tiny health server to keep Render happy.
