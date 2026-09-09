---
name: manage
description: >
  Open position monitor and management advisor. Takes a live position's entry,
  SL, TP1, and TP2, fetches the current price, calculates unrealized P&L, checks
  4H structure validity, and issues specific management advice based on which level
  has been hit. Sends a Telegram update.
version: institutional
---

# Position Manager Ã¢â‚¬â€ Trade Lifecycle Advisor

## Purpose
Once a trade is entered, the system had no tool to help manage it. This skill
answers: "What should I do with this position right now?"

It enforces the management rules from `trading_rules.md`:
- TP1 hit Ã¢â€ â€™ close 35%, move SL to breakeven
- TP2 hit Ã¢â€ â€™ close 40%, activate trailing stop
- Structure reversed Ã¢â€ â€™ consider early exit
- RSI exhaustion in profit zone Ã¢â€ â€™ consider partial close

---

## Runtime Notes
- PowerShell runs internally Ã¢â‚¬â€ use `python`
- trading_utils.py lives in scripts/trading_utils.py (no repo-root dependency) - scripts import it directly from the same folder
- Ensure VPN is active on hotspot

---

## âš ï¸ SCRIPT LOCATION â€” MANDATORY

Script: `scripts/manage.py`

**Before creating a new script, ALWAYS check if it already exists:**
```powershell
Test-Path "scripts\manage.py"
```
If found, run it directly. Do not rewrite.

---

## Execution

```powershell
python "scripts\manage.py" SYMBOL DIRECTION ENTRY SL TP1 TP2
```

Arguments (in order):
- `SYMBOL`    : e.g. SOLUSDT
- `DIRECTION` : LONG or SHORT
- `ENTRY`     : your actual fill price
- `SL`        : your stop-loss level
- `TP1`       : first take-profit (35% close Ã¢â€ â€™ move SL to BE)
- `TP2`       : second take-profit (40% close Ã¢â€ â€™ activate trailing)

Examples:
```powershell
python manage.py SOLUSDT LONG 145.50 140.00 156.00 165.00
python manage.py ETHUSDT SHORT 3200 3320 3080 2970
```

---

## Activation Triggers
- "manage [SYMBOL]"
- "check my position on [SYMBOL]"
- "how is my [SYMBOL] trade"
- "should I close [SYMBOL]"
- "P&L on [SYMBOL]"
- "manage trade"

---

## What It Checks

**1. Price and P&L**
- Fetches live price from Binance
- Calculates unrealized P&L in USD (estimated from margin Ãƒâ€” leverage Ãƒâ€” move%)
- Shows move % from entry and distance to each level

**2. Level Status**
- SL hit?  Ã¢â€ â€™ STOP-LOSS HIT Ã¢â‚¬â€ close immediately
- TP2 hit? Ã¢â€ â€™ TRAILING Ã¢â‚¬â€ 40% already closed, trail remainder
- TP1 hit? Ã¢â€ â€™ MANAGE Ã¢â‚¬â€ close 35%, move SL to breakeven
- In profit? Ã¢â€ â€™ HOLD Ã¢â‚¬â€ wait for TP1
- In drawdown? Ã¢â€ â€™ HOLD SL Ã¢â‚¬â€ do not move it

**3. Structure Validity (4H SMC)**
- Runs `detect_bos_choch(k4h)` to check if 4H trend has reversed
- If structure turned AGAINST the trade Ã¢â€ â€™ flags as INVALIDATED
- If 1H ChoCh detected against trade Ã¢â€ â€™ soft warning, partial exit suggestion

**4. Exhaustion Check**
- RSI > 75 on a long in profit Ã¢â€ â€™ suggests partial close
- RSI < 25 on a short in profit Ã¢â€ â€™ suggests partial close

**5. Funding Pressure**
- If funding > 0.10% on a long Ã¢â€ â€™ suggests taking TP1 early
- If funding < -0.05% on a short Ã¢â€ â€™ suggests taking TP1 early

---

## Output Format

```
Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
  Ã°Å¸â€œâ€¹ POSITION MANAGER: [SYMBOL]
  [datetime PHT]
Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

POSITION SUMMARY
  [dir_emoji] [DIRECTION]  |  Token: [type]
  Entry       : [price]
  Current     : [price]  ([+/- move%] from entry)
  [emoji] Unreal. P&L : $[+/- amount]  (estimated)

LEVELS
  SL          : [price]   ([dist%] away / Ã¢â€ Â HIT)
  TP1 (35%)   : [price]   ([dist%] away / Ã¢â€ Â HIT)
  TP2 (40%)   : [price]   ([dist%] away / Ã¢â€ Â HIT)
  TP3 (25%)   : Trailing (trail at SL dist after TP2)

STRUCTURE CHECK (4H)
  4H Trend    : [BULLISH/BEARISH/RANGING]
  1H Trend    : [trend]  |  MSS: [YES/None]
  Validity    : [Ã¢Å“â€¦ Valid / Ã¢ÂÅ’ INVALIDATED]
  RSI (1H)    : [value]
  Funding     : [rate]%

Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
  STATUS: [Ã°Å¸â€Â´ SL HIT / Ã°Å¸Å¸Â¢ TP1 HIT / Ã°Å¸Å¸Â¢ TP2 HIT / Ã¢Å¡Â Ã¯Â¸Â INVALID / Ã°Å¸Å¸Â¡ IN PLAY]
Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

MANAGEMENT ADVICE
  Ã¢â€ â€™ [action 1]
  Ã¢â€ â€™ [action 2]
  Ã¢Å¡Â Ã¯Â¸Â [warning if applicable]
```

---

## Management Rules Enforced

These are pulled directly from `trading_rules.md`:

| Condition | Required Action |
|---|---|
| SL hit | Close immediately. Do NOT move stop. |
| TP1 hit | Close 35%. Move SL Ã¢â€ â€™ Entry (breakeven). |
| TP2 hit | Close 40%. Activate trailing stop on remaining 25%. |
| Structure invalidated | Consider full exit Ã¢â‚¬â€ trade thesis broken. |
| 3+ consecutive losses | 24-hour cooldown (flagged in advice). |

---

## Telegram Summary

Sends: symbol, direction, current price, P&L, level distances, status, and top 3 advice items.

---

## ACTIVATION KEYWORDS
manage | manage trade | check my position | how is my trade |
should I close | P&L on | position update | trade status
