"""
skill_scanner_filter.py
Scanner Step 1-4: Fetch all Binance Futures tickers, filter by volume/range/change,
rank by absolute 24H move, return top 10.
Self-contained — no imports from other local files.
"""
import requests
import sys


EXCLUDE_SUBSTRINGS = ["USDC", "BUSD", "TUSD", "DAI", "FDUSD"]
EXCLUDE_EXACT      = {"BTCDOMUSDT", "DEFIUSDT", "ALTUSDT"}


def scan():
    url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"[scanner_filter] ERROR: {e}", file=sys.stderr)
        return [], 0

    filtered = []
    for t in data:
        symbol = t.get("symbol", "")
        if any(sub in symbol for sub in EXCLUDE_SUBSTRINGS):
            continue
        if symbol in EXCLUDE_EXACT:
            continue

        try:
            quote_volume     = float(t["quoteVolume"])
            price_change_pct = float(t["priceChangePercent"])
            high_price       = float(t["highPrice"])
            low_price        = float(t["lowPrice"])
            last_price       = float(t["lastPrice"])

            if low_price == 0:
                continue

            abs_change   = abs(price_change_pct)
            range_pct    = (high_price - low_price) / low_price * 100

            if quote_volume > 100_000_000 and range_pct > 10 and abs_change > 3:
                filtered.append({
                    "symbol":             symbol,
                    "priceChangePercent": price_change_pct,
                    "quoteVolume":        quote_volume,
                    "rangePercent":       range_pct,
                    "absChange":          abs_change,
                    "lastPrice":          last_price,
                    "highPrice":          high_price,
                    "lowPrice":           low_price,
                })
        except (ValueError, KeyError, ZeroDivisionError):
            continue

    # Relax threshold if fewer than 5 passed
    if len(filtered) < 5:
        filtered = []
        for t in data:
            symbol = t.get("symbol", "")
            if any(sub in symbol for sub in EXCLUDE_SUBSTRINGS):
                continue
            if symbol in EXCLUDE_EXACT:
                continue
            try:
                quote_volume     = float(t["quoteVolume"])
                price_change_pct = float(t["priceChangePercent"])
                high_price       = float(t["highPrice"])
                low_price        = float(t["lowPrice"])
                last_price       = float(t["lastPrice"])
                if low_price == 0:
                    continue
                abs_change = abs(price_change_pct)
                range_pct  = (high_price - low_price) / low_price * 100
                if quote_volume > 100_000_000 and range_pct > 7 and abs_change > 3:
                    filtered.append({
                        "symbol":             symbol,
                        "priceChangePercent": price_change_pct,
                        "quoteVolume":        quote_volume,
                        "rangePercent":       range_pct,
                        "absChange":          abs_change,
                        "lastPrice":          last_price,
                        "highPrice":          high_price,
                        "lowPrice":           low_price,
                    })
            except Exception:
                continue

    # Sort by absolute move DESC, take top 10
    filtered.sort(key=lambda x: x["absChange"], reverse=True)
    return filtered[:10], len(filtered)


if __name__ == "__main__":
    top10, total = scan()
    print(f"Matched: {total}")
    for i, coin in enumerate(top10, 1):
        tag = "📈" if coin["priceChangePercent"] > 0 else "📉"
        print(f"{i}. {tag} {coin['symbol']:20s}  {coin['priceChangePercent']:+.2f}%  "
              f"Vol: ${coin['quoteVolume']/1e6:.0f}M  Range: {coin['rangePercent']:.1f}%")