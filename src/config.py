from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Settings:
    telegram_bot_token: str
    telegram_chat_id: Optional[str]
    upper_threshold_percent: float
    lower_threshold_percent: float
    check_interval_seconds: int
    request_timeout_seconds: int
    updates_poll_seconds: int
    state_file_path: str
    subscribers_file_path: str
    log_file_path: str
    log_backup_days: int


def _get_env(name: str, default: Optional[str] = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _get_env_optional(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(name, default)


def load_settings() -> Settings:
    # Optional: load from .env if present, without requiring python-dotenv at runtime
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv()
    except Exception:
        # If python-dotenv is not installed in some environments, continue
        pass

    telegram_bot_token = _get_env("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = _get_env_optional("TELEGRAM_CHAT_ID")

    upper_threshold_percent = float(_get_env("UPPER_THRESHOLD_PERCENT", "55"))
    lower_threshold_percent = float(_get_env("LOWER_THRESHOLD_PERCENT", "45"))
    check_interval_seconds = int(_get_env("CHECK_INTERVAL_SECONDS", "300"))
    request_timeout_seconds = int(_get_env("REQUEST_TIMEOUT_SECONDS", "15"))
    updates_poll_seconds = int(_get_env("UPDATES_POLL_SECONDS", "2"))
    state_file_path = _get_env("STATE_FILE_PATH", "/app/data/state.json")
    subscribers_file_path = _get_env("SUBSCRIBERS_FILE_PATH", "/app/data/subscribers.json")
    log_file_path = _get_env("LOG_FILE_PATH", "/app/data/bot.log")
    log_backup_days = int(_get_env("LOG_BACKUP_DAYS", "365"))

    return Settings(
        telegram_bot_token=telegram_bot_token,
        telegram_chat_id=telegram_chat_id,
        upper_threshold_percent=upper_threshold_percent,
        lower_threshold_percent=lower_threshold_percent,
        check_interval_seconds=check_interval_seconds,
        request_timeout_seconds=request_timeout_seconds,
        updates_poll_seconds=updates_poll_seconds,
        state_file_path=state_file_path,
        subscribers_file_path=subscribers_file_path,
        log_file_path=log_file_path,
        log_backup_days=log_backup_days,
    )


