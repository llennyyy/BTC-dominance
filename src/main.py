from __future__ import annotations

import logging
import signal
import sys
import time
from typing import Dict, Optional

from src.config import load_settings
from src.fetcher import fetch_btc_dominance_percent
from src.logging_setup import setup_logging
from src.notifier import send_telegram_message
from src.state import BotState, read_state, write_state
from src.subscribers import Subscriber, read_subscribers, write_subscribers
from src.updates import (
    extract_chat_ids_from_updates,
    extract_value_requests,
    get_updates,
    parse_threshold_commands,
)


_running = True


def _handle_signal(signum, frame):  # noqa: ANN001 - standard signal signature
    global _running
    _running = False


def determine_zone(value: float, lower: float, upper: float) -> str:
    if value >= upper:
        return "above"
    if value <= lower:
        return "below"
    return "neutral"


def format_message(value: float, zone: str, lower: float, upper: float) -> str:
    if zone == "above":
        return f"⚠️ BTC dominance crossed ABOVE {upper:.2f}%\nCurrent: {value:.2f}%"
    if zone == "below":
        return f"⚠️ BTC dominance crossed BELOW {lower:.2f}%\nCurrent: {value:.2f}%"
    return f"ℹ️ BTC dominance back between thresholds ({lower:.2f}% - {upper:.2f}%)\nCurrent: {value:.2f}%"


def help_text() -> str:
    return (
        "Commands:\n"
        "/start — subscribe\n"
        "/stop — unsubscribe\n"
        "/value — current BTC dominance\n"
        "/settings — show your thresholds\n"
        "/upper <value> — set your upper (0–100)\n"
        "/lower <value> — set your lower (0–100)\n"
        "/thresholds <upper> <lower> — set both\n"
        "/reset — use global defaults\n"
        "/help — this help"
    )


