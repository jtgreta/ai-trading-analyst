"""
funding.py — Institutional Edition
Funding rate scanner for Binance Futures perpetuals.

Usage:
  python funding.py                     → scan all futures for extreme funding
  python funding.py SOLUSDT ETHUSDT     → check specific symbols only
  python funding.py --watchlist         → check symbols from watchlist.txt

Why funding rates matter for futures trading:
  - Positive funding: longs pay shorts every 8 hours → unsustainable for longs
  - Negative funding: shorts pay longs every 8 hours → unsustainable for shorts
  - Extreme positive (>0.10%): market is overcrowded long → squeeze risk
  - Extreme negative (<-0.05%): market is overcrowded short → short-squeeze risk
  - Neutral (±0.01%): no funding pressure — preferred entry zone

Rule: Never enter a LONG on a coin with funding > 0.10%.
      Never enter a SHORT on a coin with funding < -0.05%.
      Use this as an additional filter BEFORE taking a scalp.

Output Sections:
  1. Extreme funding alerts (>0.10% or <-0.05%)
  2. Full sorted table (for watchlist mode)
  3. Telegram summary
"""

import sys
import os

from datetime import datetime
from trading_utils import (
    fetch_all_funding_rates, fetch_funding_rate,
    fetch_open_interest,
    EXCLUDE_SUBS, EXCLUDE_EXACT,
    fmt, send_telegram, get_session_info, print_session_check
)

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Thresholds
EXTREME_POSITIVE = 0.0010    # 0.10% — avoid longs above this
EXTREME_NEGATIVE = -0.0005   # -0.05% — avoid shorts below this
ELEVATED         = 0.0005    # 0.05% — worth noting


def classify_funding(rate: float) -> tuple:
    """Returns (label, emoji, action)."""
    pct = rate * 100
    if rate >= EXTREME_POSITIVE:
        return f"{pct:.4f}%", "🔴", "AVOID LONG — shorts being paid"
    if rate >= ELEVATED:
        return f"{pct:.4f}%", "🟡", "Caution on longs — elevated premium"
    if rate <= EXTREME_NEGATIVE:
        return f"{pct:.4f}%", "🔵", "AVOID SHORT — longs being paid"
    return f"{pct:.4f}%", "🟢", "Neutral — no funding pressure"


def scan_all_funding() -> list:
    """Fetch and filter all funding rates. Returns sorted list."""
    raw = fetch_all_funding_rates()
    if not raw:
        return []

    results = []
    for row in raw:
        sym  = row["symbol"]
        rate = row["fundingRate"]
        if any(sub in sym for sub in EXCLUDE_SUBS):
            continue
        if sym in EXCLUDE_EXACT:
            continue
        if not sym.endswith("USDT"):
            continue
        pct_lbl, emoji, action = classify_funding(rate)
        results.append({
            "symbol":  sym,
            "rate":    rate,
            "pct":     pct_lbl,
            "emoji":   emoji,
            "action":  action,
        })

    # Sort: most extreme positive first, then most extreme negative last
    results.sort(key=lambda x: x["rate"], reverse=True)
    return results


def check_symbols(symbols: list) -> list:
    """Check funding for specific named symbols."""
    results = []
    for sym in symbols:
        sym = sym.upper()
        data = fetch_funding_rate(sym)
        if not data:
            results.append({"symbol": sym, "rate": None, "pct": "N/A",
                            "emoji": "❓", "action": "Data unavailable"})
            continue
        rate = data["fundingRate"]
        pct_lbl, emoji, action = classify_funding(rate)
        # Add OI
        oi = fetch_open_interest(sym)
        results.append({
            "symbol":  sym,
            "rate":    rate,
            "pct":     pct_lbl,
            "emoji":   emoji,
            "action":  action,
            "oi_usd":  oi.get("openInterestValue", 0) if oi else 0,
        })
    return results


def print_symbol_results(results: list):
    """Print detailed results for named symbols."""
    print(f"\n{'─'*60}")
    print(f"  FUNDING CHECK — {len(results)} symbol(s)")
    print(f"{'─'*60}")
    for r in results:
        oi_str = f"  |  OI: ${r.get('oi_usd', 0)/1e6:.1f}M" if r.get("oi_usd") else ""
        print(f"\n  {r['emoji']} {r['symbol']}")
        print(f"     Funding Rate : {r['pct']}")
        print(f"     Verdict      : {r['action']}{oi_str}")


