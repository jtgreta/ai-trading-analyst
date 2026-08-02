"""
trading_utils.py — Institutional Trading Utilities
Shared by all skills: scanner, scalper, hunter, swing, bias, funding, manage, journal.
DO NOT import any local skill files here.

Implements:
  - API helpers with retry + NaN guard
  - ATR-based volatility stops
  - SMC: BOS / ChoCh with body-close confirmation
  - SMC: Fair Value Gap (FVG) detection with fill tracking
  - SMC: Order Block identification
  - SMC: Optimal Trade Entry (OTE) via Fibonacci retracement
  - SMC: Inducement / Liquidity Grab detection
  - SMC: Liquidity (Equal Highs / Equal Lows)
  - RSI + MACD divergence
  - Token classification + dynamic position sizing
  - Institutional Telegram dispatch
  - Mandatory 4-Section Output Format (Session, Structure, Plan/Waiting, Telegram)
"""

import requests
import time
import os
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta

# ── Constants ──────────────────────────────────────────────────────────────────
BINANCE_FUTURES = "https://fapi.binance.com/fapi/v1"
CAPITAL         = 100.0
MAX_RISK        = 4.0          # Hard max dollar risk per trade
MIN_RR          = 2.0          # Minimum risk:reward ratio (TP1 >= 2x SL distance)

def _load_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip("'").strip('"'))
_load_env()

TG_TOKEN        = os.environ.get("TG_TOKEN", "")
TG_CHAT         = os.environ.get("TG_CHAT", "")

MAJOR_SYMBOLS   = {"BTCUSDT", "ETHUSDT", "BNBUSDT"}
EXCLUDE_SUBS    = ["USDC", "BUSD", "TUSD", "DAI", "FDUSD"]
EXCLUDE_EXACT   = {"BTCDOMUSDT", "DEFIUSDT", "ALTUSDT"}

