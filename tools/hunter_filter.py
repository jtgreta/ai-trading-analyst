"""
hunter_filter.py — Institutional Edition
Standalone Hunter pre-breakout filter.
Usage:
  python hunter_filter.py               → machine-readable comma-separated symbols
  python hunter_filter.py --verbose     → human-readable table output

Criteria (Hunter SKILL.md):
  quoteVolume > $100M
  3 < rangePercent < 25
  absChange < 15
  Exclude substrings: USDC, BUSD, TUSD, DAI, FDUSD
  Exclude exact: BTCDOMUSDT, DEFIUSDT, ALTUSDT
  Relax range max to 30 if fewer than 5 pass.

Output:
  Default (no flags) : comma-separated list of symbols — pipeable to hunter_coil.py
  --verbose          : ranked table with volume / range / change per coin
"""

import sys

from trading import fetch_all_tickers, hunter_candidates, fmt

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    if verbose:
        print(f"\n{'─'*65}")
        print("  🎯 HUNTER FILTER — Pre-Breakout Candidate Screen")
        print(f"{'─'*65}")
        print("\n  Fetching Binance Futures tickers...")

    tickers = fetch_all_tickers()
    if not tickers:
        if verbose:
            print("  ✗ No ticker data. Check VPN.")
        sys.exit(1)

    candidates, relaxed = hunter_candidates(tickers)

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
        print(f"\n  → To analyze coils: python hunter_coil.py {' '.join(c['symbol'] for c in candidates[:5])} ...")
        print("  → Full pipeline   : python hunter.py")
    else:
        # Machine-readable: comma-separated symbols, no trailing newline noise
        print(",".join(c["symbol"] for c in candidates))


if __name__ == "__main__":
    main()