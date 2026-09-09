"""
market_bias.py — Institutional Edition
Pre-session market bias briefing. Run this BEFORE the Scanner every session.

Usage:
  python market_bias.py           → full briefing
  python market_bias.py --quiet   → one-line verdict only

Purpose:
  Answers the question: "Should I be looking for longs, shorts, or staying out?"
  before running any scan or analysis.

Checks:
  1. BTC 4H structure (BOS/ChoCh) — the master bias signal
  2. ETH 4H structure — corroboration / divergence
  3. BTC 1H structure — intraday micro-trend
  4. BTC funding rate — extreme funding warns against direction
  5. BTC long/short ratio — crowd positioning (contrarian signal)
  6. Session window — are we even in a tradeable window?

Verdict:
  🟢 RISK ON   — BTC bullish structure, look for LONGS
  🔴 RISK OFF  — BTC bearish structure, look for SHORTS
  🟡 NEUTRAL   — Ranging or conflicting — wait for clarity, reduce size
  ⛔ STAY OUT  — Outside session window
"""

import sys
import os

from datetime import datetime
from trading_utils import (
    fetch_klines, fetch_ticker,
    fetch_funding_rate, fetch_ls_ratio,
    detect_bos_choch, find_fvg,
    sma, rsi,
    fmt, get_session_info, print_session_check, send_telegram
)

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

QUIET = "--quiet" in sys.argv or "-q" in sys.argv


def label_funding(rate: float) -> str:
    pct = rate * 100
    if pct > 0.15:
        return f"{pct:.4f}%  ⚠️ HIGH POSITIVE (longs pay — squeeze risk)"
    if pct > 0.05:
        return f"{pct:.4f}%  🔶 Elevated (slight long premium)"
    if pct < -0.05:
        return f"{pct:.4f}%  🔷 Negative (shorts pay — long-friendly)"
    return f"{pct:.4f}%  ✅ Neutral"


def label_ls(ratio: float, long_pct: float) -> str:
    if ratio > 1.5:
        return f"{ratio:.2f} ({long_pct*100:.1f}% longs)  ⚠️ Crowd heavily long — contrarian bearish"
    if ratio > 1.1:
        return f"{ratio:.2f} ({long_pct*100:.1f}% longs)  🔶 Leaning long"
    if ratio < 0.67:
        return f"{ratio:.2f} ({long_pct*100:.1f}% longs)  ⚠️ Crowd heavily short — contrarian bullish"
    if ratio < 0.9:
        return f"{ratio:.2f} ({long_pct*100:.1f}% longs)  🔷 Leaning short"
    return f"{ratio:.2f} ({long_pct*100:.1f}% longs)  ✅ Balanced"


