---
name: market-bias
description: >
  Pre-session market bias briefing. Fetches BTC and ETH structure, funding rate,
  and long/short ratio to produce a scored RISK ON / RISK OFF / NEUTRAL / STAY OUT
  verdict. Run this before every scan session. Requires no arguments.
version: institutional
---

# Market Bias Ã¢â‚¬â€ Pre-Session Briefing

## Purpose
Answers one question before you open any chart: **Should I be looking for longs,
shorts, or staying out entirely?**

Running the Scanner or Scalper without knowing the macro bias is like trading
without a trend filter. This skill provides that filter.

---

## Runtime Notes
- PowerShell runs internally Ã¢â‚¬â€ use `python`
- trading_utils.py lives in scripts/trading_utils.py (no repo-root dependency) - scripts import it directly from the same folder
- Ensure VPN is active on hotspot

---

## Ã¢Å¡Â Ã¯Â¸Â PYTHON FILE NAMING CONVENTION Ã¢â‚¬â€ MANDATORY

File name: `scripts/market_bias.py`

**Before creating a new script, ALWAYS check if it already exists:**
```powershell
Test-Path "scripts\market_bias.py"
```
If found, run it directly. Do not rewrite.

---

## Execution

```powershell
# Full briefing (default)
python "scripts\market_bias.py"

# One-line verdict only
python "scripts\market_bias.py" --quiet
```

---

## Activation Triggers
- "what's the bias"
- "market bias"
- "should I be long or short today"
- "is it risk on"
- "btc structure"
- "pre-session check"
- "what's btc doing"

---

## What It Checks

| Signal | Source | Weight |
|---|---|---|
| BTC 4H structure (BOS/ChoCh) | detect_bos_choch(k4h_btc) | 3 pts (highest) |
| ETH 4H structure | detect_bos_choch(k4h_eth) | 1 pt |
| BTC 1H structure | detect_bos_choch(k1h_btc) | 1 pt |
| BTC above 4H MA20 | sma(cl_btc_4h, 20) | 1 pt |
| BTC funding rate (contrarian) | fetch_funding_rate("BTCUSDT") | Ã‚Â±1 pt |
| BTC LS ratio (contrarian) | fetch_ls_ratio("BTCUSDT") | Ã‚Â±1 pt |

**Funding logic (contrarian):**
- Funding > 0.15% (high positive) Ã¢â€ â€™ bear_pts +1 (crowd overly long = squeeze risk)
- Funding < -0.05% (negative) Ã¢â€ â€™ bull_pts +1 (crowd overly short = long-friendly)

**LS ratio logic (contrarian):**
- Ratio > 1.5 (crowd heavily long) Ã¢â€ â€™ bear_pts +1
- Ratio < 0.67 (crowd heavily short) Ã¢â€ â€™ bull_pts +1

---

## Verdict Rules

| Condition | Verdict | Action |
|---|---|---|
| Outside session window | Ã¢â€ºâ€ STAY OUT | No trades |
| bull_pts > bear_pts + 1 | Ã°Å¸Å¸Â¢ RISK ON | Look for LONG setups |
| bear_pts > bull_pts + 1 | Ã°Å¸â€Â´ RISK OFF | Look for SHORT setups |
| Otherwise | Ã°Å¸Å¸Â¡ NEUTRAL | Grade A only, reduce size 50% |

**Confidence:**
- Strong: dominant side scores Ã¢â€°Â¥ 5 pts
- Moderate: dominant side scores 3Ã¢â‚¬â€œ4 pts

---

## Output Format

```
Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
  Ã°Å¸â€œÅ  MARKET BIAS BRIEFING  |  [datetime PHT]
Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

Ã¢ÂÂ° SESSION CHECK
[current window / quality / advice]

BTC PRICE: [price]  ([24H change]%)

STRUCTURE
  BTC 4H Trend  : [BULLISH/BEARISH/RANGING]  |  Last event: [BOS/ChoCh/Ã¢â‚¬â€]
  BTC 1H Trend  : [trend]  |  Last event: [event]
  ETH 4H Trend  : [trend]

KEY LEVELS (BTC)
  4H MA20       : [price]  (Ã¢Å“â€¦ ABOVE / Ã¢ÂÅ’ BELOW)
  4H MA50       : [price]  (Ã¢Å“â€¦ ABOVE / Ã¢ÂÅ’ BELOW)
  Nearest FVG   : [type] [low]Ã¢â‚¬â€œ[high]  ([X.X]% away)
  RSI (1H)      : [value]

MARKET SENTIMENT
  BTC Funding   : [rate]%  [warning if extreme]
  LS Ratio (1H) : [ratio] ([long]% longs)  [label]

SCORING
  Bull signals  : [N] pts
  Bear signals  : [N] pts

Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
  VERDICT: [Ã°Å¸Å¸Â¢ RISK ON / Ã°Å¸â€Â´ RISK OFF / Ã°Å¸Å¸Â¡ NEUTRAL / Ã¢â€ºâ€ STAY OUT]  ([confidence])
  [directive Ã¢â‚¬â€ e.g. "look for LONG setups"]
  Ã¢â€ â€™ Next step: run scanner / [specific advice]
Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
```

---

## Telegram Summary

Sends compact verdict with BTC price, structure, funding, LS ratio, and directive.

---

## Integration with Daily Routine

This skill is **Step 1** of the pre-session checklist:
1. `scripts/market_bias.py` Ã¢â€ Â **run this first**
2. `scripts/funding.py`
3. `scripts/scanner_run.py`
4. `scripts/scalper_analyze.py SYMBOL`

---

## ACTIVATION KEYWORDS
bias | market bias | risk on | risk off | btc structure | pre-session |
what's the bias | should I be long or short | what's btc doing | btc trend