def print_scan_results(results: list, top_n: int = 15):
    """Print market-wide scan results."""
    extremes = [r for r in results if r["rate"] >= EXTREME_POSITIVE
                or r["rate"] <= EXTREME_NEGATIVE]
    elevated = [r for r in results if ELEVATED <= r["rate"] < EXTREME_POSITIVE]

    if extremes:
        print(f"\n🚨 EXTREME FUNDING ALERTS ({len(extremes)} coins)")
        print(f"  {'Symbol':<16} {'Rate':>8}  {'Action'}")
        print(f"  {'─'*55}")
        for r in extremes:
            print(f"  {r['emoji']} {r['symbol']:<14} {r['pct']:>8}  {r['action']}")
    else:
        print(f"\n✅ No extreme funding rates detected.")

    if elevated:
        print(f"\n🟡 ELEVATED FUNDING ({len(elevated)} coins — caution on longs)")
        for r in elevated[:8]:
            print(f"   {r['symbol']:<16} {r['pct']:>8}")

    # Lowest funding (most negative — best for longs)
    negatives = [r for r in results if r["rate"] < 0]
    if negatives:
        print(f"\n🔵 LOWEST FUNDING — Best for LONGS (shorts paying)")
        for r in negatives[:5]:
            print(f"   {r['emoji']} {r['symbol']:<16} {r['pct']:>8}  {r['action']}")

    print(f"\n\n  TOP 15 BY FUNDING RATE")
    print(f"  {'#':<3} {'Symbol':<16} {'Rate':>8}  Status")
    print(f"  {'─'*50}")
    for i, r in enumerate(results[:top_n], 1):
        print(f"  {i:<3} {r['symbol']:<16} {r['pct']:>8}  {r['emoji']} {r['action'][:35]}")


def build_telegram(results: list, mode: str) -> str:
    now = datetime.now().strftime("%H:%M PHT")
    extremes = [r for r in results if r["rate"] >= EXTREME_POSITIVE
                or r["rate"] <= EXTREME_NEGATIVE]

    lines = [f"💰 FUNDING RATE SCAN | {now}"]

    if extremes:
        lines.append(f"\n🚨 EXTREME RATES ({len(extremes)} coins)")
        for r in extremes[:8]:
            lines.append(f"{r['emoji']} {r['symbol']} {r['pct']} — {r['action'][:40]}")
    else:
        lines.append("\n✅ No extreme funding detected.")

    negatives = sorted([r for r in results if r["rate"] < -0.0002],
                       key=lambda x: x["rate"])
    if negatives:
        lines.append(f"\n🔵 LOWEST (long-friendly): " +
                     ", ".join(f"{r['symbol']} {r['pct']}" for r in negatives[:4]))

    if mode == "symbol":
        for r in results:
            oi_str = f" | OI:${r.get('oi_usd',0)/1e6:.0f}M" if r.get("oi_usd") else ""
            lines.append(f"\n{r['emoji']} {r['symbol']}: {r['pct']}{oi_str}")
            lines.append(f"   → {r['action']}")

    msg = "\n".join(lines)
    return msg[:4093] + "..." if len(msg) > 4093 else msg


def main():
    args    = [a for a in sys.argv[1:] if not a.startswith("-")]
    flags   = [a for a in sys.argv[1:] if a.startswith("-")]
    now     = datetime.now().strftime("%Y-%m-%d %H:%M PHT")
    session = get_session_info()

    print(f"\n{'═'*60}")
    print(f"  💰 FUNDING RATE SCANNER  (Binance Futures)")
    print(f"  {now}")
    print(f"{'═'*60}")
    print_session_check(session)

    # Thresholds reminder
    print(f"\n  Thresholds:")
    print(f"  🔴 AVOID LONG  : funding > {EXTREME_POSITIVE*100:.2f}%")
    print(f"  🔵 AVOID SHORT : funding < {EXTREME_NEGATIVE*100:.2f}%")
    print(f"  🟢 NEUTRAL     : {EXTREME_NEGATIVE*100:.2f}% to {ELEVATED*100:.2f}%")

    if args:
        # Named symbols mode
        print(f"\n[→] Checking {len(args)} named symbol(s)...")
        results = check_symbols(args)
        print_symbol_results(results)
        tg = build_telegram(results, mode="symbol")
    else:
        # Market-wide scan
        print(f"\n[→] Scanning all Binance Futures funding rates...")
        results = scan_all_funding()
        if not results:
            print("  ✗ No data. Check VPN.")
            return
        print(f"  {len(results)} perpetuals scanned.")
        print_scan_results(results)
        tg = build_telegram(results, mode="scan")

    send_telegram(tg)


if __name__ == "__main__":
    main()