def analyze_bias() -> dict:
    """Run full bias analysis and return structured results."""

    # ── Fetch Data ─────────────────────────────────────────────────────────────
    k4h_btc = fetch_klines("BTCUSDT", "4h", 100)
    k1h_btc = fetch_klines("BTCUSDT", "1h", 60)
    k4h_eth = fetch_klines("ETHUSDT", "4h", 60)
    tick_btc = fetch_ticker("BTCUSDT")
    fund_btc = fetch_funding_rate("BTCUSDT")
    ls_btc   = fetch_ls_ratio("BTCUSDT", period="1h")

    btc_price = float(tick_btc.get("lastPrice", 0)) if tick_btc else 0
    btc_chg   = float(tick_btc.get("priceChangePercent", 0)) if tick_btc else 0

    # ── SMC Analysis ──────────────────────────────────────────────────────────
    ms_4h_btc = detect_bos_choch(k4h_btc, lookback=40) if k4h_btc else None
    ms_1h_btc = detect_bos_choch(k1h_btc, lookback=30) if k1h_btc else None
    ms_4h_eth = detect_bos_choch(k4h_eth, lookback=40) if k4h_eth else None

    # ── BTC Key Levels ────────────────────────────────────────────────────────
    fvgs_btc = find_fvg(k1h_btc, lookback=25) if k1h_btc else []
    cl_btc_1h = [c[4] for c in k1h_btc] if k1h_btc else []
    rsi_btc = rsi(cl_btc_1h, 14) if len(cl_btc_1h) >= 15 else None

    # ── Moving Averages (BTC 4H) ──────────────────────────────────────────────
    cl_btc_4h = [c[4] for c in k4h_btc] if k4h_btc else []
    ma20_4h = sma(cl_btc_4h, 20)
    ma50_4h = sma(cl_btc_4h, 50)
    btc_above_ma20 = btc_price > ma20_4h if ma20_4h else None
    btc_above_ma50 = btc_price > ma50_4h if ma50_4h else None

    # ── Scoring ───────────────────────────────────────────────────────────────
    bull_pts = 0
    bear_pts = 0

    # BTC 4H structure (most weight)
    btc_4h_trend = ms_4h_btc["trend"] if ms_4h_btc else "unknown"
    btc_4h_event = ms_4h_btc["last_event"] if ms_4h_btc else None
    if btc_4h_trend == "bullish": bull_pts += 3
    elif btc_4h_trend == "bearish": bear_pts += 3

    # ETH 4H structure (corroboration)
    eth_4h_trend = ms_4h_eth["trend"] if ms_4h_eth else "unknown"
    if eth_4h_trend == "bullish": bull_pts += 1
    elif eth_4h_trend == "bearish": bear_pts += 1

    # BTC 1H structure (intraday)
    btc_1h_trend = ms_1h_btc["trend"] if ms_1h_btc else "unknown"
    btc_1h_event = ms_1h_btc["last_event"] if ms_1h_btc else None
    if btc_1h_trend == "bullish": bull_pts += 1
    elif btc_1h_trend == "bearish": bear_pts += 1

    # MA position
    if btc_above_ma20: bull_pts += 1
    elif btc_above_ma20 is False: bear_pts += 1

    # Funding (contrarian — extreme positive = bearish lean)
    funding_rate = fund_btc.get("fundingRate", 0) if fund_btc else 0
    if funding_rate > 0.15 / 100: bear_pts += 1   # high positive = potential squeeze
    elif funding_rate < -0.05 / 100: bull_pts += 1 # negative = long-friendly

    # LS ratio (contrarian — crowd heavy long = fade)
    ls_ratio = ls_btc.get("longShortRatio", 1) if ls_btc else 1
    long_pct  = ls_btc.get("longAccount", 0.5) if ls_btc else 0.5
    if ls_ratio > 1.5: bear_pts += 1   # crowd too long — contrarian short
    elif ls_ratio < 0.67: bull_pts += 1  # crowd too short — contrarian long

    # ── Verdict ───────────────────────────────────────────────────────────────
    session = get_session_info()
    if bull_pts > bear_pts + 1:
        verdict = "🟢 RISK ON"
        direction = "LONG bias — favor long setups"
        confidence = "Strong" if bull_pts >= 5 else "Moderate"
    elif bear_pts > bull_pts + 1:
        verdict = "🔴 RISK OFF"
        direction = "SHORT bias — favor short setups"
        confidence = "Strong" if bear_pts >= 5 else "Moderate"
    else:
        verdict = "🟡 NEUTRAL"
        direction = "No clear bias — reduce size or wait"
        confidence = "Low"

    return {
        "verdict":        verdict,
        "direction":      direction,
        "confidence":     confidence,
        "bull_pts":       bull_pts,
        "bear_pts":       bear_pts,
        "btc_price":      btc_price,
        "btc_chg":        btc_chg,
        "btc_4h_trend":   btc_4h_trend,
        "btc_4h_event":   btc_4h_event,
        "btc_1h_trend":   btc_1h_trend,
        "btc_1h_event":   btc_1h_event,
        "eth_4h_trend":   eth_4h_trend,
        "btc_above_ma20": btc_above_ma20,
        "btc_above_ma50": btc_above_ma50,
        "ma20_4h":        ma20_4h,
        "ma50_4h":        ma50_4h,
        "rsi_btc":        rsi_btc,
        "fvgs_btc":       fvgs_btc,
        "funding_rate":   funding_rate,
        "ls_ratio":       ls_ratio,
        "long_pct":       long_pct,
        "session":        session,
        "ms_1h_btc":      ms_1h_btc,
    }


