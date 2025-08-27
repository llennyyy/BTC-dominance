## BTC Dominance Alert Bot

A lightweight Telegram bot that checks Bitcoin dominance from CoinGecko and alerts when crossing thresholds. Designed for Raspberry Pi (ARM) and generic Docker hosts.

### Features
- Alerts when BTC dominance goes above/below configured thresholds
- Sends a follow-up when returning to neutral range
- Persists last state to avoid duplicate alerts
- Simple, containerized deployment

### Configuration
Create a `.env` file based on `.env.example`:

```
TELEGRAM_BOT_TOKEN=your_bot_token
# Optional: fallback single chat id; normally not needed with subscriptions
# TELEGRAM_CHAT_ID=your_telegram_user_or_group_id
UPPER_THRESHOLD_PERCENT=55
LOWER_THRESHOLD_PERCENT=45
CHECK_INTERVAL_SECONDS=300
REQUEST_TIMEOUT_SECONDS=15
STATE_FILE_PATH=/app/data/state.json
SUBSCRIBERS_FILE_PATH=/app/data/subscribers.json
```

Notes:
- `TELEGRAM_CHAT_ID`: For a private chat, send a message to your bot and use a tool like `@userinfobot` to get your id, or read updates from `getUpdates` while talking to your bot.
- Thresholds are inclusive: alert triggers when value ≥ upper or ≤ lower.

### Run locally (without Docker)
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.main
```

### Build and run with Docker
```
docker build -t btc-dominance-bot .
docker run --name btc-dominance-bot --restart unless-stopped --env-file .env -v bot_data:/app/data -d btc-dominance-bot
```

### Using docker-compose
```
docker compose up -d --build
```

### Raspberry Pi notes
The provided Dockerfile uses the official `python:3.11-slim` image which supports multi-arch builds. On Apple Silicon or Pi, Docker will select the correct architecture automatically.

### Service behavior
- Polls Telegram for `/start` and `/stop` subscriptions; subscribers stored in `SUBSCRIBERS_FILE_PATH`.
- Users can ask the current value via `/value`; the bot replies immediately.
- Each subscriber can set personal thresholds using `/upper`, `/lower`, or `/thresholds`.
- Polls CoinGecko every `CHECK_INTERVAL_SECONDS` seconds.
- On each check, determines zone: `above`, `neutral`, or `below` based on thresholds.
- Broadcasts to all subscribers only when crossing zones.
- Stores last zone/value in `STATE_FILE_PATH`.

### Troubleshooting
- If you see rate limiting or network errors, the fetcher retries automatically. You can increase `CHECK_INTERVAL_SECONDS`.
- Ensure your bot is started by sending `/start` to it before expecting messages.
- For group chats, make sure the bot is added and has permission to send messages.

### Commands
- `/start` — subscribe to alerts
- `/stop` — unsubscribe
- `/value` — reply with current BTC dominance and your effective thresholds
- `/settings` — show your current thresholds (custom or defaults)
- `/upper <value>` — set your personal upper threshold (0–100)
- `/lower <value>` — set your personal lower threshold (0–100)
- `/thresholds <upper> <lower>` — set both at once
- `/reset` — clear personal thresholds to use global defaults
- `/help` — list available commands

### Logging
- Console logging plus daily rotating file. Configure via `.env`:
```
LOG_FILE_PATH=/app/data/bot.log
LOG_BACKUP_DAYS=365
```
- Logs include user interactions (commands, alerts sent). Old logs auto-delete after retention.


