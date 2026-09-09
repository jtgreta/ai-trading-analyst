"""
manage.py — Institutional Edition
Open position monitor + management advisor.

Usage:
  python manage.py SYMBOL DIRECTION ENTRY SL TP1 TP2
  python manage.py SOLUSDT LONG 145.50 140.00 156.00 165.00

  DIRECTION : LONG or SHORT
  ENTRY     : Your actual entry price
  SL        : Your stop-loss level
  TP1       : First take-profit (35% close → move SL to BE)
  TP2       : Second take-profit (40% close → activate trailing stop)

What it does:
  1. Fetches current live price
  2. Calculates current P&L (unrealized) in USD and %
  3. Shows distance to each level (SL / TP1 / TP2)
  4. Checks current 4H structure for trade validity
  5. Issues management advice based on rules:
     - TP1 hit → move SL to breakeven
     - TP2 hit → activate trailing stop
     - Structure reversed against trade → consider early exit
     - RSI exhaustion in profit → consider partial close
  6. Sends Telegram update
"""

import sys
import os

from datetime import datetime
from trading_utils import (
    fetch_klines, fetch_ticker, fetch_funding_rate,
    detect_bos_choch, rsi, atr,
    fmt, send_telegram, get_session_info, print_session_check,
    SCALP_RULES, classify_token
)

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

CAPITAL = 100.0


def parse_args():
    args = sys.argv[1:]
    if len(args) < 6:
        print("Usage: python manage.py SYMBOL DIRECTION ENTRY SL TP1 TP2")
        print("Example: python manage.py SOLUSDT LONG 145.50 140.00 156.00 165.00")
        sys.exit(1)
    symbol    = args[0].upper()
    direction = args[1].upper()
    if direction not in ("LONG", "SHORT"):
        print(f"Direction must be LONG or SHORT, got: {direction}")
        sys.exit(1)
    try:
        entry = float(args[2])
        sl    = float(args[3])
        tp1   = float(args[4])
        tp2   = float(args[5])
    except ValueError:
        print("ENTRY, SL, TP1, TP2 must be numbers.")
        sys.exit(1)
    return symbol, direction, entry, sl, tp1, tp2


def pct_from(price: float, ref: float) -> float:
    """Percent change from ref to price."""
    return (price - ref) / ref * 100 if ref != 0 else 0


def distance_pct(price: float, level: float) -> float:
    """Distance from current price to a level, as % of current price."""
    return abs(price - level) / price * 100 if price != 0 else 0


