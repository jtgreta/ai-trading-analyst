---
name: market_bias
description: >
  Pre-session market bias briefing. Fetches BTC and ETH structure, funding rate,
  and long/short ratio to produce a scored RISK ON / RISK OFF / NEUTRAL / STAY OUT
  verdict. Run this before every scan session. Requires no arguments.
version: institutional
---

# Market Bias — Pre-Session Briefing

## Purpose
Answers one question before you open any chart: **Should I be looking for longs,
shorts, or staying out entirely?**

Running the Scanner or Scalper without knowing the macro bias is like trading
without a trend filter. This skill provides that filter.

---

## Runtime Notes
- PowerShell runs internally — use `python`
- trading_utils.py must be in the same directory
- Ensure VPN is active on hotspot

---

## ⚠️ PYTHON FILE NAMING CONVENTION — MANDATORY

File name: `skill_market_bias.py`

**Before creating, ALWAYS check if it already exists:**
```powershell
Test-Path "C:\Users\Jerome\gemini-trading-analyst\skill_market_bias.py"
```
If found, run it directly. Do not rewrite.

---

## Execution

```powershell
# Full briefing (default)
python "C:\Users\Jerome\gemini-trading-analyst\skill_market_bias.py"

# One-line verdict only
python "C:\Users\Jerome\gemini-trading-analyst\skill_market_bias.py" --quiet
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
| BTC funding rate (contrarian) | fetch_funding_rate("BTCUSDT") | ±1 pt |
| BTC LS ratio (contrarian) | fetch_ls_ratio("BTCUSDT") | ±1 pt |

**Funding logic (contrarian):**
- Funding > 0.15% (high positive) → bear_pts +1 (crowd overly long = squeeze risk)
- Funding < -0.05% (negative) → bull_pts +1 (crowd overly short = long-friendly)

**LS ratio logic (contrarian):**
- Ratio > 1.5 (crowd heavily long) → bear_pts +1
- Ratio < 0.67 (crowd heavily short) → bull_pts +1

---

## Verdict Rules

| Condition | Verdict | Action |
|---|---|---|
| Outside session window | ⛔ STAY OUT | No trades |
| bull_pts > bear_pts + 1 | 🟢 RISK ON | Look for LONG setups |
| bear_pts > bull_pts + 1 | 🔴 RISK OFF | Look for SHORT setups |
| Otherwise | 🟡 NEUTRAL | Grade A only, reduce size 50% |

**Confidence:**
- Strong: dominant side scores ≥ 5 pts
- Moderate: dominant side scores 3–4 pts

---

## Output Format

```
════════════════════════════════════════════════════
  📊 MARKET BIAS BRIEFING  |  [datetime PHT]
════════════════════════════════════════════════════

⏰ SESSION CHECK
[current window / quality / advice]

BTC PRICE: [price]  ([24H change]%)

STRUCTURE
  BTC 4H Trend  : [BULLISH/BEARISH/RANGING]  |  Last event: [BOS/ChoCh/—]
  BTC 1H Trend  : [trend]  |  Last event: [event]
  ETH 4H Trend  : [trend]

KEY LEVELS (BTC)
  4H MA20       : [price]  (✅ ABOVE / ❌ BELOW)
  4H MA50       : [price]  (✅ ABOVE / ❌ BELOW)
  Nearest FVG   : [type] [low]–[high]  ([X.X]% away)
  RSI (1H)      : [value]

MARKET SENTIMENT
  BTC Funding   : [rate]%  [warning if extreme]
  LS Ratio (1H) : [ratio] ([long]% longs)  [label]

SCORING
  Bull signals  : [N] pts
  Bear signals  : [N] pts

════════════════════════════════════════════════════
  VERDICT: [🟢 RISK ON / 🔴 RISK OFF / 🟡 NEUTRAL / ⛔ STAY OUT]  ([confidence])
  [directive — e.g. "look for LONG setups"]
  → Next step: run scanner / [specific advice]
════════════════════════════════════════════════════
```

---

## Telegram Summary

Sends compact verdict with BTC price, structure, funding, LS ratio, and directive.

---

## Integration with Daily Routine

This skill is **Step 1** of the pre-session checklist:
1. `skill_market_bias.py` ← **run this first**
2. `skill_funding.py`
3. `skill_scanner_run.py`
4. `skill_scalper_analyze.py SYMBOL`

---

## ACTIVATION KEYWORDS
bias | market bias | risk on | risk off | btc structure | pre-session |
what's the bias | should I be long or short | what's btc doing | btc trend
