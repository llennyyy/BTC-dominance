from __future__ import annotations

from typing import Iterable

import requests


class NotifyError(Exception):
    pass


def send_telegram_message(bot_token: str, chat_id: int, text: str, timeout_seconds: int = 15) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    response = requests.post(url, json=payload, timeout=timeout_seconds)
    if response.status_code != 200:
        raise NotifyError(f"Telegram sendMessage failed: {response.status_code} {response.text}")


def broadcast_message(bot_token: str, chat_ids: Iterable[int], text: str, timeout_seconds: int = 15) -> None:
    errors = []
    for cid in chat_ids:
        try:
            send_telegram_message(bot_token, cid, text, timeout_seconds)
        except Exception as e:  # noqa: BLE001
            errors.append((cid, str(e)))
    if errors:
        raise NotifyError(f"Failed to send to {len(errors)} subscribers: {errors}")


