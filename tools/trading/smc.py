"""Smart Money Concepts (SMC) engine.

Pure price-action detection over candle arrays:
  * BOS / ChoCh market structure with body-close confirmation
  * Fair Value Gaps (FVG) with fill tracking
  * Order Blocks (OB)
  * Liquidity clusters (equal highs / equal lows)
  * Optimal Trade Entry (OTE) via Fibonacci retracement
  * Inducement / liquidity-grab detection
  * ATR-based stop geometry (scalp + swing variants)

Nothing in this module performs I/O — candles are passed in as data.
"""

from __future__ import annotations

from collections import Counter
from typing import Optional

from .indicators import atr


# ── Market structure (BOS / ChoCh) ────────────────────────────────────────────

def detect_bos_choch(candles: list[list[float]], lookback: int = 30) -> dict:
    """Detect break of structure (BOS) and change of character (ChoCh).

    Returns a dict describing the current trend, the latest structural event and
    the surrounding swing points.
    """
    empty = {
        "trend": "ranging", "last_event": None,
        "swing_high": None, "swing_low": None, "mss": False,
        "bos_level": None, "choch_pivot": None,
        "swing_highs": [], "swing_lows": [],
    }
    if len(candles) < 10:
        return empty

    recent = candles[-lookback:]
    highs = [c[2] for c in recent]
    lows = [c[3] for c in recent]
    closes = [c[4] for c in recent]

    n = 2
    swing_highs: list[tuple[int, float]] = []
    swing_lows: list[tuple[int, float]] = []

    for i in range(n, len(highs) - n):
        if all(highs[i] > highs[j] for j in range(i - n, i + n + 1) if j != i):
            swing_highs.append((i, highs[i]))
        if all(lows[i] < lows[j] for j in range(i - n, i + n + 1) if j != i):
            swing_lows.append((i, lows[i]))

    if not swing_highs or not swing_lows:
        empty["swing_highs"] = swing_highs
        empty["swing_lows"] = swing_lows
        return empty

    last_sh_idx, last_sh = swing_highs[-1]
    last_sl_idx, last_sl = swing_lows[-1]

    if len(swing_highs) >= 2 and len(swing_lows) >= 2:
        hh = swing_highs[-1][1] > swing_highs[-2][1]
        hl = swing_lows[-1][1] > swing_lows[-2][1]
        lh = swing_highs[-1][1] < swing_highs[-2][1]
        ll = swing_lows[-1][1] < swing_lows[-2][1]
        if hh and hl:
            trend = "bullish"
        elif lh and ll:
            trend = "bearish"
        else:
            trend = "ranging"
    else:
        trend = "ranging"

    last_event = None
    mss = False
    bos_level = None
    choch_pivot = None

    for ci in range(len(closes) - 1, max(last_sh_idx, last_sl_idx), -1):
        candle_close = closes[ci]
        if candle_close > last_sh:
            if trend == "bullish":
                last_event = "BOS_up"
                bos_level = last_sh
            else:
                last_event = "ChoCh_up"
                mss = True
                bos_level = last_sh
                choch_pivot = last_sl
            break
        if candle_close < last_sl:
            if trend == "bearish":
                last_event = "BOS_down"
                bos_level = last_sl
            else:
                last_event = "ChoCh_down"
                mss = True
                bos_level = last_sl
                choch_pivot = last_sh
            break

    return {
        "trend": trend,
        "last_event": last_event,
        "swing_high": last_sh,
        "swing_low": last_sl,
        "mss": mss,
        "bos_level": bos_level,
        "choch_pivot": choch_pivot,
        "swing_highs": swing_highs,
        "swing_lows": swing_lows,
    }


# Legacy alias used by earlier skill iterations.
detect_market_structure = detect_bos_choch


# ── Fair Value Gap ────────────────────────────────────────────────────────────

def find_fvg(candles: list[list[float]], lookback: int = 20) -> list[dict]:
    """Unfilled fair value gaps (most recent first, capped at 5)."""
    recent = candles[-lookback:]
    fvgs: list[dict] = []
    for i in range(2, len(recent)):
        c0, c1, c2 = recent[i - 2], recent[i - 1], recent[i]
        if c0[2] < c2[3]:
            top, bottom = c2[3], c0[2]
            mid = (top + bottom) / 2
            filled = any(recent[j][3] <= top for j in range(i + 1, len(recent)))
            fvgs.append({"type": "bullish", "top": top, "bottom": bottom,
                         "midpoint": mid, "filled": filled, "bar_index": i})
        elif c0[3] > c2[2]:
            top, bottom = c0[3], c2[2]
            mid = (top + bottom) / 2
            filled = any(recent[j][2] >= bottom for j in range(i + 1, len(recent)))
            fvgs.append({"type": "bearish", "top": top, "bottom": bottom,
                         "midpoint": mid, "filled": filled, "bar_index": i})
    return [f for f in reversed(fvgs) if not f["filled"]][:5]