def assess_position(symbol, direction, entry, sl, tp1, tp2):
    """Full position assessment. Returns structured result dict."""

    # ── Fetch live data ───────────────────────────────────────────────────────
    ticker = fetch_ticker(symbol)
    k4h    = fetch_klines(symbol, "4h", 60)
    k1h    = fetch_klines(symbol, "1h", 60)
    fund   = fetch_funding_rate(symbol)

    if not ticker:
        print(f"  ✗ Could not fetch price for {symbol}. Check VPN.")
        sys.exit(1)

    current = float(ticker.get("lastPrice", 0))
    qvol    = float(ticker.get("quoteVolume", 0))
    tok_type = classify_token(symbol, qvol)

    # ── P&L Calculation ───────────────────────────────────────────────────────
    rules    = SCALP_RULES[tok_type]
    sl_dist  = abs(entry - sl)
    sl_pct   = sl_dist / entry

    # Estimate margin from rules (Grade B as default)
    margin   = rules["margin"] * 0.5
    lev      = rules["lev"]
    position = margin * lev
    risk_usd = position * sl_pct

    # Current PnL (unrealized)
    if direction == "LONG":
        move_pct = pct_from(current, entry)
        pnl_usd  = (current - entry) / entry * position
    else:
        move_pct = -pct_from(current, entry)
        pnl_usd  = (entry - current) / entry * position

    # ── Distance to levels ────────────────────────────────────────────────────
    dist_sl  = distance_pct(current, sl)
    dist_tp1 = distance_pct(current, tp1)
    dist_tp2 = distance_pct(current, tp2)

    # Level status
    if direction == "LONG":
        sl_hit  = current <= sl
        tp1_hit = current >= tp1
        tp2_hit = current >= tp2
        above_entry = current > entry
    else:
        sl_hit  = current >= sl
        tp1_hit = current <= tp1
        tp2_hit = current <= tp2
        above_entry = current < entry

    # ── Structure Check ───────────────────────────────────────────────────────
    ms_4h = detect_bos_choch(k4h, lookback=30) if k4h else None
    ms_1h = detect_bos_choch(k1h, lookback=30) if k1h else None

    cl_1h = [c[4] for c in k1h] if k1h else []
    rsi_1h = rsi(cl_1h, 14) if len(cl_1h) >= 15 else None
    atr_1h = atr(k1h, 14) if k1h and len(k1h) >= 15 else None

    # Structure validity
    struct_valid = True
    struct_warn  = []
    if ms_4h:
        if direction == "LONG" and ms_4h["trend"] == "bearish":
            struct_valid = False
            struct_warn.append("4H structure turned BEARISH against LONG — trade invalidated")
        elif direction == "SHORT" and ms_4h["trend"] == "bullish":
            struct_valid = False
            struct_warn.append("4H structure turned BULLISH against SHORT — trade invalidated")
        if ms_1h and ms_1h["mss"]:
            if direction == "LONG" and ms_1h["last_event"] in ("ChoCh_down",):
                struct_warn.append("1H ChoCh DOWN detected — consider partial exit")
            elif direction == "SHORT" and ms_1h["last_event"] in ("ChoCh_up",):
                struct_warn.append("1H ChoCh UP detected — consider partial exit")

    # Funding pressure
    fund_rate = fund.get("fundingRate", 0) if fund else 0
    fund_warn = []
    if direction == "LONG" and fund_rate > 0.0010:
        fund_warn.append(f"Funding {fund_rate*100:.4f}% — longs paying. Consider TP1 early.")
    elif direction == "SHORT" and fund_rate < -0.0005:
        fund_warn.append(f"Funding {fund_rate*100:.4f}% — shorts paying. Consider TP1 early.")

    # RSI extremes in profit zone
    rsi_warn = []
    if rsi_1h and above_entry:
        if direction == "LONG" and rsi_1h > 75:
            rsi_warn.append(f"RSI {rsi_1h:.1f} overbought — momentum may fade. Lock partial profit.")
        elif direction == "SHORT" and rsi_1h < 25:
            rsi_warn.append(f"RSI {rsi_1h:.1f} oversold — momentum may fade. Lock partial profit.")

    # ── Management Advice ─────────────────────────────────────────────────────
    advice = []
    status = "🟡 IN PLAY"

    if sl_hit:
        status = "🔴 STOP-LOSS HIT"
        advice.append("Stop-loss reached. Position should be closed.")
        advice.append("Do NOT move the stop. Accept the loss and review the setup.")
    elif tp2_hit:
        status = "🟢 TP2 HIT — Trailing"
        advice.append("TP2 reached (40% should already be closed).")
        advice.append("Remaining 25% should be on trailing stop — let it run.")
        advice.append("Trail distance: " + (fmt(atr_1h) + " (ATR-based)" if atr_1h else "manual"))
    elif tp1_hit:
        status = "🟢 TP1 HIT — Manage"
        advice.append("TP1 reached (close 35% of position NOW if not done).")
        advice.append("Move SL to breakeven immediately: SL → " + fmt(entry))
        advice.append("Target: hold remaining for TP2 at " + fmt(tp2))
    elif not struct_valid:
        status = "⚠️ STRUCTURE INVALID"
        advice.extend(struct_warn)
        advice.append("Consider early exit — trade invalidation condition met.")
    elif above_entry:
        status = "🟡 IN PROFIT — Hold"
        advice.append(f"Trade is {move_pct:+.2f}% in your favor.")
        advice.append(f"Hold until TP1 at {fmt(tp1)} ({dist_tp1:.2f}% away).")
        if rsi_warn:
            advice.extend(rsi_warn)
    else:
        status = "🟠 IN DRAWDOWN"
        advice.append(f"Trade is {move_pct:+.2f}% against you.")
        advice.append(f"SL at {fmt(sl)} is {dist_sl:.2f}% away — hold your discipline.")
        advice.append("Do NOT move the SL. It was set before entry for a reason.")
        if struct_warn:
            advice.extend(struct_warn)

    if fund_warn:
        advice.extend(fund_warn)

    return {
        "symbol":       symbol,
        "direction":    direction,
        "entry":        entry,
        "sl":           sl,
        "tp1":          tp1,
        "tp2":          tp2,
        "current":      current,
        "move_pct":     move_pct,
        "pnl_usd":      pnl_usd,
        "dist_sl":      dist_sl,
        "dist_tp1":     dist_tp1,
        "dist_tp2":     dist_tp2,
        "sl_hit":       sl_hit,
        "tp1_hit":      tp1_hit,
        "tp2_hit":      tp2_hit,
        "struct_valid": struct_valid,
        "struct_warn":  struct_warn,
        "rsi_warn":     rsi_warn,
        "fund_warn":    fund_warn,
        "advice":       advice,
        "status":       status,
        "ms_4h":        ms_4h,
        "ms_1h":        ms_1h,
        "rsi_1h":       rsi_1h,
        "fund_rate":    fund_rate,
        "tok_type":     tok_type,
        "margin":       margin,
        "position":     position,
        "risk_usd":     risk_usd,
    }


