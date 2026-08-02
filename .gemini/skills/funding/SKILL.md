---
name: funding
description: >
  Funding rate scanner for Binance Futures perpetuals. Scans all tickers or
  checks named symbols. Flags extreme positive funding (avoid longs > 0.10%) and
  extreme negative funding (avoid shorts < -0.05%). Run after market bias and
  before any scalp entry.
version: institutional
---

# Funding Rate Scanner — Pre-Entry Filter

## Purpose
Funding rates directly affect futures P&L. If you enter a long on a coin with
0.20% positive funding, you pay 0.20% every 8 hours — that is $0.20 per $100 on
a flat position, which eats your profit target.

**Rule: Never long a coin with funding > 0.10%. Never short a coin with funding < -0.05%.**

---

## Runtime Notes
- PowerShell runs internally — use `python`
- trading_utils.py must be in the same directory
- Ensure VPN is active on hotspot

---

## ⚠️ PYTHON FILE NAMING CONVENTION — MANDATORY

File name: `skill_funding.py`

**Before creating, ALWAYS check if it already exists:**
```powershell
Test-Path "C:\Users\Jerome\gemini-trading-analyst\skill_funding.py"
```
If found, run it directly. Do not rewrite.

---

## Execution

```powershell
# Scan all Binance Futures (show extremes + top 15)
python "C:\Users\Jerome\gemini-trading-analyst\skill_funding.py"

# Check specific symbols before a scalp
python "C:\Users\Jerome\gemini-trading-analyst\skill_funding.py" SOLUSDT ETHUSDT BTCUSDT

# Check a single coin
python "C:\Users\Jerome\gemini-trading-analyst\skill_funding.py" PEPEUSDT
```

---

## Activation Triggers
- "check funding"
- "funding rate"
- "funding on [SYMBOL]"
- "is [SYMBOL] safe to long/short"
- "funding scan"
- "what's the funding"

---

## Funding Rate Thresholds

| Rate | Label | Rule |
|---|---|---|
| > 0.10% | 🔴 EXTREME POSITIVE | Avoid LONG — longs paying premium |
| 0.05% – 0.10% | 🟡 ELEVATED | Caution on longs — slight long premium |
| -0.05% – 0.05% | 🟢 NEUTRAL | No funding pressure — preferred entry zone |
| < -0.05% | 🔵 NEGATIVE | Avoid SHORT — shorts paying, longs favored |

Funding is paid every **8 hours** on Binance Futures.
Check at: 00:00, 08:00, 16:00 UTC (08:00, 16:00, 00:00 PHT).

---

## What It Fetches

**Market-wide scan (no args):**
```
GET https://fapi.binance.com/fapi/v1/fundingRate
```
Returns latest funding for all perpetuals. Filters out stablecoin pairs.
Sorts highest to lowest. Shows extremes + top 15 + lowest (best for longs).

**Named symbol mode:**
```
GET https://fapi.binance.com/fapi/v1/fundingRate?symbol=SYMBOL&limit=1
GET https://fapi.binance.com/fapi/v1/openInterest?symbol=SYMBOL
```
Also shows Open Interest in USD for context (high OI = more institutional activity).

---

## Output Format

```
════════════════════════════════════════════════════
  💰 FUNDING RATE SCANNER  (Binance Futures)
  [datetime PHT]
════════════════════════════════════════════════════

Thresholds:
  🔴 AVOID LONG  : funding > 0.10%
  🔵 AVOID SHORT : funding < -0.05%
  🟢 NEUTRAL     : -0.05% to 0.05%

🚨 EXTREME FUNDING ALERTS ([N] coins)
  [emoji] [SYMBOL]   [rate]%   [action]

🟡 ELEVATED FUNDING ([N] coins — caution on longs)
  [SYMBOL]   [rate]%

🔵 LOWEST FUNDING — Best for LONGS (shorts paying)
  [emoji] [SYMBOL]   [rate]%   [action]

TOP 15 BY FUNDING RATE
  [# | Symbol | Rate | Status]
```

---

## Telegram Summary

Sends: extreme alerts (up to 8 coins), lowest funding coins (best for longs),
and per-symbol details when run in named-symbol mode.

---

## Integration with Daily Routine

This skill is **Step 2** of the pre-session checklist:
1. `skill_market_bias.py`
2. `skill_funding.py` ← **run this second**
3. `skill_scanner_run.py`
4. `skill_scalper_analyze.py SYMBOL`

Also run it on any specific coin before entering a trade.

---

## ACTIVATION KEYWORDS
funding | funding rate | funding scan | check funding |
is [SYMBOL] safe to long | what's the funding | funding on SYMBOL