# Legacy alias used by earlier skill iterations.
detect_fvg = find_fvg


# ── Order Blocks ──────────────────────────────────────────────────────────────

def detect_order_blocks(candles: list[list[float]], lookback: int = 40) -> list[dict]:
    """Unmitigated order blocks (most recent first, capped at 4)."""
    recent = candles[-lookback:]
    obs: list[dict] = []
    current = candles[-1][4]
    for i in range(1, len(recent) - 1):
        c, c_next = recent[i], recent[i + 1]
        body, next_body = abs(c[4] - c[1]), abs(c_next[4] - c_next[1])
        if body == 0:
            continue
        if c[4] < c[1] and c_next[4] > c_next[1] and next_body >= 1.5 * body:
            obs.append({"type": "bullish", "top": c[2], "bottom": c[3],
                        "mitigated": current <= c[2], "bar_index": i})
        elif c[4] > c[1] and c_next[4] < c_next[1] and next_body >= 1.5 * body:
            obs.append({"type": "bearish", "top": c[2], "bottom": c[3],
                        "mitigated": current >= c[3], "bar_index": i})
    return [ob for ob in reversed(obs) if not ob["mitigated"]][:4]


# ── Liquidity clusters ────────────────────────────────────────────────────────

def detect_liquidity(
    candles: list[list[float]],
    tolerance_pct: float = 0.003,
    lookback: int = 40,
) -> dict:
    """Equal highs / equal lows (liquidity pools) around the current price."""
    recent, current = candles[-lookback:], candles[-1][4]
    highs = [c[2] for c in recent]
    lows = [c[3] for c in recent]

    def cluster(values: list[float], above_price: bool) -> list[float]:
        groups: list[float] = []
        for value in values:
            if (above_price and value <= current) or (not above_price and value >= current):
                continue
            if not any(abs(value - group) / group <= tolerance_pct for group in groups):
                groups.append(value)
        buckets = Counter(round(v / (current * tolerance_pct)) for v in groups)
        return sorted(v for v in groups
                      if buckets[round(v / (current * tolerance_pct))] >= 2)

    eqh, eql = cluster(highs, True), cluster(lows, False)
    return {
        "eqh": eqh,
        "eql": eql,
        "nearest_eqh": min(eqh, key=lambda x: abs(x - current)) if eqh else None,
        "nearest_eql": min(eql, key=lambda x: abs(x - current)) if eql else None,
    }


# ── Optimal Trade Entry ───────────────────────────────────────────────────────

def calculate_ote_zone(
    swing_start: float, swing_end: float, direction: str = "bullish"
) -> dict:
    """0.618 / 0.705 / 0.786 retracement of a swing leg (the OTE discount zone)."""
    leg = abs(swing_end - swing_start)
    if leg == 0:
        return {"ote_top": swing_start, "ote_mid": swing_start,
                "ote_bottom": swing_start, "direction": direction}
    if direction == "bullish":
        fib_618, fib_705, fib_786 = (
            swing_end - leg * 0.618, swing_end - leg * 0.705, swing_end - leg * 0.786
        )
        ote_top, ote_mid, ote_bottom = fib_618, fib_705, fib_786
    else:
        fib_618, fib_705, fib_786 = (
            swing_end + leg * 0.618, swing_end + leg * 0.705, swing_end + leg * 0.786
        )
        ote_top, ote_mid, ote_bottom = fib_786, fib_705, fib_618
    return {"ote_top": round(ote_top, 8), "ote_mid": round(ote_mid, 8),
            "ote_bottom": round(ote_bottom, 8), "direction": direction}


# ── Inducement / liquidity grab ───────────────────────────────────────────────

def identify_inducement(
    candles: list[list[float]],
    swing_highs: list[tuple[int, float]],
    swing_lows: list[tuple[int, float]],
    trend: str,
    lookback: int = 40,
) -> list[dict]:
    """LIQUIDITY grabs that swept a swing level and snapped back inside 5 bars."""
    if len(candles) < 10 or len(swing_highs) < 2 or len(swing_lows) < 2:
        return []
    recent = candles[-lookback:]
    results: list[dict] = []
    max_h = max(sh[1] for sh in swing_highs)
    min_l = min(sl[1] for sl in swing_lows)

    if trend in ("bullish", "ranging"):
        for sl_idx, sl_price in swing_lows:
            if sl_price <= min_l:
                continue
            for ci in range(sl_idx + 1, len(recent)):
                if recent[ci][3] < sl_price:
                    snapped_back = any(
                        recent[ri][4] > sl_price
                        for ri in range(ci + 1, min(ci + 6, len(recent)))
                    )
                    if snapped_back:
                        results.append({"type": "bearish_idm", "level": sl_price,
                                        "bar_index": ci, "reversed": True})
                    break

    if trend in ("bearish", "ranging"):
        for sh_idx, sh_price in swing_highs:
            if sh_price >= max_h:
                continue
            for ci in range(sh_idx + 1, len(recent)):
                if recent[ci][2] > sh_price:
                    snapped_back = any(
                        recent[ri][4] < sh_price
                        for ri in range(ci + 1, min(ci + 6, len(recent)))
                    )
                    if snapped_back:
                        results.append({"type": "bullish_idm", "level": sh_price,
                                        "bar_index": ci, "reversed": True})
                    break

    return [r for r in reversed(results) if r["reversed"]][:5]


