"""
skill_hunter_filter.py — Institutional Edition
Standalone Hunter pre-breakout filter.
Usage:
  python skill_hunter_filter.py               → machine-readable comma-separated symbols
  python skill_hunter_filter.py --verbose     → human-readable table output

Criteria (Hunter SKILL.md):
  quoteVolume > $100M
  3 < rangePercent < 25
  absChange < 15
  Exclude substrings: USDC, BUSD, TUSD, DAI, FDUSD
  Exclude exact: BTCDOMUSDT, DEFIUSDT, ALTUSDT
  Relax range max to 30 if fewer than 5 pass.

Output:
  Default (no flags) : comma-separated list of symbols — pipeable to skill_hunter_coil.py
  --verbose          : ranked table with volume / range / change per coin
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from trading_utils import fetch_all_tickers, EXCLUDE_SUBS, EXCLUDE_EXACT, fmt

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def get_hunter_candidates(tickers: list) -> tuple:
    """
    Filter tickers against Hunter pre-breakout criteria.
    Returns (candidates list, relaxed bool).
    Each candidate dict contains: symbol, quoteVolume, lastPrice, pctChange, range24h, absChange.
    """

    def _apply_filter(tickers, range_max):
        out = []
        for t in tickers:
            sym = t.get("symbol", "")
            if any(sub in sym for sub in EXCLUDE_SUBS):
                continue
            if sym in EXCLUDE_EXACT:
                continue
            try:
                qv  = float(t["quoteVolume"])
                pcp = float(t["priceChangePercent"])
                hi  = float(t["highPrice"])
                lo  = float(t["lowPrice"])
                lp  = float(t["lastPrice"])
                if lo <= 0 or lp <= 0:
                    continue
                rng = (hi - lo) / lo * 100
                ac  = abs(pcp)
                if qv > 100_000_000 and 3 < rng < range_max and ac < 15:
                    out.append({
                        "symbol":      sym,
                        "quoteVolume": qv,
                        "lastPrice":   lp,
                        "pctChange":   pcp,
                        "range24h":    rng,
                        "absChange":   ac,
                    })
            except Exception:
                continue
        return out

    candidates = _apply_filter(tickers, range_max=25)
    relaxed    = False

    if len(candidates) < 5:
        candidates = _apply_filter(tickers, range_max=30)
        relaxed    = True

    # Sort by volume descending — highest liquidity first
    candidates.sort(key=lambda x: x["quoteVolume"], reverse=True)
    return candidates, relaxed


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    if verbose:
        print(f"\n{'─'*65}")
        print(f"  🎯 HUNTER FILTER — Pre-Breakout Candidate Screen")
        print(f"{'─'*65}")
        print("\n  Fetching Binance Futures tickers...")

    tickers = fetch_all_tickers()
    if not tickers:
        if verbose:
            print("  ✗ No ticker data. Check VPN.")
        sys.exit(1)

    candidates, relaxed = get_hunter_candidates(tickers)

    if verbose:
        print(f"\n  {len(candidates)} coins passed Hunter pre-breakout filter"
              + (" (relaxed range ≤30%)" if relaxed else " (strict range ≤25%)"))
        print(f"  Criteria: Vol >$100M | Range 3–{'30' if relaxed else '25'}% | |Change| <15%\n")
        print(f"  {'#':<4} {'Symbol':<16} {'Vol ($M)':<12} {'Range%':<10} {'Change%':<10} {'Price'}")
        print(f"  {'─'*62}")
        for i, c in enumerate(candidates, 1):
            tag = "📈" if c["pctChange"] > 0 else "📉"
            print(
                f"  {i:<4} {c['symbol']:<16} ${c['quoteVolume']/1e6:<10.1f}"
                f" {c['range24h']:<10.1f}% {tag} {c['pctChange']:>+7.2f}%  {fmt(c['lastPrice'])}"
            )
        print(f"\n  → To analyze coils: python skill_hunter_coil.py {' '.join(c['symbol'] for c in candidates[:5])} ...")
        print(f"  → Full pipeline   : python skill_hunter_scan.py")
    else:
        # Machine-readable: comma-separated symbols, no trailing newline noise
        print(",".join(c["symbol"] for c in candidates))


if __name__ == "__main__":
    main()
