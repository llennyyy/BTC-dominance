from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import Dict, Optional


@dataclass
class Subscriber:
    upper: Optional[float] = None
    lower: Optional[float] = None
    last_zone: Optional[str] = None  # 'above' | 'below' | 'neutral'
    last_value: Optional[float] = None


def _ensure_parent(file_path: str) -> None:
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def read_subscribers(file_path: str) -> Dict[int, Subscriber]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    except Exception:
        return {}

    # Migration: if data is a list of ids -> convert to dict of empty Subscriber
    if isinstance(data, list):
        return {int(cid): Subscriber() for cid in data}

    if isinstance(data, dict):
        result: Dict[int, Subscriber] = {}
        for key, val in data.items():
            try:
                cid = int(key)
            except Exception:
                continue
            if isinstance(val, dict):
                result[cid] = Subscriber(
                    upper=_safe_float(val.get("upper")),
                    lower=_safe_float(val.get("lower")),
                    last_zone=val.get("last_zone"),
                    last_value=_safe_float(val.get("last_value")),
                )
            else:
                result[cid] = Subscriber()
        return result

    return {}


def _safe_float(x):
    try:
        return float(x) if x is not None else None
    except Exception:
        return None


def write_subscribers(file_path: str, subscribers: Dict[int, Subscriber]) -> None:
    _ensure_parent(file_path)
    serializable = {str(cid): asdict(sub) for cid, sub in subscribers.items()}
    tmp_path = f"{file_path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(serializable, f)
    os.replace(tmp_path, file_path)


