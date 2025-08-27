from __future__ import annotations

from typing import Iterable, Optional, Tuple

import requests


class UpdatesError(Exception):
    pass


def get_updates(bot_token: str, offset: Optional[int], timeout_seconds: int) -> Tuple[int, list]:
    """Poll Telegram getUpdates.

    Returns: (last_update_id, updates_list)
    """
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    params = {"timeout": timeout_seconds}
    if offset is not None:
        params["offset"] = offset
    response = requests.get(url, params=params, timeout=timeout_seconds + 5)
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise UpdatesError(f"getUpdates failed: {data}")
    updates = data.get("result", [])
    last_id = offset or 0
    for upd in updates:
        if isinstance(upd, dict) and "update_id" in upd:
            if upd["update_id"] > last_id:
                last_id = upd["update_id"]
    # Return next offset (max_id + 1) so callers can pass it back directly
    next_offset = (last_id + 1) if updates else last_id
    return next_offset, updates


def extract_chat_ids_from_updates(updates: Iterable[dict]) -> Tuple[set[int], set[int]]:
    """Return (start_ids, stop_ids) collected from /start and /stop commands."""
    start_ids: set[int] = set()
    stop_ids: set[int] = set()
    for upd in updates:
        message = upd.get("message") if isinstance(upd, dict) else None
        if not isinstance(message, dict):
            continue
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        if not isinstance(chat_id, int):
            continue
        text = message.get("text") or ""
        text = text.strip().lower()
        if text == "/start" or text.startswith("/start@"):
            start_ids.add(chat_id)
        elif text == "/stop" or text.startswith("/stop@"):
            stop_ids.add(chat_id)
    return start_ids, stop_ids


def extract_value_requests(updates: Iterable[dict]) -> set[int]:
    """Return set of chat ids who asked for /value."""
    value_ids: set[int] = set()
    for upd in updates:
        message = upd.get("message") if isinstance(upd, dict) else None
        if not isinstance(message, dict):
            continue
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        if not isinstance(chat_id, int):
            continue
        text = message.get("text") or ""
        text = text.strip().lower()
        if text == "/value" or text.startswith("/value@"):
            value_ids.add(chat_id)
    return value_ids


def parse_threshold_commands(updates: Iterable[dict]):
    """Yield tuples of (chat_id, cmd, args) for threshold-related commands.

    cmd in {"thresholds", "upper", "lower", "settings", "reset", "help"}
    args: list[str]
    """
    for upd in updates:
        message = upd.get("message") if isinstance(upd, dict) else None
        if not isinstance(message, dict):
            continue
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        if not isinstance(chat_id, int):
            continue
        text = (message.get("text") or "").strip()
        if not text.startswith("/"):
            continue
        cmd_and_args = text.split()
        cmd = cmd_and_args[0].lower()
        args = cmd_and_args[1:]
        if cmd == "/thresholds" or cmd.startswith("/thresholds@"):
            yield chat_id, "thresholds", args
        elif cmd == "/upper" or cmd.startswith("/upper@"):
            yield chat_id, "upper", args
        elif cmd == "/lower" or cmd.startswith("/lower@"):
            yield chat_id, "lower", args
        elif cmd == "/settings" or cmd.startswith("/settings@"):
            yield chat_id, "settings", args
        elif cmd == "/reset" or cmd.startswith("/reset@"):
            yield chat_id, "reset", args
        elif cmd == "/help" or cmd.startswith("/help@"):
            yield chat_id, "help", args


