from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict


@dataclass
class BotState:
    last_zone: str | None  # 'above' | 'below' | 'neutral' | None
    last_value: float | None


def ensure_parent_directory(file_path: str) -> None:
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def read_state(file_path: str) -> BotState:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return BotState(last_zone=data.get("last_zone"), last_value=data.get("last_value"))
    except FileNotFoundError:
        return BotState(last_zone=None, last_value=None)
    except Exception:
        # If the file is corrupted, reset state
        return BotState(last_zone=None, last_value=None)


def write_state(file_path: str, state: BotState) -> None:
    ensure_parent_directory(file_path)
    tmp_path = f"{file_path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(asdict(state), f)
    os.replace(tmp_path, file_path)