def main() -> int:
    settings = load_settings()

    setup_logging(settings.log_file_path, settings.log_backup_days)
    log = logging.getLogger(__name__)

    # graceful shutdown
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    state = read_state(settings.state_file_path)
    subscribers: Dict[int, Subscriber] = read_subscribers(settings.subscribers_file_path)
    log.info("starting bot state=%s subscribers=%d", state, len(subscribers))

    last_update_id: Optional[int] = None
    last_value: Optional[float] = state.last_value
    last_zone: Optional[str] = state.last_zone

    next_check_time = time.time()

    while _running:
        try:
            # 1) Poll Telegram updates frequently for commands and interactions
            try:
                offset_param = last_update_id  # get_updates already expects the "next offset"
                last_update_id, updates = get_updates(
                    settings.telegram_bot_token,
                    offset_param,
                    settings.updates_poll_seconds,
                )
                value_ids = set()
                if updates:
                    start_ids, stop_ids = extract_chat_ids_from_updates(updates)
                    value_ids = extract_value_requests(updates)
                    if start_ids:
                        log.info("/start from %s", list(start_ids))
                    if stop_ids:
                        log.info("/stop from %s", list(stop_ids))

                    # Add/remove subscribers
                    changed = False
                    for cid in start_ids:
                        if cid not in subscribers:
                            subscribers[cid] = Subscriber()
                            changed = True
                    for cid in stop_ids:
                        if cid in subscribers:
                            del subscribers[cid]
                            changed = True

                    # Handle threshold and help commands
                    for cid, cmd, args in parse_threshold_commands(updates):
                        if cid not in subscribers:
                            subscribers[cid] = Subscriber()
                            changed = True
                        sub = subscribers[cid]
                        if cmd == "settings":
                            eff_upper = sub.upper if sub.upper is not None else settings.upper_threshold_percent
                            eff_lower = sub.lower if sub.lower is not None else settings.lower_threshold_percent
                            msg = (
                                f"Your thresholds: upper={eff_upper:.2f}%, lower={eff_lower:.2f}%\n"
                                f"Using {'custom' if sub.upper or sub.lower else 'global defaults'}."
                            )
                            try:
                                send_telegram_message(settings.telegram_bot_token, cid, msg, settings.request_timeout_seconds)
                                log.info("/settings replied to %s", cid)
                            except Exception as e:  # noqa: BLE001
                                log.warning("settings send error cid=%s err=%s", cid, repr(e))
                        elif cmd in ("upper", "lower", "thresholds"):
                            try:
                                if cmd == "upper":
                                    if not args:
                                        raise ValueError("Usage: /upper <value>")
                                    val = float(args[0])
                                    if not (0 <= val <= 100):
                                        raise ValueError("Upper must be between 0 and 100")
                                    sub.upper = val
                                elif cmd == "lower":
                                    if not args:
                                        raise ValueError("Usage: /lower <value>")
                                    val = float(args[0])
                                    if not (0 <= val <= 100):
                                        raise ValueError("Lower must be between 0 and 100")
                                    sub.lower = val
                                else:  # thresholds
                                    if len(args) < 2:
                                        raise ValueError("Usage: /thresholds <upper> <lower>")
                                    u = float(args[0])
                                    l = float(args[1])
                                    if not (0 <= u <= 100 and 0 <= l <= 100):
                                        raise ValueError("Values must be between 0 and 100")
                                    sub.upper = u
                                    sub.lower = l
                                eff_upper = sub.upper if sub.upper is not None else settings.upper_threshold_percent
                                eff_lower = sub.lower if sub.lower is not None else settings.lower_threshold_percent
                                if eff_lower >= eff_upper:
                                    raise ValueError("Lower must be less than upper")
                                write_subscribers(settings.subscribers_file_path, subscribers)
                                log.info("saved thresholds for %s -> upper=%s lower=%s", cid, eff_upper, eff_lower)
                                changed = False  # already wrote, avoid extra write
                                send_telegram_message(
                                    settings.telegram_bot_token,
                                    cid,
                                    f"Saved thresholds. upper={eff_upper:.2f}%, lower={eff_lower:.2f}%",
                                    settings.request_timeout_seconds,
                                )
                            except Exception as e:  # noqa: BLE001
                                try:
                                    send_telegram_message(
                                        settings.telegram_bot_token,
                                        cid,
                                        f"Threshold error: {e}",
                                        settings.request_timeout_seconds,
                                    )
                                except Exception:
                                    pass
                                log.warning("threshold cmd error cid=%s cmd=%s args=%s err=%s", cid, cmd, args, repr(e))
                        elif cmd == "reset":
                            sub.upper = None
                            sub.lower = None
                            write_subscribers(settings.subscribers_file_path, subscribers)
                            changed = False
                            try:
                                send_telegram_message(
                                    settings.telegram_bot_token,
                                    cid,
                                    "Your thresholds have been reset to global defaults.",
                                    settings.request_timeout_seconds,
                                )
                                log.info("reset thresholds for %s", cid)
                            except Exception:
                                pass
                        elif cmd == "help":
                            try:
                                send_telegram_message(
                                    settings.telegram_bot_token,
                                    cid,
                                    help_text(),
                                    settings.request_timeout_seconds,
                                )
                                log.info("/help replied to %s", cid)
                            except Exception as e:
                                log.warning("help send error cid=%s err=%s", cid, repr(e))

                    if changed:
                        write_subscribers(settings.subscribers_file_path, subscribers)
                        log.info("subscribers updated -> %d", len(subscribers))
            except Exception as updates_err:  # noqa: BLE001
                logging.getLogger(__name__).warning("updates error: %s", repr(updates_err))
                value_ids = set()

            # 2) If it's time, perform the dominance check and send alerts per user
            now = time.time()
            if now >= next_check_time:
                try:
                    current_value = fetch_btc_dominance_percent(settings.request_timeout_seconds)

                    # Evaluate per-user alerts
                    for cid, sub in list(subscribers.items()):
                        upper = sub.upper if sub.upper is not None else settings.upper_threshold_percent
                        lower = sub.lower if sub.lower is not None else settings.lower_threshold_percent
                        if lower >= upper:
                            # Skip invalid per-user config; notify user once?
                            continue
                        zone = determine_zone(current_value, lower, upper)
                        if zone in ("above", "below") and zone != (sub.last_zone or "neutral"):
                            msg = format_message(current_value, zone, lower, upper)
                            try:
                                send_telegram_message(settings.telegram_bot_token, cid, msg, settings.request_timeout_seconds)
                                log.info("alert to %s zone=%s value=%.2f upper=%.2f lower=%.2f", cid, zone, current_value, upper, lower)
                            except Exception as e:  # noqa: BLE001
                                log.warning("alert send error cid=%s err=%s", cid, repr(e))
                        if zone == "neutral" and (sub.last_zone in ("above", "below")):
                            msg = format_message(current_value, zone, lower, upper)
                            try:
                                send_telegram_message(settings.telegram_bot_token, cid, msg, settings.request_timeout_seconds)
                                log.info("neutral notice to %s value=%.2f", cid, current_value)
                            except Exception as e:  # noqa: BLE001
                                log.warning("alert send error cid=%s err=%s", cid, repr(e))
                        sub.last_zone = zone
                        sub.last_value = current_value

                    # Persist per-user states
                    write_subscribers(settings.subscribers_file_path, subscribers)

                    # Persist global last value/zone for convenience
                    last_value = current_value
                    last_zone = None
                    write_state(settings.state_file_path, BotState(last_zone=None, last_value=last_value))

                    log.info("checked value %.2f for %d subscribers", current_value, len(subscribers))
                finally:
                    next_check_time = now + settings.check_interval_seconds

            # 3) Respond to any /value requests with the most recent known value and per-user thresholds
            if value_ids:
                if last_value is None:
                    try:
                        last_value = fetch_btc_dominance_percent(settings.request_timeout_seconds)
                    except Exception as e:  # noqa: BLE001
                        logging.getLogger(__name__).warning("quick fetch error for /value: %s", repr(e))
                for cid in value_ids:
                    try:
                        sub = subscribers.get(cid) or Subscriber()
                        upper = sub.upper if sub.upper is not None else settings.upper_threshold_percent
                        lower = sub.lower if sub.lower is not None else settings.lower_threshold_percent
                        z = determine_zone(last_value or 0.0, lower, upper) if last_value is not None else "unknown"
                        msg = (
                            f"BTC dominance is {last_value:.2f}% (zone: {z})\n"
                            f"Your thresholds: upper={upper:.2f}%, lower={lower:.2f}%"
                            if last_value is not None
                            else "BTC dominance value not available. Try again shortly."
                        )
                        send_telegram_message(settings.telegram_bot_token, cid, msg, settings.request_timeout_seconds)
                        log.info("/value replied to %s", cid)
                    except Exception as e:  # noqa: BLE001
                        log.warning("/value send error cid=%s err=%s", cid, repr(e))

        except Exception as error:  # noqa: BLE001
            logging.getLogger(__name__).warning("loop error: %s", repr(error))

        # Short sleep between update polls
        for _ in range(settings.updates_poll_seconds):
            if not _running:
                break
            time.sleep(1)

    logging.getLogger(__name__).info("shutting down")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