def print_management(r: dict, session: dict):
    now = datetime.now().strftime("%Y-%m-%d %H:%M PHT")
    dir_emoji = "🚀" if r["direction"] == "LONG" else "🐻"
    pnl_emoji = "🟢" if r["pnl_usd"] >= 0 else "🔴"

    print(f"\n{'═'*60}")
    print(f"  📋 POSITION MANAGER: {r['symbol']}")
    print(f"  {now}")
    print(f"{'═'*60}")
    print_session_check(session)

    print(f"\nPOSITION SUMMARY")
    print(f"  {dir_emoji} {r['direction']}  |  Token: {r['tok_type'].capitalize()}")
    print(f"  Entry       : {fmt(r['entry'])}")
    print(f"  Current     : {fmt(r['current'])}  ({r['move_pct']:+.2f}% from entry)")
    print(f"  {pnl_emoji} Unreal. P&L : ${r['pnl_usd']:+.2f}  (estimated, {r['direction']} {r['position']:.0f} position)")

    print(f"\nLEVELS")
    sl_arrow  = "← ⚠️ HIT" if r["sl_hit"] else f"({r['dist_sl']:.2f}% away)"
    tp1_arrow = "← ✅ HIT" if r["tp1_hit"] else f"({r['dist_tp1']:.2f}% away)"
    tp2_arrow = "← ✅ HIT" if r["tp2_hit"] else f"({r['dist_tp2']:.2f}% away)"
    print(f"  SL          : {fmt(r['sl'])}   {sl_arrow}")
    print(f"  TP1 (35%)   : {fmt(r['tp1'])}   {tp1_arrow}")
    print(f"  TP2 (40%)   : {fmt(r['tp2'])}   {tp2_arrow}")
    print(f"  TP3 (25%)   : Trailing (trail at SL dist after TP2)")

    print(f"\nSTRUCTURE CHECK (4H)")
    if r["ms_4h"]:
        ms4h = r["ms_4h"]
        valid_str = "✅ Valid" if r["struct_valid"] else "❌ INVALIDATED"
        print(f"  4H Trend    : {ms4h['trend'].upper()}  |  Event: {ms4h['last_event'] or '—'}")
        if r["ms_1h"]:
            ms1h = r["ms_1h"]
            print(f"  1H Trend    : {ms1h['trend'].upper()}  |  MSS: {'⚠️ YES' if ms1h['mss'] else '✅ None'}")
        print(f"  Validity    : {valid_str}")
    rsi_val = f"{r['rsi_1h']:.1f}" if r['rsi_1h'] else "—"
    print(f"  RSI (1H)    : {rsi_val}")
    print(f"  Funding     : {r['fund_rate']*100:.4f}%")

    print(f"\n{'─'*60}")
    print(f"  STATUS: {r['status']}")
    print(f"{'─'*60}")
    print(f"\nMANAGEMENT ADVICE")
    for line in r["advice"]:
        bullet = "  ⚠️" if any(w in line.lower() for w in ["warn", "exit", "invalid", "move", "close"]) else "  →"
        print(f"{bullet} {line}")
    print()


def build_telegram(r: dict) -> str:
    now = datetime.now().strftime("%H:%M PHT")
    dir_e = "🚀" if r["direction"] == "LONG" else "🐻"
    pnl_e = "🟢" if r["pnl_usd"] >= 0 else "🔴"

    lines = [
        f"📋 POSITION UPDATE | {now}",
        f"{dir_e} {r['symbol']} {r['direction']}",
        f"Entry: {fmt(r['entry'])} → Now: {fmt(r['current'])} ({r['move_pct']:+.2f}%)",
        f"{pnl_e} P&L: ${r['pnl_usd']:+.2f} (est.)",
        "",
        f"SL: {fmt(r['sl'])} ({r['dist_sl']:.2f}% away)",
        f"TP1: {fmt(r['tp1'])} ({r['dist_tp1']:.2f}% away)",
        f"TP2: {fmt(r['tp2'])} ({r['dist_tp2']:.2f}% away)",
        "",
        f"{r['status']}",
    ]
    for a in r["advice"][:3]:
        lines.append(f"→ {a}")

    msg = "\n".join(lines)
    return msg[:4093] + "..." if len(msg) > 4093 else msg


def main():
    symbol, direction, entry, sl, tp1, tp2 = parse_args()
    session = get_session_info()

    r = assess_position(symbol, direction, entry, sl, tp1, tp2)
    print_management(r, session)
    send_telegram(build_telegram(r))


if __name__ == "__main__":
    main()
