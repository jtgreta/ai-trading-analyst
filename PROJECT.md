# Trading Analyst — Project Documentation
**Owner:** jtgreta | **Status:** Active — Manual Analysis Tool  
**Last updated:** 2026-06-08 | **Session continuity doc**

---

## Project Overview

A set of AI-assisted skills for **manual institutional crypto trading analysis**. Jerome types a prompt, the AI fetches live Binance Futures data, runs full SMC analysis (BOS/ChoCh, FVG, Order Blocks, OTE, Inducement), outputs results to terminal, and sends a summary to Telegram.

The system covers the full trade lifecycle:
- **Pre-session**: market bias + funding check
- **Discovery**: scanner
- **Analysis**: scalper / hunter / swing
- **Execution**: graded trade plans with ATR stops
- **Management**: position monitor with live P&L
- **Review**: trade journal + weekly compliance tracker

---

## The Four Trading Philosophies (SMC)

### 0. Pre-Session Layer 📊
**Goal**: Know the macro context before touching any coin.
- **Market Bias** (`skill_market_bias.py`): BTC/ETH structure + funding + LS ratio → RISK ON / RISK OFF / NEUTRAL verdict. Run first, every session.
- **Funding** (`skill_funding.py`): Scan all futures funding rates. Flag coins to avoid based on direction.

### 1. The Scalper / Scanner (Momentum) 🚀
**Goal**: Quick wins by riding existing structural trends.
**Philosophy**: "Trade the institutional order flow."
- **Scanner** (`skill_scanner_run.py`): Find high-volume movers, rank by SMC priority (BOS, FVG, IDM, OB, OTE).
- **Scalper** (`skill_scalper_analyze.py`): Deep analysis on 1 coin. Enforces 4H structure gate, OTE/FVG/OB entry targeting.
- **Grade A** = Full Margin, **Grade B** = Half Margin.
- **Best for**: Day trading during London/NY open.

### 2. The Hunter (Pre-Breakout) 💎
**Goal**: Catch the breakout before it happens.
**Philosophy**: "Find the coil, ride the explosion."
- **Hunter Filter** (`skill_hunter_filter.py`): Standalone ticker screen. Vol >$100M, range 3–25%, |change| <15%.
- **Hunter Coil** (`skill_hunter_coil.py`): Score named symbol(s) on coil criteria A–F + Inducement bonus.
- **Hunter Scan** (`skill_hunter_scan.py`): Full pipeline — filter → score → trade plan → Telegram. Preferred.

### 3. The Swing (Macro Trend) 📈
**Goal**: Multi-day holds of 15–40%+.
- **Swing** (`skill_swing_analyze.py`): 1W macro gate, 1D FVG entry, 4H ATR stops.

### 4. Post-Trade Layer 📓
- **Manager** (`skill_manage.py`): Live position monitor. Calculates P&L, checks structure validity, issues management advice.
- **Journal** (`skill_journal.py`): Log trades, calculate win rate + expectancy, compliance tracker, weekly review.

---

## The Daily Routine (Session Timing)

All times are **PHT (UTC+8)**:

| Time | Window | Command | Action |
|---|---|---|---|
| **2:45 PM** | Pre-London | `skill_manage.py` | Check open positions. |
| **3:00 PM** | London Prep | `skill_market_bias.py` | Get RISK ON/OFF verdict first. |
| **3:05 PM** | London Prep | `skill_funding.py` | Check funding on candidates. |
| **3:10 PM** | London Open | `skill_scanner_run.py` | Find movers and SMC picks. |
| **3:20 PM** | London Open | `skill_scalper_analyze.py X` | Grade A setups only. |
| **9:00 PM** | Pre-NY | `skill_market_bias.py` | Re-confirm bias. |
| **9:05 PM** | Pre-NY | `skill_scanner_run.py` | Re-scan for NY session. |
| **9:15 PM** | Pre-NY | `skill_scalper_analyze.py X` | Final analysis on top picks. |
| **9:30 PM** | NY Overlap | — | **Enter** if Score ≥ 6, all ✅. |
| **11:30 PM** | Late NY | `skill_manage.py` | Management only. |
| **12:00 AM** | Hard Stop | — | No new entries. |
| **Post-trade** | Any | `skill_journal.py log` | Log every completed trade. |
| **Weekend** | — | `skill_journal.py review` | Mandatory weekly review. |
| **9:30 PM – 12:00 AM** | London–NY Overlap | ⭐⭐⭐⭐⭐ **PRIME WINDOW**. Both sessions active. Enter on score ≥ 6. |
| **12:00 AM+** | Off-hours | ❌ **No new entries** regardless of setup quality. |

---

## The 4 Mandatory Output Sections

Every analysis script (Scalper, Swing, etc.) outputs exactly 4 sections:

1. **SESSION CHECK**: Current PHT window + quality rating. Blocks entries if Asian/Midnight.
2. **MARKET STRUCTURE SUMMARY**: High timeframe and low timeframe trends, recent BOS/ChoCh, nearest FVG and OB, and liquidity pools.
3. **TRADE PLAN** (if score ≥ 6) OR **WAITING ROOM** (if score < 6 or blocked):
   - **Trade Plan**: Precise entry, ATR-based stops, RR ≥ 1:2, graded position sizing.
   - **Waiting Room**: Replaces dead-end "BLOCKED". Tells you exactly *what* to wait for, key levels, and the next check time.
