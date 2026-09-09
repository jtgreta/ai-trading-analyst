# Trading Routine & Session Windows (PHT / UTC+8)

This document defines the daily operational rhythm and high-probability trading windows.

---

## 1. Daily Prep (The Routine)
The goal of the prep phase is to avoid "forcing" trades and only execute on high-conviction setups.

| Time (PHT) | Action | Command | Goal |
| :--- | :--- | :--- | :--- |
| **2:45 PM** | **Review Open Positions** | `scripts/manage.py SYM DIR E SL TP1 TP2` | Check open swing positions. Get live P&L and management advice. |
| **3:00 PM** | **Market Bias Check** | `scripts/market_bias.py` | Get RISK ON / RISK OFF / NEUTRAL verdict **before** scanning. |
| **3:05 PM** | **Funding Check** | `scripts/funding.py` | Flag coins with extreme funding. Avoid those directions. |
| **3:10 PM** | **Run Scanner** | `scripts/scanner_run.py` | Identify top movers and SMC-ranked coins for the session. |
| **3:20 PM** | **Deep Analysis** | `scripts/scalper_analyze.py X` | If a **Grade A (Score >= 8)** setup exists → run Scalper. |
| **5:00 PM** | **London Fade** | — | No new entries unless a perfect Swing setup appears. |
| **9:00 PM** | **Re-Run Bias** | `scripts/market_bias.py` | Confirm bias hasn't flipped since London open. |
| **9:05 PM** | **Re-Run Scanner** | `scripts/scanner_run.py` | Market rotates. Check for new priority coins. |
| **9:15 PM** | **Final Analysis** | `scripts/scalper_analyze.py X` | Run Scalper on top 1–2 NY picks. |
| **9:30 PM** | **Execution** | — | Enter if **Score >= 6** and all checklist items are checked. |
| **11:30 PM** | **Trade Management** | `scripts/manage.py` | Manage open positions. Be extremely selective about new entries. |
| **12:00 AM** | **Hard Stop** | — | **No new entries** regardless of setup quality. |
| **Post-trade** | **Log Every Trade** | `scripts/journal.py log ...` | Record outcome immediately — win, loss, or BE. |
| **Weekend** | **Weekly Review** | `scripts/journal.py review` | Mandatory compliance + performance review. |

---

## 2. Pre-Session Checklist (Run in Order Before Any Trade)

Each step must pass before proceeding to the next.

```
Step 1 — Bias
  python scripts/market_bias.py
  RISK ON  → look for longs
  RISK OFF → look for shorts
  NEUTRAL  → Grade A only, reduce size 50%
  STAY OUT → wrong session window, no trades

Step 2 — Funding (on any coin you are considering)
  python scripts/funding.py SYMBOL
  If funding > 0.10%  → do NOT long this coin
  If funding < -0.05% → do NOT short this coin

Step 3 — Discovery
  python scripts/scanner_run.py
  Get shortlist; look for Priority Score >= 4

Step 4 — Analysis
  python scripts/scalper_analyze.py SYMBOL
  Must score >= 6 and pass all three hard filters (HF-1/2/3)

Step 5 — Pre-entry mental check
  [ ] Session window is London or NY Overlap
  [ ] Score >= 6 (Grade B or A)
  [ ] Entry is at FVG / OB / OTE — not a chase
  [ ] Stop-loss is set BEFORE clicking enter
  [ ] Risk <= $4.00
  [ ] Daily loss limit NOT hit
  [ ] Emotional state: neutral
```

---

## 3. Post-Trade Protocol

Always log every completed trade immediately:
```
python scripts/journal.py log SYMBOL DIR ENTRY SL TP1 TP2 GRADE SCORE OUTCOME [NOTE]

Outcomes: win_tp1  win_tp2  win_tp3  win_early  loss_sl  loss_early  be
```

Weekly review (every weekend):
```
python scripts/journal.py review   → compliance, win rate, expectancy, violations
python scripts/journal.py stats    → all-time performance
```

---

## 4. Recommended Trading Hours

| Window | PHT Time | Quality | Action / Rule |
| :--- | :--- | :--- | :--- |
| **Asian Session** | 8:00 AM – 12:00 PM | Avoid | No new scalps. Manage positions only. |
| **Pre-London** | 12:00 PM – 3:00 PM | Low | Prep phase. Run bias + funding checks. |
| **London Open** | 3:00 PM – 5:00 PM | Good | Grade A setups only (Score >= 8). |
| **London–NY Gap** | 5:00 PM – 9:00 PM | Moderate | No new entries unless Swing setup is perfect. |
| **Pre-NY Prep** | 9:00 PM – 9:30 PM | Prep | Re-run bias + scanner. Finalize watchlist. |
| **NY Overlap** | 9:30 PM – 12:00 AM | PRIME | BEST WINDOW. Enter on Score >= 6. |
| **Off-hours** | 12:00 AM+ | Stop | Hard stop. No new entries. |
