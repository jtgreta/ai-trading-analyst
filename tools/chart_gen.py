"""
chart_gen.py — Long-term BTC log-scale chart with cycle bounce tracing

Purpose:
  Produces a log10(price) vs date chart of Bitcoin's full Binance daily
  history and overlays a pseudo "value floor" line fitted through the major
  cycle bottoms (the lows BTC keeps bouncing off after big dumps).

  Series 1 = actual daily close price.
  Series 2 = pseudo bounce/trace line (log-linear fit through cycle troughs),
             extended forward to show where price historically reverts.

  It also prints a short readout of the current price vs the pseudo line and
  the next cycle-dump / bounce-back zone (illustrative, NOT a signal).

Usage:
  python tools/chart_gen.py            → save PNG to reports/_generated/btc_log10_chart.png
  python tools/chart_gen.py --show     → also display the chart window
  python tools/chart_gen.py --out my.png

Behavior:
  Fetches BTCUSDT daily klines from Binance (public endpoint, no key).
  The pseudo line is a least-squares fit in log10 space through the largest
  cycle bottoms (by date proximity to known capitulation lows). Both the fit
  and the chart are saved next to the PNG as CSV.

DISCLAIMER:
  This tool is for education and charting practice only. The pseudo line is a
  statistical trace, not a prediction. It does not constitute investment advice.
"""

import sys

from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import argparse
import csv

import requests

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CHART_DIR = ROOT / "reports"
BASE_URL = "https://api.binance.com/api/v3/klines"

# Known capitulation / cycle-bottom windows used as fit anchors (MTM date).
ANCHOR_DATES = [
    "2015-01-14",  # pre-exchange macro low (used if data reachable; else skipped)
    "2018-12-15",  # 2018 bear-market floor
    "2020-03-13",  # COVID panic low
    "2022-11-21",  # 2022 FTX capitulation floor
]


