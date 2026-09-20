"""
scanner_filter.py — Scanner Step 1-4
Fetch all Binance Futures tickers, filter by volume/range/change,
rank by absolute 24H move, return top 10.

Thin CLI wrapper around the shared ``trading.filters`` engine.
"""
import sys

from trading import fetch_all_tickers, scanner_candidates


def scan() -> tuple:
    """Top-10 candidates plus the total matched count."""
    tickers = fetch_all_tickers()
    if not tickers:
        print("[scanner_filter] ERROR: no ticker data", file=sys.stderr)
        return [], 0
    filtered, total = scanner_candidates(tickers)
    return filtered[:10], total


if __name__ == "__main__":
    top10, total = scan()
    print(f"Matched: {total}")
    for i, coin in enumerate(top10, 1):
        tag = "📈" if coin["priceChangePercent"] > 0 else "📉"
        print(f"{i}. {tag} {coin['symbol']:20s}  {coin['priceChangePercent']:+.2f}%  "
              f"Vol: ${coin['quoteVolume']/1e6:.0f}M  Range: {coin['rangePercent']:.1f}%")