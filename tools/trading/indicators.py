"""Technical indicators used across the tool suite (pure functions, no I/O).

Candle rows follow the Binance kline layout and are expected to be lists/tuples
where indexes ``2``/``3``/``4``/``5``/``7`` are high/low/close/volume/quote-volume.
"""

from __future__ import annotations

from typing import Optional

CLOSE_IDX = 4


def sma(values: list[float], period: int) -> Optional[float]:
    """Simple moving average of the last ``period`` values."""
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def ema(values: list[float], period: int) -> Optional[float]:
    """Exponential moving average (seed = SMA of the first ``period`` values)."""
    if len(values) < period:
        return None
    k = 2.0 / (period + 1)
    result = sum(values[:period]) / period
    for value in values[period:]:
        result = value * k + result * (1 - k)
    return result


def atr(candles: list[list[float]], period: int = 14) -> Optional[float]:
    """Average True Range; NaN/None-safe over the given candles."""
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, len(candles)):
        high, low = candles[i][2], candles[i][3]
        prev_close = candles[i - 1][4]
        if any(x is None or x != x for x in (high, low, prev_close)):
            continue
        trs.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    if len(trs) < period:
        return None
    return sum(trs[-period:]) / period


def rsi(closes: list[float], period: int = 14) -> Optional[float]:
    """Relative Strength Index (Wilder-style simple average)."""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - 100 / (1 + rs), 2)


def macd(
    closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> dict[str, Optional[float]]:
    """MACD line, signal line and histogram."""
    if len(closes) < slow + signal:
        return {"macd": None, "signal": None, "hist": None}

    macd_line = (ema(closes, fast) or 0.0) - (ema(closes, slow) or 0.0)

    # Reconstruct a small running history of MACD values for the signal line.
    macd_series = []
    for i in range(signal + 5, 0, -1):
        sub = closes[:-i] if i > 0 else closes
        ef = ema(sub, fast)
        es = ema(sub, slow)
        if ef is not None and es is not None:
            macd_series.append(ef - es)

    signal_line = ema(macd_series, signal) if len(macd_series) >= signal else None
    hist = (macd_line - signal_line) if signal_line is not None else None
    return {"macd": macd_line, "signal": signal_line, "hist": hist}


def detect_divergence(candles: list[list[float]], lookback: int = 40) -> dict[str, Optional[str]]:
    """RSI divergence between price action and momentum.

    Bullish: price makes a lower low while RSI prints a higher low.
    Bearish: price makes a higher high while RSI prints a lower high.
    """
    if len(candles) < lookback + 15:
        return {"type": "none", "rsi_now": None}

    closes = [c[4] for c in candles]
    rsi_vals: list[Optional[float]] = []
    for i in range(len(closes) - lookback, len(closes)):
        window = closes[i - 14 : i]
        if len(window) < 14:
            rsi_vals.append(None)
            continue
        gains = [max(window[j] - window[j - 1], 0) for j in range(1, len(window))]
        losses = [max(window[j - 1] - window[j], 0) for j in range(1, len(window))]
        avg_gain = sum(gains) / 13
        avg_loss = sum(losses) / 13
        rs = avg_gain / avg_loss if avg_loss != 0 else 100
        rsi_vals.append(round(100 - 100 / (1 + rs), 2))

    rsi_now = rsi_vals[-1]
    price_now = closes[-1]

    # Bullish divergence: lower price low but higher RSI low.
    price_low = min(closes[-lookback:])
    rsi_low = min((v for v in rsi_vals if v is not None), default=100)
    if rsi_now is not None and price_now > price_low and rsi_now > rsi_low and rsi_now < 40:
        return {"type": "bullish", "rsi_now": rsi_now}

    # Bearish divergence: higher price high but lower RSI high.
    price_high = max(closes[-lookback:])
    rsi_high = max((v for v in rsi_vals if v is not None), default=0)
    if rsi_now is not None and price_now < price_high and rsi_now < rsi_high and rsi_now > 60:
        return {"type": "bearish", "rsi_now": rsi_now}

    return {"type": "none", "rsi_now": rsi_now}


def ma_stack_label(
    price: float,
    ma5: Optional[float],
    ma10: Optional[float],
    ma20: Optional[float],
) -> str:
    """Label for MA-stack alignment: Bullish, Bearish, or Mixed."""
    if ma5 is None or ma10 is None or ma20 is None:
        return "Mixed"
    if price > ma5 > ma10 > ma20:
        return "Bullish"
    if price < ma5 < ma10 < ma20:
        return "Bearish"
    return "Mixed"


# ── Price math ────────────────────────────────────────────────────────────────

def pct_from(price: float, ref: float) -> float:
    """Percent change from ``ref`` to ``price``."""
    return (price - ref) / ref * 100 if ref != 0 else 0.0


def distance_pct(price: float, level: float) -> float:
    """Distance from ``price`` to ``level`` as a % of ``price``."""
    return abs(price - level) / price * 100 if price != 0 else 0.0


# ── Trailing geometry ─────────────────────────────────────────────────────────

def calc_trail_callback_pct(
    atr_val: Optional[float], entry: float, tok_type: str = "midcap"
) -> float:
    """Trailing-stop callback as a % of price, derived from ATR and token class."""
    if atr_val is None or entry == 0:
        return 3.0
    base_pct = (atr_val / entry) * 100
    mult = {"major": 1.0, "midcap": 1.5, "new": 2.0}.get(tok_type, 1.5)
    return round(min(max(base_pct * mult, 1.0), 7.0), 2)