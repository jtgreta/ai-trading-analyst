"""Binance USD-M Futures API helpers.

A thin, defensive client over the public REST endpoints used across the tool
suite. Every request is retried with exponential backoff and degrades to an
empty payload (``{}`` / ``[]``) instead of raising, so callers can keep working
during transient network problems.

Only public endpoints are used — no API key is required to scan.
"""

from __future__ import annotations

import time
from typing import Any

import requests

from .config import BINANCE_FUTURES

_DEFAULT_TIMEOUT = 10
_BACKOFF_BASE = 1.5


def _get(
    endpoint: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
    retries: int = 3,
    what: str,
) -> Any:
    """GET *endpoint* with retry/backoff. Returns parsed JSON (may be empty)."""
    url = f"{BINANCE_FUTURES}/{endpoint}"
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                time.sleep(_BACKOFF_BASE ** attempt)
        except Exception as exc:  # noqa: BLE001 - network errors must not crash
            if attempt == retries - 1:
                print(f"[api] {what}: {exc}")
    return None


# ── Market data ───────────────────────────────────────────────────────────────

def fetch_klines(
    symbol: str,
    interval: str,
    limit: int = 100,
    retries: int = 3,
    backoff: float = _BACKOFF_BASE,
) -> list[list[float]]:
    """Candlestick data; rows converted to floats, malformed rows dropped."""
    raw = _get(
        "klines",
        params={"symbol": symbol, "interval": interval, "limit": limit},
        timeout=10,
        retries=retries,
        what=f"klines {symbol}/{interval}",
    )
    if not isinstance(raw, list) or not raw:
        return []
    result: list[list[float]] = []
    for row in raw:
        try:
            result.append([float(x) for x in row])
        except (TypeError, ValueError):
            continue
    return result


def fetch_ticker(symbol: str, retries: int = 3) -> dict[str, Any]:
    """24H rolling ticker for a single symbol."""
    data = _get(
        "ticker/24hr",
        params={"symbol": symbol},
        timeout=10,
        retries=retries,
        what=f"ticker {symbol}",
    )
    return data if isinstance(data, dict) else {}


def fetch_all_tickers(retries: int = 3) -> list[dict[str, Any]]:
    """24H rolling tickers for every USD-S perpetual."""
    data = _get("ticker/24hr", timeout=15, retries=retries, what="all tickers")
    return data if isinstance(data, list) else []


def fetch_depth(symbol: str, limit: int = 20) -> dict[str, Any]:
    """Order book snapshot (bids/asks)."""
    data = _get(
        "depth",
        params={"symbol": symbol, "limit": limit},
        timeout=10,
        what=f"depth {symbol}",
    )
    return data if isinstance(data, dict) else {}


# ── Funding ───────────────────────────────────────────────────────────────────

def fetch_funding_rate(symbol: str, retries: int = 3) -> dict[str, Any]:
    """Most recent funding rate record for a symbol."""
    data = _get(
        "fundingRate",
        params={"symbol": symbol, "limit": 1},
        timeout=10,
        retries=retries,
        what=f"funding {symbol}",
    )
    if isinstance(data, list) and data:
        row = data[-1]
        return {
            "symbol": row.get("symbol", symbol),
            "fundingRate": float(row.get("fundingRate", 0)),
            "fundingTime": int(row.get("fundingTime", 0)),
        }
    return {}


def fetch_all_funding_rates(retries: int = 3) -> list[dict[str, Any]]:
    """Latest funding records for every perpetual."""
    data = _get("fundingRate", timeout=15, retries=retries, what="all funding rates")
    if not isinstance(data, list):
        return []
    result: list[dict[str, Any]] = []
    for row in data:
        try:
            result.append(
                {
                    "symbol": row["symbol"],
                    "fundingRate": float(row["fundingRate"]),
                    "fundingTime": int(row.get("fundingTime", 0)),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    return result


# ── Positioning / sentiment ───────────────────────────────────────────────────

def fetch_open_interest(symbol: str, retries: int = 3) -> dict[str, Any]:
    """Open interest (contracts + notional value in USDT)."""
    data = _get(
        "openInterest",
        params={"symbol": symbol},
        timeout=10,
        retries=retries,
        what=f"open interest {symbol}",
    )
    if not isinstance(data, dict):
        return {}
    ticker = fetch_ticker(symbol)
    price = float(ticker.get("lastPrice", 0)) if ticker else 0.0
    oi = float(data.get("openInterest", 0))
    return {
        "symbol": symbol,
        "openInterest": oi,
        "openInterestValue": round(oi * price, 2),
    }


def fetch_ls_ratio(
    symbol: str, period: str = "1h", limit: int = 1, retries: int = 3
) -> dict[str, Any]:
    """Global long/short account ratio (crowd positioning, contrarian signal)."""
    data = _get(
        "globalLongShortAccountRatio",
        params={"symbol": symbol, "period": period, "limit": limit},
        timeout=10,
        retries=retries,
        what=f"LS ratio {symbol}",
    )
    if isinstance(data, list) and data:
        row = data[-1]
        return {
            "longAccount": float(row.get("longAccount", 0)),
            "shortAccount": float(row.get("shortAccount", 0)),
            "longShortRatio": float(row.get("longShortRatio", 1)),
        }
    return {}