# ── ATR-based stops ───────────────────────────────────────────────────────────

def calc_atr_stop(
    candles: list[list[float]],
    entry: float,
    direction: str,
    multiplier: float = 1.5,
    period: int = 14,
    max_sl_pct: float = 0.20,
) -> dict:
    """Scalp stop geometry: SL = ATR * multiplier capped at ``max_sl_pct``.

    TP1/TP2/TP3 are fixed multiples of the SL distance (2.0x / 3.5x / 5.0x).
    """
    atr_val = atr(candles, period) or (entry * 0.01)
    sl_distance = min(atr_val * multiplier, entry * max_sl_pct)
    if direction == "LONG":
        sl, tp1, tp2, tp3 = (
            entry - sl_distance,
            entry + sl_distance * 2.0,
            entry + sl_distance * 3.5,
            entry + sl_distance * 5.0,
        )
    else:
        sl, tp1, tp2, tp3 = (
            entry + sl_distance,
            entry - sl_distance * 2.0,
            entry - sl_distance * 3.5,
            entry - sl_distance * 5.0,
        )
    return {
        "sl": round(sl, 8),
        "sl_pct": round(sl_distance / entry, 6),
        "tp1": round(tp1, 8),
        "tp2": round(tp2, 8),
        "tp3": round(tp3, 8),
        "atr_value": round(atr_val, 8),
        "sl_distance": round(sl_distance, 8),
        "trail_dist": round(sl_distance, 8),
    }


def calc_atr_stop_swing(
    klines: list[list[float]],
    entry_price: float,
    direction: str,
    multiplier: float = 2.0,
    period: int = 14,
    max_sl_pct: float = 0.05,
) -> dict:
    """Swing stop geometry — wider ATR multiplier for multi-day holds."""
    if not klines or len(klines) < period * 2:
        sl = entry_price * (1 - max_sl_pct) if direction == "LONG" else entry_price * (1 + max_sl_pct)
        dist = abs(entry_price - sl)
        return {
            "atr_value": None,
            "sl": round(sl, 4),
            "sl_pct": max_sl_pct,
            "tp1": round(entry_price + (dist * 2.0) if direction == "LONG" else entry_price - (dist * 2.0), 4),
            "tp2": round(entry_price + (dist * 3.5) if direction == "LONG" else entry_price - (dist * 3.5), 4),
            "tp3": "Trailing",
        }

    tr_list = []
    for i in range(1, len(klines)):
        high = float(klines[i][2])
        low = float(klines[i][3])
        prev_close = float(klines[i - 1][4])
        tr_list.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))

    atr_val = sum(tr_list[-period:]) / period
    sl_dist = min(atr_val * multiplier, entry_price * max_sl_pct)
    sl = entry_price - sl_dist if direction == "LONG" else entry_price + sl_dist
    return {
        "atr_value": atr_val,
        "sl": round(sl, 4),
        "sl_pct": sl_dist / entry_price,
        "tp1": round(entry_price + (sl_dist * 2.0) if direction == "LONG" else entry_price - (sl_dist * 2.0), 4),
        "tp2": round(entry_price + (sl_dist * 3.5) if direction == "LONG" else entry_price - (sl_dist * 3.5), 4),
        "tp3": "Trailing",
    }


# ── Correlation guard ─────────────────────────────────────────────────────────

def correlation_warning(open_positions: list[str], symbol: str) -> Optional[str]:
    """Warn when the requested symbol overlaps an already-open correlated group."""
    if not open_positions:
        return None

    groups = {
        "MAJORS": {"BTCUSDT", "ETHUSDT", "BNBUSDT"},
        "MEMES": {"DOGEUSDT", "SHIBUSDT", "PEPEUSDT", "WIFUSDT", "BONKUSDT"},
        "AI": {"FETUSDT", "RNDRUSDT", "AGIXUSDT", "NEARUSDT"},
    }

    for group_name, members in groups.items():
        if symbol in members:
            overlap = [pos for pos in open_positions if pos in members]
            if overlap:
                return (
                    f"  ⚠️  CORRELATION WARNING: You already have positions in "
                    f"{group_name} ({', '.join(overlap)}). Diversify or reduce size."
                )
    return None