4. **TELEGRAM SUMMARY**: Compact output sent to the channel.

---

## Directory Structure

```
C:\Users\Jerome\ai-trading-analyst
    ├── AGENTS.md              ← AI assistant instructions (auto-read by any AI tool)
    ├── PROJECT.md             ← this file
    │
    ├── ── SKILLS (stored globally in ~/.agents/skills/) ──
    ├── ~/.agents/skills
    │       ├── market-bias
    │       │       SKILL.md      ← Pre-Session Bias Briefing
    │       ├── funding
    │       │       SKILL.md      ← Funding Rate Scanner
    │       ├── hunter
    │       │       SKILL.md      ← Pre-Breakout Coil Logic (SMC)
    │       ├── scalper
    │       │       SKILL.md      ← Precision Execution (SMC)
    │       ├── scanner
    │       │       SKILL.md      ← Momentum Discovery (SMC)
    │       ├── swing
    │       │       SKILL.md      ← Multi-day Trend (SMC)
    │       ├── manage
    │       │       SKILL.md      ← Position Manager
    │       └── journal
    │               SKILL.md      ← Trade Journal & Review
    │
    ├── ── PRE-SESSION ──
    ├── skill_market_bias.py      ← BTC/ETH structure + funding + LS → RISK ON/OFF verdict
    ├── skill_funding.py          ← Funding rate scanner; flags coins to avoid
    │
    ├── ── DISCOVERY ──
    ├── skill_scanner_filter.py   ← Standalone ticker filter (top 10 movers)
    ├── skill_scanner_run.py      ← Full SMC scanner pipeline → Telegram
    │
    ├── ── ANALYSIS ──
    ├── skill_scalper_analyze.py      ← 5-TF scalper: hard filters, OTE, waiting room
    ├── skill_scalper_deep_analyze.py ← Supplementary: BB, MACD, LS ratio deep dive
    ├── skill_hunter_filter.py        ← Hunter standalone filter (outputs symbol list)
    ├── skill_hunter_coil.py          ← Coil scorer for named symbols (A–F + IDM bonus)
    ├── skill_hunter_scan.py          ← Full hunter pipeline → Telegram
    ├── skill_swing_analyze.py        ← 1W/1D/4H swing analysis, FVG entry, ATR stops
    │
    ├── ── LIFECYCLE ──
    ├── skill_manage.py    ← Live position monitor: P&L, structure check, advice
    ├── skill_journal.py   ← Trade log + weekly review + compliance tracker
    │
    ├── ── CORE LIBRARY ──
    ├── trading_utils.py   ← All SMC logic, session gating, sizing, formatters, API helpers
    │
    ├── ── RETIRED (stubs only — use replacements above) ──
    ├── check_bias.py        ← Retired → use skill_market_bias.py
    ├── long_funding_plan.py ← Retired → use skill_funding.py
    │
    └── PROJECT.md  ← this file
```

---

## Python File Naming Convention

**All Python files created for these skills must follow this format:**
`skill_<skillname>_<purpose>.py`

---

## Recommended Workflow

```
1. "scan the market"  (Scanner)
       ↓ Finds movers, outputs SMC-ranked list.
       ↓ Pick a priority coin and run: "scalp [SYMBOL]"

2. "hunt" (Hunter)
       ↓ Scans for pre-breakout coils.
       ↓ If qualified (score ≥ 6), outputs full trade plan. No need to run scalper.

3. "swing [SYMBOL]" (Swing)
       ↓ Checks 1W macro trend, sets entry at 1D FVG, calculates 4H ATR stop.
```

---

## Telegram Configuration

**Bot Token:** Loaded from .env file  
**Channel ID:** `-1003922568527`

---

## Account Sizing Reference ($100)

**Max Risk**: **$3.00 – $4.00 per trade**. If actual risk exceeds this, margin is automatically reduced.
**Min RR**: 1:2 (TP1 must be ≥ 2× SL distance).

**Scalping (Scanner / Scalper / Hunter)**:
| Token Type | Leverage | Full Margin | Half Margin | Max SL% |
|---|---|---|---|---|
| Major (BTC/ETH/BNB) | 10x | $10 | $5 | 3% |
| Mid-cap | 5x | $7 | $3.50 | 8.5% |
| New/Meme/AI | 3x | $5 | $2.50 | 20% |

**Swing (Swing skill)**:
| Token Type | Leverage | Full Margin | Half Margin | Max SL% |
|---|---|---|---|---|
| Major (BTC/ETH/BNB) | 5x | $10 | $5 | 6% |
| Mid-cap | 3x | $7 | $3.50 | 14% |
| New/Meme/AI | 2x | $5 | $2.50 | 30% |

Grade A (score 8–10) → full margin. Grade B (score 6–7) → half margin. Grade C → Waiting Room.