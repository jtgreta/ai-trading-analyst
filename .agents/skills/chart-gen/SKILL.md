# Skill: chart-gen

# Chart Generator — Log-Scale Value-Floor Analysis

## Purpose

Generates a **log10(price) vs date** value-floor chart for **any coin** (BTC,
ETH, OKB, mid-caps...) from its complete daily history, with a **pseudo
value-floor line** fitted through the major cycle bottoms. It traces the "dumps
always bounce off the floor" behavior and projects where the floor sits in the
future — showing the probable next big-dump bounce-back zone.

Series 1 = actual daily close. Series 2 = pseudo bounce/trace line.
Supports **Binance** spot (`BTCUSDT`) and **OKX** spot (`OKB-USDT`) — no keys.

## Runtime Notes

- PowerShell runs internally — use `python`
- Uses public spot APIs (no key required)
- Chart is saved under `reports/_generated/`; regenerable output, always gitignored
- The fit is perspective/education only, NOT a signal

## ⚠️ PYTHON FILE NAMING CONVENTION — MANDATORY

File name: `tools/chart_gen.py`

**Before creating a new script, ALWAYS check if it already exists:**
```powershell
Test-Path "tools\chart_gen.py"
```
If found, run it directly. Do not rewrite.

## Execution

Interactive notebook (recommended — tweak CONFIG cell):
```powershell
# open the notebook
jupyter notebook "reports\value_floor_analysis.ipynb"
```
Run the cells in order — `CELL 1 (CONFIG)` holds every tweakable input
(exchange, symbol, date range, floor anchors, window, y-tick step, horizon,
output name). Chart is written to `reports/_generated/value_floor_chart.png`.

CLI (quick BTC, no tweaking):
```powershell
python "tools\chart_gen.py"             # save PNG to reports/_generated/btc_log10_chart.png
python "tools\chart_gen.py" --show      # also open the chart window
python "tools\chart_gen.py" --out my.png
```

## Activation Triggers

- "generate a log-scale chart for [coin]"
- "chart [symbol] on log scale"
- "show the value-floor trend line"
- "where is the next dump bounce zone"
- "log 10 chart"
- "what is price vs floor for [symbol]"

## What It Produces

1. A chart PNG in `reports/_generated/` (always excluded from git) with:
   - daily close (series 1, log10 y-axis, $ formatting, yearly x-ticks).
   - The pseudo value-floor line (series 2, dashed) = log-linear least-squares
     fit through the cycle bottom lows (each anchor troughed within ±40 days).
   - Its forward projection (dotted), and annotations marking the cycle bottoms.
2. A console readout:
   - Current price vs the fitted floor today (e.g., "+10% above floor").
   - A projected floor-line horizon (quarterly, 0-2 years) showing the
     probable next dump bounce-back zone.

## Output to the User

After running, summarize:

- Where the coin stands relative to the value floor (overshoot %).
- How past cycle bottoms reverted to (or near) the same log-linear band — the
  "bounces back from big drops" behavior is a charted tendency, not a guarantee.
- The projected floor-line price for the next quarter + one year.
- For exchange tokens (OKB/BNB...) or young assets: flag that a negative
  (below-floor) readout means a fragile fit, NOT a buy signal.
- The mandatory disclaimer: illustrative trace, not financial advice.

## See Also

- [Project overview](../docs/PROJECT.md)
- [Trading math](../docs/trading_math.md)