def fetch_daily_klines(symbol: str = "BTCUSDT") -> pd.DataFrame:
    """Fetch the full daily history for a symbol from Binance (paginated)."""
    rows = []
    start_ms = 0
    while True:
        params = {
            "symbol": symbol,
            "interval": "1d",
            "startTime": start_ms,
            "limit": 1000,
        }
        resp = requests.get(BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        rows.extend(data)
        start_ms = data[-1][6] + 1
        if len(data) < 1000:
            break

    df = pd.DataFrame(
        rows,
        columns=["open_time", "o", "h", "l", "c", "v", "close_time",
                 "qv", "n", "tb", "tq", "ignore"],
    )
    df["date"] = pd.to_datetime(df["open_time"], unit="ms")
    df["close"] = df["c"].astype(float)
    df["low"] = df["l"].astype(float)
    df = df[["date", "close", "low"]].drop_duplicates(subset="date").reset_index(drop=True)
    return df


def fit_bounce_line(df: pd.DataFrame) -> pd.Series:
    """Fit a log-linear 'value floor' through the cycle-bottom anchors.

    For each anchor date we take the minimum close inside a +/-40 day window
    (the actual trough), then fit log10(low) = a + b * days_since_start.
    Returns the fitted line (in log10) at every date in df.
    """
    start_date = df["date"].iloc[0]
    candidates = []
    for anchor in ANCHOR_DATES:
        anchor_ts = pd.Timestamp(anchor)
        if anchor_ts < start_date:
            continue
        window = df[
            (df["date"] >= anchor_ts - pd.Timedelta(days=40))
            & (df["date"] <= anchor_ts + pd.Timedelta(days=40))
        ]
        if window.empty:
            continue
        trough = window.loc[window["low"].idxmin()]
        candidates.append((trough["date"], trough["low"]))

    x = np.array([(d - start_date).days for d, _ in candidates], dtype=float)
    y = np.array([np.log10(p) for _, p in candidates], dtype=float)
    slope, intercept = np.polyfit(x, y, 1)

    days = np.array((df["date"] - start_date).dt.days, dtype=float)
    return pd.Series(slope * days + intercept, index=df.index)


def dump_zone_estimate(df: pd.DataFrame, log_line: pd.Series, price_now: float) -> dict:
    """Heuristic: compare current log price to the pseudo floor line.

    Returns the % distance to the floor and (illustratively) the date-price
    pair where the floor line sits today/future — the 'bounce-back zone'.
    """
    last = df["date"].iloc[-1]
    floor_today = 10 ** log_line.iloc[-1]
    pct_to_floor = (price_now / floor_today - 1) * 100

    days_ahead = np.arange(0, 365 * 3, 90)
    horizon = []
    start = last
    slope = (log_line.iloc[-1] - log_line.iloc[0]) / max(1, (last - df["date"].iloc[0]).days)
    for d in days_ahead:
        when = start + pd.Timedelta(days=int(d))
        lvl = 10 ** (log_line.iloc[-1] + slope * d)
        horizon.append((when.strftime("%Y-%m-%d"), round(lvl, 1)))

    return {
        "floor_today": floor_today,
        "pct_to_floor": pct_to_floor,
        "horizon": horizon,
    }


def build_chart(df: pd.DataFrame, log_line: pd.Series, out_path: Path, show: bool) -> None:
    start_date = df["date"].iloc[0]
    line = pd.Series(
        10 ** log_line.values,
        index=df["date"],
    )

    fig, ax = plt.subplots(figsize=(14, 7), dpi=120)
    ax.semilogy(df["date"], df["close"], lw=1.4, color="#f7931a",
                label="BTC close (log10 scale)")
    ax.plot(df["date"], line, lw=2.0, ls="--", color="#4a5cff",
            label="Pseudo value-floor (cycle lows fit)")

    # Annotate major dumps that bounced off the floor
    annotations = [
        ("2018-12-15", "2018 crash\nbottom"),
        ("2020-03-13", "COVID dump\nbottom"),
        ("2022-11-21", "FTX dump\nbottom"),
    ]
    for when, note in annotations:
        ts = pd.Timestamp(when)
        if ts < df["date"].iloc[0]:
            continue
        idx = (df["date"] - ts).abs().idxmin()
        ax.annotate(
            note, xy=(df["date"][idx], df["close"][idx]),
            xytext=(30, 30), textcoords="offset points",
            arrowprops=dict(arrowstyle="->", color="#444"),
            fontsize=8, color="#333",
        )

    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_title("Bitcoin long-term log scale — dumps bounce off the value floor",
                 fontsize=13, fontweight="bold")
    ax.set_ylabel("Price (USD, log10)")
    ax.set_xlabel("Date")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(loc="upper left")
    fig.tight_layout()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    if show:
        plt.show()
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="BTC log-scale chart with bounce tracing")
    parser.add_argument("--out", default=str(CHART_DIR / "_generated" / "btc_log10_chart.png"),
                        help="Output PNG path (default: reports/_generated/btc_log10_chart.png)")
    parser.add_argument("--show", action="store_true", help="Display the chart window")
    args = parser.parse_args()

    print("⏳ Fetching BTCUSDT daily history from Binance...")
    df = fetch_daily_klines()
    print(f"   ✓ {len(df)} daily bars  ({df['date'].iloc[0].date()} → {df['date'].iloc[-1].date()})")

    log_line = fit_bounce_line(df)
    price_now = float(df["close"].iloc[-1])
    est = dump_zone_estimate(df, log_line, price_now)

    out_path = Path(args.out)
    build_chart(df, log_line, out_path, args.show)

    print(f"\n   ✓ Chart saved: {out_path}")
    print("─" * 62)
    print("📈 BTC TODAY vs PSEUDO VALUE-FLOOR")
    print(f"   BTC close    : ${price_now:,.0f}")
    print(f"   Floor today  : ${est['floor_today']:,.0f}")
    print(f"   Price vs floor: +{est['pct_to_floor']:.0f}% above floor")
    print("─" * 62)
    print("🔮 Probable next BIG-DUMP bounce-back zone (floor-line projection):")
    for when, lvl in est["horizon"]:
        print(f"   {when}  →  floor ≈ ${lvl:,.0f}")
    print("─" * 62)
    print("⚠️  Illustrative trace, not a signal. Not financial advice.")


if __name__ == "__main__":
    main()