# Scalp rules — (leverage, margin, max_sl_pct)
SCALP_RULES = {
    "major":  {"lev": 10, "margin": 10, "max_sl": 0.030, "label": "BTC/ETH/BNB"},
    "midcap": {"lev":  5, "margin":  7, "max_sl": 0.085, "label": "Mid-cap"},
    "new":    {"lev":  3, "margin":  5, "max_sl": 0.200, "label": "New/Meme/AI"},
}
# Swing rules
SWING_RULES = {
    "major":  {"lev":  5, "margin": 10, "max_sl": 0.060, "label": "BTC/ETH/BNB"},
    "midcap": {"lev":  3, "margin":  7, "max_sl": 0.140, "label": "Mid-cap"},
    "new":    {"lev":  2, "margin":  5, "max_sl": 0.300, "label": "New/Meme/AI"},
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def fetch_klines(symbol: str, interval: str, limit: int = 100,
                 retries: int = 3, backoff: float = 1.5) -> list:
    url = f"{BINANCE_FUTURES}/klines"
    for attempt in range(retries):
        try:
            r = requests.get(url, params={"symbol": symbol, "interval": interval,
                                           "limit": limit}, timeout=10)
            r.raise_for_status()
            raw = r.json()
            if not isinstance(raw, list) or len(raw) == 0:
                return []
            result = []
            for row in raw:
                try:
                    result.append([float(x) for x in row])
                except (ValueError, TypeError):
                    continue
            return result
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                time.sleep(backoff ** attempt)
        except Exception as e:
            if attempt == retries - 1:
                print(f"  [utils] klines {symbol}/{interval}: {e}")
    return []

def fetch_ticker(symbol: str, retries: int = 3) -> dict:
    url = f"{BINANCE_FUTURES}/ticker/24hr"
    for attempt in range(retries):
        try:
            r = requests.get(url, params={"symbol": symbol}, timeout=10)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                time.sleep(1.5 ** attempt)
        except Exception as e:
            if attempt == retries - 1:
                print(f"  [utils] ticker {symbol}: {e}")
    return {}

def fetch_all_tickers(retries: int = 3) -> list:
    url = f"{BINANCE_FUTURES}/ticker/24hr"
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                time.sleep(1.5 ** attempt)
        except Exception as e:
            if attempt == retries - 1:
                print(f"  [utils] all tickers: {e}")
    return []

def fetch_depth(symbol: str, limit: int = 20) -> dict:
    url = f"{BINANCE_FUTURES}/depth"
    try:
        r = requests.get(url, params={"symbol": symbol, "limit": limit}, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  [utils] depth {symbol}: {e}")
    return {}

def fetch_funding_rate(symbol: str, retries: int = 3) -> dict:
    url = f"{BINANCE_FUTURES}/fundingRate"
    for attempt in range(retries):
        try:
            r = requests.get(url, params={"symbol": symbol, "limit": 1}, timeout=10)
            r.raise_for_status()
            data = r.json()
            if data and isinstance(data, list):
                row = data[-1]
                return {
                    "symbol":      row.get("symbol", symbol),
                    "fundingRate": float(row.get("fundingRate", 0)),
                    "fundingTime": int(row.get("fundingTime", 0)),
                }
            return {}
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                time.sleep(1.5 ** attempt)
        except Exception as e:
            if attempt == retries - 1:
                print(f"  [utils] funding {symbol}: {e}")
    return {}

def fetch_all_funding_rates(retries: int = 3) -> list:
    url = f"{BINANCE_FUTURES}/fundingRate"
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, list):
                return []
            result = []
            for row in data:
                try:
                    result.append({
                        "symbol":      row["symbol"],
                        "fundingRate": float(row["fundingRate"]),
                        "fundingTime": int(row.get("fundingTime", 0)),
                    })
                except Exception:
                    continue
            return result
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                time.sleep(1.5 ** attempt)
        except Exception as e:
            if attempt == retries - 1:
                print(f"  [utils] all funding rates: {e}")
    return []

def fetch_open_interest(symbol: str, retries: int = 3) -> dict:
    url = f"{BINANCE_FUTURES}/openInterest"
    for attempt in range(retries):
        try:
            r = requests.get(url, params={"symbol": symbol}, timeout=10)
            r.raise_for_status()
            data = r.json()
            price_data = fetch_ticker(symbol)
            price = float(price_data.get("lastPrice", 0)) if price_data else 0
            oi    = float(data.get("openInterest", 0))
            return {
                "symbol":            symbol,
                "openInterest":      oi,
                "openInterestValue": round(oi * price, 2),
            }
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                time.sleep(1.5 ** attempt)
        except Exception as e:
            if attempt == retries - 1:
                print(f"  [utils] open interest {symbol}: {e}")
    return {}

def fetch_ls_ratio(symbol: str, period: str = "1h",
                   limit: int = 1, retries: int = 3) -> dict:
    url = f"{BINANCE_FUTURES}/globalLongShortAccountRatio"
    for attempt in range(retries):
        try:
            r = requests.get(url, params={"symbol": symbol, "period": period,
                                           "limit": limit}, timeout=10)
            r.raise_for_status()
            data = r.json()
            if data and isinstance(data, list):
                row = data[-1]
                return {
                    "longAccount":    float(row.get("longAccount", 0)),
                    "shortAccount":   float(row.get("shortAccount", 0)),
                    "longShortRatio": float(row.get("longShortRatio", 1)),
                }
            return {}
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                time.sleep(1.5 ** attempt)
        except Exception as e:
            if attempt == retries - 1:
                print(f"  [utils] LS ratio {symbol}: {e}")
    return {}

def send_telegram(msg: str):
    try:
        if len(msg) > 4096:
            msg = msg[:4093] + "..."
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            data={"chat_id": TG_CHAT, "text": msg},
            timeout=10
        )
        print(f"  ✅ Telegram sent ({len(msg)} chars)")
    except Exception as e:
        print(f"  ⚠️  Telegram failed: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TOKEN CLASSIFICATION + POSITION SIZING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def classify_token(symbol: str, quote_vol: float) -> str:
    if symbol in MAJOR_SYMBOLS:
        return "major"
    if quote_vol > 500_000_000:
        return "midcap"
    return "new"

def calc_position(tok_type: str, sl_pct: float, mode: str = "scalp",
                  setup_grade: str = "B") -> dict:
    """
    Dynamic position sizing based on setup grade.
    Grade A  → full margin
    Grade B  → half margin
    Grade C  → blocked (handled by skill as Waiting Room)
    """
    rules = SCALP_RULES if mode == "scalp" else SWING_RULES
    base = rules[tok_type]

    # Grade Multiplier (A=100%, B=50%, C=0% - C is typically handled as Waiting Room)
    grade_mult = {"A": 1.0, "B": 0.50, "C": 0.0}.get(setup_grade, 0.50)
    
    # Calculate margin based on grade
    margin = round(base["margin"] * grade_mult, 2)
    
    lev      = base["lev"]
    position = round(margin * lev, 2)
    risk     = round(position * sl_pct, 2)

    # Hard risk cap: if computed risk > MAX_RISK, shrink margin
    if risk > MAX_RISK:
        # margin = MAX_RISK / (leverage * sl_pct)
        margin   = round(MAX_RISK / (lev * sl_pct), 2)
        position = round(margin * lev, 2)
        risk     = round(position * sl_pct, 2)

    return {
        "lev": lev, "margin": margin, "position": position,
        "risk": risk, "label": base["label"], "grade": setup_grade
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BASIC INDICATORS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def ma_stack_label(price: float, ma5: Optional[float], ma10: Optional[float], ma20: Optional[float]) -> str:
    """Returns a label for the MA stack alignment (Bullish, Bearish, or Mixed)."""
    if ma5 is None or ma10 is None or ma20 is None:
        return "Mixed"
    if price > ma5 > ma10 > ma20:
        return "Bullish"
    if price < ma5 < ma10 < ma20:
        return "Bearish"
    return "Mixed"

def sma(values: list, period: int) -> Optional[float]:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period

def ema(values: list, period: int) -> Optional[float]:
    if len(values) < period:
        return None
    k = 2.0 / (period + 1)
    result = sum(values[:period]) / period
    for v in values[period:]:
        result = v * k + result * (1 - k)
    return result

def atr(candles: list, period: int = 14) -> Optional[float]:
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, len(candles)):
        h = candles[i][2]
        l = candles[i][3]
        pc = candles[i - 1][4]
        if any(x is None or x != x for x in [h, l, pc]):
            continue
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    if len(trs) < period:
        return None
    return sum(trs[-period:]) / period

def rsi(closes: list, period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - 100 / (1 + rs), 2)

def macd(closes: list, fast: int = 12, slow: int = 26,
         signal: int = 9) -> dict:
    if len(closes) < slow + signal:
        return {"macd": None, "signal": None, "hist": None}
    ema_fast   = ema(closes, fast)
    ema_slow   = ema(closes, slow)
    if ema_fast is None or ema_slow is None:
        return {"macd": None, "signal": None, "hist": None}
    macd_line  = ema_fast - ema_slow
    macd_hist_vals = []
    for i in range(signal + 5, 0, -1):
        sub = closes[:-i] if i > 0 else closes
        ef  = ema(sub, fast)
        es  = ema(sub, slow)
        if ef and es:
            macd_hist_vals.append(ef - es)
    signal_line = ema(macd_hist_vals, signal) if len(macd_hist_vals) >= signal else None
    hist        = (macd_line - signal_line) if signal_line is not None else None
    return {"macd": macd_line, "signal": signal_line, "hist": hist}


def detect_divergence(candles: list, lookback: int = 40) -> dict:
    """
    Detects RSI divergence between price action and momentum.
    Bullish: Price Lower Low, RSI Higher Low.
    Bearish: Price Higher High, RSI Lower High.
    """
    if len(candles) < lookback + 15:
        return {"type": "none", "rsi_now": None}
    
    closes = [c[4] for c in candles]
    rsi_vals = []
    for i in range(len(closes) - lookback, len(closes)):
        # Calculate RSI for the window ending at index i
        window = closes[i - 14 : i]
        if len(window) < 14:
            rsi_vals.append(None)
            continue
        gains, losses = [], []
        for j in range(1, len(window)):
            diff = window[j] - window[j-1]
            gains.append(max(diff, 0))
            losses.append(max(-diff, 0))
        avg_gain = sum(gains) / 13
        avg_loss = sum(losses) / 13
        rs = avg_gain / avg_loss if avg_loss != 0 else 100
        rsi_vals.append(round(100 - 100 / (1 + rs), 2))
    
    rsi_now = rsi_vals[-1]
    price_now = closes[-1]
    
    # Look for structural lows/highs in the lookback window
    # Bullish Divergence
    price_low = min(closes[-lookback:])
    rsi_low = min([v for v in rsi_vals if v is not None], default=100)
    if price_now > price_low and rsi_now > rsi_low and rsi_now < 40:
        return {"type": "bullish", "rsi_now": rsi_now}
    
    # Bearish Divergence
    price_high = max(closes[-lookback:])
    rsi_high = max([v for v in rsi_vals if v is not None], default=0)
    if price_now < price_high and rsi_now < rsi_high and rsi_now > 60:
        return {"type": "bearish", "rsi_now": rsi_now}
        
    return {"type": "none", "rsi_now": rsi_now}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SMC — MARKET STRUCTURE (BOS / ChoCh with body-close confirmation)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def detect_bos_choch(candles: list, lookback: int = 30) -> dict:
    empty = {
        "trend": "ranging", "last_event": None,
        "swing_high": None, "swing_low": None, "mss": False,
        "bos_level": None, "choch_pivot": None,
        "swing_highs": [], "swing_lows": [],
    }
    if len(candles) < 10:
        return empty

    recent = candles[-lookback:]
    highs  = [c[2] for c in recent]
    lows   = [c[3] for c in recent]
    closes = [c[4] for c in recent]

    n = 2
    swing_highs: list[tuple[int, float]] = []
    swing_lows:  list[tuple[int, float]] = []

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
        hl = swing_lows[-1][1]  > swing_lows[-2][1]
        lh = swing_highs[-1][1] < swing_highs[-2][1]
        ll = swing_lows[-1][1]  < swing_lows[-2][1]
        if hh and hl:
            trend = "bullish"
        elif lh and ll:
            trend = "bearish"
        else:
            trend = "ranging"
    else:
        trend = "ranging"

    last_event   = None
    mss          = False
    bos_level    = None
    choch_pivot  = None

    for ci in range(len(closes) - 1, max(last_sh_idx, last_sl_idx), -1):
        candle_close = closes[ci]
        if candle_close > last_sh:
            if trend == "bullish":
                last_event = "BOS_up"
                bos_level  = last_sh
            else:
                last_event  = "ChoCh_up"
                mss         = True
                bos_level   = last_sh
                choch_pivot = last_sl
            break
        if candle_close < last_sl:
            if trend == "bearish":
                last_event = "BOS_down"
                bos_level  = last_sl
            else:
                last_event  = "ChoCh_down"
                mss         = True
                bos_level   = last_sl
                choch_pivot = last_sh
            break

    return {
        "trend":       trend,
        "last_event":  last_event,
        "swing_high":  last_sh,
        "swing_low":   last_sl,
        "mss":         mss,
        "bos_level":   bos_level,
        "choch_pivot": choch_pivot,
        "swing_highs": swing_highs,
        "swing_lows":  swing_lows,
    }

detect_market_structure = detect_bos_choch


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SMC — FAIR VALUE GAP (FVG)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def find_fvg(candles: list, lookback: int = 20) -> list:
    recent  = candles[-lookback:]
    fvgs    = []
    for i in range(2, len(recent)):
        c0, c1, c2 = recent[i - 2], recent[i - 1], recent[i]
        if c0[2] < c2[3]:
            top, bottom = c2[3], c0[2]
            mid = (top + bottom) / 2
            filled = False
            for j in range(i + 1, len(recent)):
                if recent[j][3] <= top:
                    filled = True
                    break
            fvgs.append({"type": "bullish", "top": top, "bottom": bottom, "midpoint": mid, "filled": filled, "bar_index": i})
        elif c0[3] > c2[2]:
            top, bottom = c0[3], c2[2]
            mid = (top + bottom) / 2
            filled = False
            for j in range(i + 1, len(recent)):
                if recent[j][2] >= bottom:
                    filled = True
                    break
            fvgs.append({"type": "bearish", "top": top, "bottom": bottom, "midpoint": mid, "filled": filled, "bar_index": i})
    return [f for f in reversed(fvgs) if not f["filled"]][:5]

detect_fvg = find_fvg


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SMC — ORDER BLOCKS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def detect_order_blocks(candles: list, lookback: int = 40) -> list:
    recent   = candles[-lookback:]
    obs      = []
    current  = candles[-1][4]
    for i in range(1, len(recent) - 1):
        c, c_next = recent[i], recent[i+1]
        body, next_body = abs(c[4] - c[1]), abs(c_next[4] - c_next[1])
        if body == 0: continue
        if c[4] < c[1] and c_next[4] > c_next[1] and next_body >= 1.5 * body:
            obs.append({"type": "bullish", "top": c[2], "bottom": c[3], "mitigated": current <= c[2], "bar_index": i})
        elif c[4] > c[1] and c_next[4] < c_next[1] and next_body >= 1.5 * body:
            obs.append({"type": "bearish", "top": c[2], "bottom": c[3], "mitigated": current >= c[3], "bar_index": i})
    return [ob for ob in reversed(obs) if not ob["mitigated"]][:4]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SMC — LIQUIDITY (EQH / EQL)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def detect_liquidity(candles: list, tolerance_pct: float = 0.003, lookback: int = 40) -> dict:
    recent, current = candles[-lookback:], candles[-1][4]
    highs, lows = [c[2] for c in recent], [c[3] for c in recent]
    def cluster(values, above_price):
        groups = []
        for v in values:
            if (above_price and v <= current) or (not above_price and v >= current): continue
            merged = False
            for grp in groups:
                if abs(v - grp) / grp <= tolerance_pct:
                    merged = True; break
            if not merged: groups.append(v)
        from collections import Counter
        c = Counter([round(v / (current * tolerance_pct)) for v in groups])
        return sorted([v for v in groups if c[round(v / (current * tolerance_pct))] >= 2])
    eqh, eql = cluster(highs, True), cluster(lows, False)
    return {
        "eqh": eqh, "eql": eql,
        "nearest_eqh": min(eqh, key=lambda x: abs(x - current)) if eqh else None,
        "nearest_eql": min(eql, key=lambda x: abs(x - current)) if eql else None,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SMC — OTE ZONE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def calculate_ote_zone(swing_start: float, swing_end: float, direction: str = "bullish") -> dict:
    leg = abs(swing_end - swing_start)
    if leg == 0: return {"ote_top": swing_start, "ote_mid": swing_start, "ote_bottom": swing_start, "direction": direction}
    if direction == "bullish":
        fib_618, fib_705, fib_786 = swing_end - leg * 0.618, swing_end - leg * 0.705, swing_end - leg * 0.786
        ote_top, ote_mid, ote_bottom = fib_618, fib_705, fib_786
    else:
        fib_618, fib_705, fib_786 = swing_end + leg * 0.618, swing_end + leg * 0.705, swing_end + leg * 0.786
        ote_top, ote_mid, ote_bottom = fib_786, fib_705, fib_618
    return {"ote_top": round(ote_top, 8), "ote_mid": round(ote_mid, 8), "ote_bottom": round(ote_bottom, 8), "direction": direction}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SMC — INDUCEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def identify_inducement(candles: list, swing_highs: list, swing_lows: list, trend: str, lookback: int = 40) -> list:
    if len(candles) < 10 or len(swing_highs) < 2 or len(swing_lows) < 2: return []
    recent = candles[-lookback:]
    results = []
    max_h, min_l = max(sh[1] for sh in swing_highs), min(sl[1] for sl in swing_lows)
    if trend in ("bullish", "ranging"):
        for sl_idx, sl_price in swing_lows:
            if sl_price <= min_l: continue
            for ci in range(sl_idx + 1, len(recent)):
                if recent[ci][3] < sl_price:
                    reversed_back = any(recent[ri][4] > sl_price for ri in range(ci + 1, min(ci + 6, len(recent))))
                    if reversed_back: results.append({"type": "bearish_idm", "level": sl_price, "bar_index": ci, "reversed": True})
                    break
    if trend in ("bearish", "ranging"):
        for sh_idx, sh_price in swing_highs:
            if sh_price >= max_h: continue
            for ci in range(sh_idx + 1, len(recent)):
                if recent[ci][2] > sh_price:
                    reversed_back = any(recent[ri][4] < sh_price for ri in range(ci + 1, min(ci + 6, len(recent))))
                    if reversed_back: results.append({"type": "bullish_idm", "level": sh_price, "bar_index": ci, "reversed": True})
                    break
    return [r for r in reversed(results) if r["reversed"]][:5]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ATR-BASED STOP LOGIC
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def calc_atr_stop(candles: list, entry: float, direction: str, multiplier: float = 1.5, period: int = 14, max_sl_pct: float = 0.20) -> dict:
    atr_val = atr(candles, period) or (entry * 0.01)
    sl_distance = min(atr_val * multiplier, entry * max_sl_pct)
    if direction == "LONG":
        sl, tp1, tp2, tp3 = entry - sl_distance, entry + sl_distance * 2.0, entry + sl_distance * 3.5, entry + sl_distance * 5.0
    else:
        sl, tp1, tp2, tp3 = entry + sl_distance, entry - sl_distance * 2.0, entry - sl_distance * 3.5, entry - sl_distance * 5.0
    return {"sl": round(sl, 8), "sl_pct": round(sl_distance / entry, 6), "tp1": round(tp1, 8), "tp2": round(tp2, 8), "tp3": round(tp3, 8), "atr_value": round(atr_val, 8), "sl_distance": round(sl_distance, 8), "trail_dist": round(sl_distance, 8)}


def correlation_warning(open_positions: list, symbol: str) -> Optional[str]:
    """
    Warns the user if they are already heavily exposed to the same or highly correlated coins.
    Example: If longing BTC and trying to long ETH.
    """
    if not open_positions:
        return None
    
    # Basic correlation groups
    groups = {
        "MAJORS": {"BTCUSDT", "ETHUSDT", "BNBUSDT"},
        "MEMES": {"DOGEUSDT", "SHIBUSDT", "PEPEUSDT", "WIFUSDT", "BONKUSDT"},
        "AI": {"FETUSDT", "RNDRUSDT", "AGIXUSDT", "NEARUSDT"},
    }
    
    for group_name, members in groups.items():
        if symbol in members:
            overlap = [pos for pos in open_positions if pos in members]
            if overlap:
                return f"  ⚠️  CORRELATION WARNING: You already have positions in {group_name} ({', '.join(overlap)}). Diversify or reduce size."
    
    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FORMATTING HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def fmt(price: float) -> str:
    if price is None: return "N/A"
    if price >= 1000: return f"{price:,.2f}"
    if price >= 1: return f"{price:.4f}"
    if price >= 0.01: return f"{price:.5f}"
    return f"{price:.8f}"

def grade_label(grade: str) -> str:
    return {"A": "🏆 Grade A (Full)", "B": "✅ Grade B (Half)", "C": "⚡ Grade C (Waiting)"}.get(grade, grade)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SESSION TIMING (PHT / UTC+8)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PHT = timezone(timedelta(hours=8))

def get_session_info() -> dict:
    now = datetime.now(PHT)
    h, m = now.hour, now.minute
    t = h * 60 + m
    time_str = now.strftime("%Y-%m-%d %H:%M PHT")
    
    # Volatility Adaptive Mapping
    # Prime: London Open (3-5 PM) and NY Overlap (9:30 PM - 12 AM)
    # Secondary: London-NY Gap (5-9 PM)
    # Low: Asian Session (8 AM - 12 PM) and Off-hours (12 AM - 3 PM)
    
    if 900 <= t < 1020: # London Open
        return {"time_str": time_str, "window": "London Open", "volatility": "🟢 High", "aggression": "Maximum", "advice": "Prime Window. High probability of impulsive, trending moves.", "can_enter": True, "min_grade": "B"}
    elif 1290 <= t < 1440: # NY Overlap
        return {"time_str": time_str, "window": "NY Overlap", "volatility": "🟢 High", "aggression": "Maximum", "advice": "Prime Window. Maximum liquidity and volume.", "can_enter": True, "min_grade": "B"}
    elif 1020 <= t < 1260: # London-NY Gap
        return {"time_str": time_str, "window": "London-NY Gap", "volatility": "🟡 Moderate", "aggression": "Moderate", "advice": "Secondary Window. Favor setups with clear structural alignment.", "can_enter": True, "min_grade": "B"}
    elif 480 <= t < 720: # Asian Session
        return {"time_str": time_str, "window": "Asian Session", "volatility": "🟡 Low", "aggression": "Conservative", "advice": "Low-Vol Window. Favor Grade A setups. Higher risk of chop.", "can_enter": True, "min_grade": "A"}
    else: # Off-hours (12 AM - 3 PM)
        return {"time_str": time_str, "window": "Off-hours", "volatility": "🟡 Low", "aggression": "Conservative", "advice": "Low-Vol Window. High risk of fakeouts. Favor Grade A setups.", "can_enter": True, "min_grade": "A"}

def print_session_check(session: dict):
    print(f"""
⏰ SESSION CHECK  [{session['time_str']}]
Current window : {session['window']}
Volatility     : {session['volatility']}
Aggression     : {session['aggression']}
Advice         : {session['advice']}""")

def print_market_structure(ms_htf: dict, ms_ltf: dict, htf_label: str, ltf_label: str, rsi_val, fvg_nearest: str, ob_nearest: str, liq_eqh: str, liq_eql: str):
    mss_status = "✅ None"
    if ms_ltf.get("mss") or ms_htf.get("mss"):
        evt = ms_ltf.get("last_event") or ms_htf.get("last_event") or "unknown"
        mss_status = f"⚠️ YES — structural reversal signal ({evt})"
    rsi_label = "—"
    if rsi_val is not None:
        rsi_label = f"{rsi_val:.1f}  ⚠️ Overbought" if rsi_val > 70 else f"{rsi_val:.1f}  ⚠️ Oversold" if rsi_val < 30 else f"{rsi_val:.1f}  🟢 Normal"
    print(f"""
MARKET STRUCTURE
  {htf_label} Trend  : {ms_htf['trend'].upper()}  |  Last event: {ms_htf['last_event'] or '—'}
  {ltf_label} Trend  : {ms_ltf['trend'].upper()}  |  Last event: {ms_ltf['last_event'] or '—'}
  MSS (ChoCh)  : {mss_status}
  FVG nearest  : {fvg_nearest}
  OB nearest   : {ob_nearest}
  Liquidity    : EQH at {liq_eqh} / EQL at {liq_eql}
  RSI ({ltf_label})     : {rsi_label}""")

def print_trade_plan(symbol: str, direction: str, score: int, grade: str, entry: float, entry_note: str, stops: dict, sizing: dict, trail_callback_pct: float, invalidation: float, tf_label: str = "4H"):
    dir_emoji = "🚀" if direction == "LONG" else "🐻"
    quality = "🟢 PRIME" if score >= 8 else "🟡 GOOD"
    sl_pct = stops['sl_pct'] * 100
    rr1 = abs(stops["tp1"] - entry) / abs(stops["sl"] - entry) if abs(stops["sl"] - entry) > 0 else 0
    rr2 = abs(stops["tp2"] - entry) / abs(stops["sl"] - entry) if abs(stops["sl"] - entry) > 0 else 0
    inv_dir = "below" if direction == "LONG" else "above"
    print(f"""
{dir_emoji} {direction} — {quality}  Score: {score}/10  Grade: {grade}

Entry          : {fmt(entry)}  ← {entry_note}
Stop-Loss      : {fmt(stops['sl'])}  ({sl_pct:.2f}%  |  ATR × 1.5)
TP1 (35%)      : {fmt(stops['tp1'])}  → RR 1:{rr1:.1f}  → on hit: move SL to breakeven
TP2 (40%)      : {fmt(stops['tp2'])}  → RR 1:{rr2:.1f}  → on hit: activate trailing stop
TP3 (25%)      : Trailing Stop
                  Callback rate  : {trail_callback_pct:.2f}%  (ATR-derived)
                  Activation     : {fmt(stops['tp1'])}

Position
  {sizing['label']} | {sizing['lev']}x leverage | Margin: ${sizing['margin']} | Max risk: ${sizing['risk']:.2f}

Invalidation   : {tf_label} close {inv_dir} {fmt(invalidation)} → exit entire position.""")

def print_waiting_room(symbol: str, reasons: list, ms_htf: dict, ms_ltf: dict, htf_label: str, ltf_label: str, key_levels: list, preconditions: dict, next_window: str, rerun_cmd: str, verify_note: str, fvg_zones: list = None, ob_zones: list = None):
    print(f"""
⏳ WAITING ROOM  — No trade yet

Why not now:""")
    for r in reasons: print(f"  • {r}")
    print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHAT WOULD UNLOCK A TRADE""")
    sh = fmt(ms_ltf.get("swing_high")) if ms_ltf.get("swing_high") else "—"
    sl_val = fmt(ms_ltf.get("swing_low")) if ms_ltf.get("swing_low") else "—"
    bull_fvg_note = ""
    bear_fvg_note = ""
    if fvg_zones:
        for fvg in fvg_zones[:2]:
            if fvg["type"] == "bullish": 
                bull_fvg_note = f"\n  🔓 {ltf_label} pullback to bullish FVG at {fmt(fvg['bottom'])}–{fmt(fvg['top'])}"
            elif fvg["type"] == "bearish": 
                bear_fvg_note = f"\n  🔓 {ltf_label} pullback to bearish FVG at {fmt(fvg['bottom'])}–{fmt(fvg['top'])}"
    print(f"""
    For LONG to become valid:
    🔓 {htf_label} candle CLOSES above {sh} — confirms BOS{bull_fvg_note}

    For SHORT to become valid:
    🔓 {htf_label} candle CLOSES below {sl_val} — confirms BOS{bear_fvg_note}""")

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("KEY LEVELS TO WATCH")
    for price_val, desc in key_levels: print(f"  📍 {fmt(price_val)}  — {desc}")
    print(f"""
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    PATTERN TO WATCH FOR
    {ms_htf['trend'].capitalize() if ms_htf['trend'] != 'ranging' else 'Directional'} setup trigger candle:

    1. Engulfing candle on {ltf_label} CLOSING at a key level with volume > 1.5x average
    2. Pin bar (hammer/shooting star) on 15M rejecting off an OB or FVG zone
    3. {ltf_label} BOS after a liquidity sweep of {'EQL' if ms_htf['trend'] != 'bearish' else 'EQH'}

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    PRE-CONDITIONS STATUS""")
    met = sum(1 for p in preconditions.values() if p)
    for name, passed in preconditions.items(): print(f"  [{'✅' if passed else '❌'}] {name}")
    print(f"\n  {met} of {len(preconditions)} conditions met. Need all {len(preconditions)} for full green light.")
    print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NEXT CHECK

  🕒 Next best window : {next_window}
  📋 Re-run command   : {rerun_cmd}
  ⚡ What to verify   : {verify_note}""")

def format_telegram_trade(symbol: str, direction: str, grade: str, session: dict, structure: dict, zones: dict, risk: dict, invalidation: float) -> str:
    dir_emoji = "🚀" if direction == "LONG" else "🐻"
    lines = [
        f"⏰ {session['window']} | {session['volatility']}",
        f"{dir_emoji} {symbol} | {direction} | Grade {grade}",
        "",
        f"📐 {structure.get('tf_4h', '—')} | {structure.get('tf_1h', '—')}",
        f"Event: {structure.get('event', '—')}",
        "",
        f"Entry: {fmt(zones.get('entry', 0))}",
        f"SL: {fmt(risk['sl'])} ({risk['sl_pct']:.2f}%)",
        f"TP1: {fmt(risk['tp1'])} | TP2: {fmt(risk['tp2'])}",
        f"Risk: ${risk['risk_usd']:.2f} | Margin: ${risk['margin']} | {risk['lev']}x",
        "",
        f"🚫 Invalidation: {'below' if direction == 'LONG' else 'above'} {fmt(invalidation)}",
    ]
    return "\n".join(lines)[:4090]

def format_telegram_waiting(symbol: str, session: dict, reasons: list, trigger_level: str, next_check: str) -> str:
    lines = [
        f"⏰ {session['window']} | {session['volatility']}",
        f"⏳ {symbol} — WAITING ROOM",
        "",
        "Why: " + "; ".join(reasons[:2]),
        f"Watch: {trigger_level}",
        f"Next: {next_check}",
    ]
    return "\n".join(lines)[:4090]

def get_next_session_window() -> str:
    now = datetime.now(PHT)
    h = now.hour
    if h < 15: return "3:00 PM PHT — London open"
    elif h < 21: return "9:30 PM PHT — London–NY overlap opens"
    else: return "3:00 PM PHT tomorrow — London open"

def calc_trail_callback_pct(atr_val: float, entry: float, tok_type: str = "midcap") -> float:
    if atr_val is None or entry == 0: return 3.0
    base_pct = (atr_val / entry) * 100
    mult = {"major": 1.0, "midcap": 1.5, "new": 2.0}.get(tok_type, 1.5)
    return round(min(max(base_pct * mult, 1.0), 7.0), 2)
