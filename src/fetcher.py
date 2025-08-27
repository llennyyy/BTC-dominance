from __future__ import annotations

import time
from typing import Callable, TypeVar

import requests

T = TypeVar("T")


class FetchError(Exception):
    pass


def with_retries(operation: Callable[[], T], attempts: int = 3, backoff_seconds: float = 1.5) -> T:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except Exception as error:  # noqa: BLE001 - propagate as FetchError after retries
            last_error = error
            if attempt < attempts:
                time.sleep(backoff_seconds * attempt)
    raise FetchError(str(last_error) if last_error else "Unknown fetch error")


def fetch_btc_dominance_percent(timeout_seconds: int) -> float:
    """Fetch Bitcoin dominance percentage using CoinGecko global endpoint.

    API: https://api.coingecko.com/api/v3/global
    Response contains: data.market_cap_percentage.bitcoin (e.g., 52.34)
    """

    def _request() -> float:
        response = requests.get(
            "https://api.coingecko.com/api/v3/global",
            timeout=timeout_seconds,
            headers={"Accept": "application/json", "User-Agent": "btc-dominance-bot/1.0"},
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") or {}
        market_caps = data.get("market_cap_percentage") or {}
        btc = market_caps.get("btc") or market_caps.get("bitcoin")
        if btc is None:
            raise FetchError("BTC dominance not found in response")
        return float(btc)

    return with_retries(_request)


