---
name: journal
description: >
  Trade logger, compliance tracker, and weekly review generator. Logs every
  completed trade with symbol, direction, entry, SL, TPs, grade, score, and
  outcome. Calculates win rate, expectancy, compliance rate, and average RR
  achieved. Supports the mandatory weekly review from trading_rules.md.
  Stores trades in journal.json.
version: institutional
---

# Trade Journal — Performance & Compliance Tracker

## Purpose
The trading_rules.md requires a weekly review covering:
- Compliance rate (target ≥ 80%)
- Rule violations
- Win rate and average RR
- Psychological assessment

Without logging, none of these can be measured. This skill provides the
infrastructure for that review and for tracking whether the system is
actually producing positive expectancy over time.

---

## Runtime Notes
- PowerShell runs internally — use `python`
- trading_utils.py must be in the same directory
- Saves trades to `journal.json` in the same directory

---

## ⚠️ PYTHON FILE NAMING CONVENTION — MANDATORY

File name: `skill_journal.py`

**Before creating, ALWAYS check if it already exists:**
```powershell
Test-Path "C:\Users\Jerome\gemini-trading-analyst\skill_journal.py"
```
If found, run it directly. Do not rewrite.

---

## Commands

### Log a Trade
```powershell
python skill_journal.py log SYMBOL DIR ENTRY SL TP1 TP2 GRADE SCORE OUTCOME [NOTE]
```

Arguments (in order):
| Arg | Description | Example |
|---|---|---|
| SYMBOL | Binance Futures ticker | SOLUSDT |
| DIR | LONG or SHORT | LONG |
| ENTRY | Actual fill price | 145.50 |
| SL | Stop-loss level | 140.00 |
| TP1 | First take-profit | 156.00 |
| TP2 | Second take-profit | 165.00 |
| GRADE | A, B, or C | B |
| SCORE | System score 0–10 | 7 |
| OUTCOME | See table below | win_tp1 |
| NOTE | Optional free text | "news pump entry" |

**Valid OUTCOME values:**
| Outcome | Result | Meaning |
|---|---|---|
| `win_tp1` | WIN | Closed at TP1 (35%) |
| `win_tp2` | WIN | Closed at TP2 (40%) |
| `win_tp3` | WIN | Closed at TP3 / trailing stop |
| `win_early` | WIN | Manual exit in profit |
| `loss_sl` | LOSS | Stopped out at SL |
| `loss_early` | LOSS | Manual exit at a loss |
| `be` | BE | Breakeven (SL moved to entry, hit) |

### Other Commands

```powershell
# Show last N trades (default 10)
python skill_journal.py list [N]

# Weekly review — last 7 days + compliance check
python skill_journal.py review

# All-time statistics
python skill_journal.py stats

# Remove a trade by ID
python skill_journal.py delete ID
```

---

## Activation Triggers
- "log trade"
- "log win" / "log loss"
- "journal [SYMBOL]"
- "weekly review"
- "what's my win rate"
- "compliance check"
- "trading stats"
- "how am I doing"

---

## What Gets Calculated

### Per Trade (auto-calculated on log):
- **RR achieved**: based on outcome and price levels
  - win_tp1 → (TP1 - entry) / (entry - SL)
  - win_tp2 → (TP2 - entry) / (entry - SL)
  - loss_sl → -1.0 (full loss)
  - be → 0.0
- **Compliant**: True if grade is A or B AND score ≥ 6
- **Violation**: auto-detected if grade C or score < 6

### Stats (computed over a window):
- **Win Rate**: wins / (wins + losses)
- **Expectancy**: (win% × avg_win_RR) + (loss% × avg_loss_RR)
  - Positive expectancy = system is working
  - Negative expectancy after 10+ trades = execution problem, not system problem
- **Compliance Rate**: compliant_trades / total_trades × 100
- **Max Loss Streak**: longest consecutive loss run (triggers 24h cooldown at 3)

---

## Compliance Rules (auto-flagged as violations)

| Violation | What triggers it |
|---|---|
| Grade C trade | grade == "C" |
| Score below minimum | score < 6 |

Note: session timing violations, SL movement, and revenge trades cannot be
auto-detected from the log alone. Use the weekly review questions to self-assess.

---

## Output Formats

### `log` output:
```
  ✅ Trade #7 logged
  🟢 SOLUSDT LONG | Grade B | Score 7/10
  Outcome: Closed at TP1 (35%) | RR: +2.00
```

### `stats` / `review` output:
```
════════════════════════════════════
  📊 TRADING STATS — THIS WEEK
════════════════════════════════════

  Total Trades    : 8
  ✅ Win Rate     : 62.5%  (5W / 3L / 0BE)
  ✅ Expectancy   : +0.84R per trade
  Avg Win RR      : +2.10R
  Avg Loss RR     : -0.95R
  Max Loss Streak : 2

  ✅ Compliance   : 87.5%  (target ≥ 80%)
  Rule Violations : 1

  Grade Mix       : A=2  B=5  C=1
```

### `list` output:
```
  #     Date               Symbol       Dir    Grade  Score    RR      Result
  ─────────────────────────────────────────────────────────────────────────
  7     2026-06-08 21:30   SOLUSDT      LONG   B      7/10   +2.00R  🟢 WIN
  6     2026-06-07 22:15   ETHUSDT      SHORT  A      9/10   -1.00R  🔴 LOSS  ⚠️
```

---

## Storage

Trades are saved to `journal.json` in the project directory.

Format (per trade):
```json
{
  "id": 7,
  "timestamp": "2026-06-08 21:30",
  "symbol": "SOLUSDT",
  "direction": "LONG",
  "entry": 145.5,
  "sl": 140.0,
  "tp1": 156.0,
  "tp2": 165.0,
  "grade": "B",
  "score": 7,
  "outcome": "win_tp1",
  "result": "WIN",
  "rr_achieved": 2.0,
  "compliant": true,
  "violation": null,
  "note": ""
}
```

Do NOT edit `journal.json` manually. Use `delete ID` to remove entries.

---

## ACTIVATION KEYWORDS
journal | log trade | log win | log loss | weekly review | trading stats |
what's my win rate | compliance | how am I doing | trade history | review