def print_bias(b: dict):
    now = datetime.now().strftime("%Y-%m-%d %H:%M PHT")
    session = b["session"]

    print(f"\n{'═'*60}")
    print(f"  📊 MARKET BIAS BRIEFING  |  {now}")
    print(f"{'═'*60}")
    print_session_check(session)

    print(f"\n{'─'*60}")
    print(f"  BTC PRICE: {fmt(b['btc_price'])}  ({b['btc_chg']:+.2f}% 24H)")
    print(f"{'─'*60}")

    print(f"\nSTRUCTURE")
    print(f"  BTC 4H Trend  : {b['btc_4h_trend'].upper()}  |  Last event: {b['btc_4h_event'] or '—'}")
    print(f"  BTC 1H Trend  : {b['btc_1h_trend'].upper()}  |  Last event: {b['btc_1h_event'] or '—'}")
    print(f"  ETH 4H Trend  : {b['eth_4h_trend'].upper()}")

    print(f"\nKEY LEVELS (BTC)")
    ma20_str = fmt(b["ma20_4h"]) if b["ma20_4h"] else "—"
    ma50_str = fmt(b["ma50_4h"]) if b["ma50_4h"] else "—"
    above_ma20 = "✅ ABOVE" if b["btc_above_ma20"] else ("❌ BELOW" if b["btc_above_ma20"] is False else "—")
    above_ma50 = "✅ ABOVE" if b["btc_above_ma50"] else ("❌ BELOW" if b["btc_above_ma50"] is False else "—")
    print(f"  4H MA20       : {ma20_str}  ({above_ma20})")
    print(f"  4H MA50       : {ma50_str}  ({above_ma50})")
    if b["fvgs_btc"]:
        f = b["fvgs_btc"][0]
        dist = abs(b["btc_price"] - f["midpoint"]) / b["btc_price"] * 100
        print(f"  Nearest FVG   : {f['type'].capitalize()} {fmt(f['bottom'])}–{fmt(f['top'])}  ({dist:.1f}% away)")
    rsi_str = f"{b['rsi_btc']:.1f}" if b["rsi_btc"] else "—"
    print(f"  RSI (1H)      : {rsi_str}")

    print(f"\nMARKET SENTIMENT")
    print(f"  BTC Funding   : {label_funding(b['funding_rate'])}")
    print(f"  LS Ratio (1H) : {label_ls(b['ls_ratio'], b['long_pct'])}")

    print(f"\nSCORING")
    print(f"  Bull signals  : {b['bull_pts']} pts")
    print(f"  Bear signals  : {b['bear_pts']} pts")

    print(f"\n{'═'*60}")
    print(f"  VERDICT: {b['verdict']}  ({b['confidence']} confidence)")
    print(f"  {b['direction']}")

    if b["verdict"] == "🟢 RISK ON":
        print(f"\n  → Run scanner next: python scanner_run.py")
        print(f"  → Focus on LONG setups with 4H BOS / FVG entries")
        if b["btc_1h_trend"] != "bullish":
            print(f"  ⚠️ Note: BTC 1H is {b['btc_1h_trend']} — wait for 1H confirmation before entry")
    elif b["verdict"] == "🔴 RISK OFF":
        print(f"\n  → Run scanner next: python scanner_run.py")
        print(f"  → Focus on SHORT setups only")
        if b["btc_1h_trend"] != "bearish":
            print(f"  ⚠️ Note: BTC 1H is {b['btc_1h_trend']} — 4H bearish but 1H conflicting, size down")
    elif b["verdict"] == "🟡 NEUTRAL":
        print(f"\n  → Reduce position size 50% until bias clarifies")
        print(f"  → Only Grade A (score ≥8) setups in either direction")
    elif b["verdict"] == "⛔ STAY OUT":
        print(f"\n  → {session['advice']}")
        print(f"  → Re-run at next session window")
    print(f"{'═'*60}")


def build_telegram(b: dict) -> str:
    lines = [
        f"📊 MARKET BIAS | {datetime.now().strftime('%H:%M PHT')}",
        f"BTC: {fmt(b['btc_price'])} ({b['btc_chg']:+.2f}%)",
        "",
        f"BTC 4H: {b['btc_4h_trend'].upper()} | Event: {b['btc_4h_event'] or '—'}",
        f"BTC 1H: {b['btc_1h_trend'].upper()} | ETH 4H: {b['eth_4h_trend'].upper()}",
        f"Funding: {b['funding_rate']*100:.4f}% | LS: {b['ls_ratio']:.2f}",
        f"RSI(1H): {b['rsi_btc']:.1f}" if b['rsi_btc'] else "RSI(1H): —",
        "",
        f"{'='*30}",
        f"{b['verdict']} ({b['confidence']})",
        f"{b['direction']}",
        f"⏰ {b['session']['window']} | {b['session']['volatility']}",
    ]
    msg = "\n".join(lines)
    return msg[:4093] + "..." if len(msg) > 4093 else msg


def main():
    b = analyze_bias()

    if QUIET:
        print(f"{b['verdict']} | {b['direction']} | BTC 4H: {b['btc_4h_trend'].upper()}")
        return

    print_bias(b)
    send_telegram(build_telegram(b))


if __name__ == "__main__":
    main()
