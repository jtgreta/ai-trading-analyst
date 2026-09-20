# Trading Routine and Session Windows (PHT / UTC+8)

This document defines the daily operational rhythm and high-probability trading
windows.

[TOC]

## Daily prep (the routine)

The goal of the prep phase is to avoid "forcing" trades and only execute on
high-conviction setups.

| Time (PHT) | Action | Command | Goal |
| :--- | :--- | :--- | :--- |
| **2:45 PM** | Review open positions | `tools/manage.py SYM DIR E SL TP1 TP2` | Check open swing positions. Get live P&L and management advice |
| **3:00 PM** | Market bias check | `tools/market_bias.py` | Get RISK ON / RISK OFF / NEUTRAL verdict before scanning |
| **3:05 PM** | Funding check | `tools/funding.py` | Flag coins with extreme funding. Avoid those directions |
| **3:10 PM** | Run scanner | `tools/scanner.py` | Identify top movers and SMC-ranked coins for the session |
| **3:20 PM** | Deep analysis | `tools/scalper.py X` | If a Grade A (score >= 8) setup exists, run scalper |
| **5:00 PM** | London fade | - | No new entries unless a perfect swing setup appears |
| **9:00 PM** | Re-run bias | `tools/market_bias.py` | Confirm bias hasn't flipped since London open |
| **9:05 PM** | Re-run scanner | `tools/scanner.py` | Market rotates. Check for new priority coins |
| **9:15 PM** | Final analysis | `tools/scalper.py X` | Run scalper on top 1-2 NY picks |
| **9:30 PM** | Execution | - | Enter if score >= 6 and all checklist items are checked |
| **11:30 PM** | Trade management | `tools/manage.py` | Manage open positions. Be extremely selective about new entries |
| **12:00 AM** | Hard stop | - | No new entries regardless of setup quality |
| **Post-trade** | Log every trade | `tools/journal.py log ...` | Record outcome immediately - win, loss, or BE |
| **Weekend** | Weekly review | `tools/journal.py review` | Mandatory compliance + performance review |

## Pre-session checklist (run in order before any trade)

Each step must pass before proceeding to the next.

```text
Step 1 - Bias
  python tools/market_bias.py
  RISK ON  -> look for longs
  RISK OFF -> look for shorts
  NEUTRAL  -> grade A only, reduce size 50%
  STAY OUT -> wrong session window, no trades

Step 2 - Funding (on any coin you are considering)
  python tools/funding.py SYMBOL
  If funding > 0.10%  -> do NOT long this coin
  If funding < -0.05% -> do NOT short this coin

Step 3 - Discovery
  python tools/scanner.py
  Get shortlist; look for priority score >= 4

Step 4 - Analysis
  python tools/scalper.py SYMBOL
  Must score >= 6 and pass all three hard filters (HF-1/2/3)

Step 5 - Pre-entry mental check
  Session window is London or NY overlap
  Score >= 6 (Grade B or A)
  Entry is at FVG / OB / OTE - not a chase
  Stop-loss is set BEFORE clicking enter
  Risk <= $4.00
  Daily loss limit NOT hit
  Emotional state: neutral
```

## Post-trade protocol

Always log every completed trade immediately:

```powershell
python tools/journal.py log SYMBOL DIR ENTRY SL TP1 TP2 GRADE SCORE OUTCOME [NOTE]
```

Outcomes: `win_tp1`, `win_tp2`, `win_tp3`, `win_early`, `loss_sl`,
`loss_early`, `be`.

Weekly review (every weekend):

```powershell
python tools/journal.py review   # compliance, win rate, expectancy, violations
python tools/journal.py stats    # all-time performance
```

## Recommended trading hours

| Window | PHT time | Quality | Action / rule |
| :--- | :--- | :--- | :--- |
| **Asian session** | 8:00 AM - 12:00 PM | Avoid | No new scalps. Manage positions only |
| **Pre-London** | 12:00 PM - 3:00 PM | Low | Prep phase. Run bias + funding checks |
| **London open** | 3:00 PM - 5:00 PM | Good | Grade A setups only (score >= 8) |
| **London-NY gap** | 5:00 PM - 9:00 PM | Moderate | No new entries unless swing setup is perfect |
| **Pre-NY prep** | 9:00 PM - 9:30 PM | Prep | Re-run bias + scanner. Finalize watchlist |
| **NY overlap** | 9:30 PM - 12:00 AM | PRIME | Best window. Enter on score >= 6 |
| **Off-hours** | 12:00 AM+ | Stop | Hard stop. No new entries |

## See also

- [Trading rules](trading_rules.md)
- [Trading math](trading_math.md)
- [Project overview](PROJECT.md)