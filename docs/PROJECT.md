# Project Documentation

A set of AI-assisted skills for manual institutional crypto trading analysis
on Binance Futures. The user types a prompt, the AI fetches live market data,
runs full SMC analysis (BOS/ChoCh, FVG, Order Blocks, OTE, Inducement), outputs
results to terminal, and sends a summary to Telegram.

*Owner: ai-trading-analyst contributors | Status: Active - Manual Analysis
Tool | Last updated: 2026-09-19 | Session continuity doc*

[TOC]

## Project overview

The system covers the full trade lifecycle:

- **Pre-session**: market bias + funding check.
- **Discovery**: scanner.
- **Analysis**: scalper / hunter / swing.
- **Execution**: graded trade plans with ATR stops.
- **Management**: position monitor with live P&L.
- **Review**: trade journal + weekly compliance tracker.

## The four trading philosophies (SMC)

### 0. Pre-session layer

**Goal**: know the macro context before touching any coin.

- **Market Bias** (`tools/market_bias.py`): BTC/ETH structure + funding + LS
  ratio -> RISK ON / RISK OFF / NEUTRAL verdict. Run first, every session.
- **Funding** (`tools/funding.py`): scan all futures funding rates. Flag
  coins to avoid based on direction.

### 1. The scalper / scanner (momentum)

**Goal**: quick wins by riding existing structural trends.

**Philosophy**: "Trade the institutional order flow."

- **Scanner** (`tools/scanner.py`): find high-volume movers, rank by SMC
  priority (BOS, FVG, IDM, OB, OTE).
- **Scalper** (`tools/scalper.py`): deep analysis on 1 coin. Enforces 4H
  structure gate, OTE/FVG/OB entry targeting.
- **Grade A** = full margin, **Grade B** = half margin.
- **Best for**: day trading during London/NY open.

### 2. The hunter (pre-breakout)

**Goal**: catch the breakout before it happens.

**Philosophy**: "Find the coil, ride the explosion."

- **Hunter Filter** (`tools/hunter_filter.py`): standalone ticker screen. Vol
  >$100M, range 3-25%, |change| <15%.
- **Hunter Coil** (`tools/hunter_coil.py`): score named symbol(s) on coil
  criteria A-F + Inducement bonus.
- **Hunter Scan** (`tools/hunter.py`): full pipeline - filter -> score ->
  trade plan -> Telegram. Preferred.

### 3. The swing (macro trend)

**Goal**: multi-day holds of 15-40%+.

- **Swing** (`tools/swing.py`): 1W macro gate, 1D FVG entry, 4H ATR stops.

### 4. Post-trade layer

- **Manager** (`tools/manage.py`): live position monitor. Calculates P&L,
  checks structure validity, issues management advice.
- **Journal** (`tools/journal.py`): log trades, calculate win rate +
  expectancy, compliance tracker, weekly review.

## The daily routine (session timing)

All times are **PHT (UTC+8)**:

| Time | Window | Command | Action |
| :--- | :--- | :--- | :--- |
| **2:45 PM** | Pre-London | `tools/manage.py` | Check open positions |
| **3:00 PM** | London Prep | `tools/market_bias.py` | Get RISK ON/OFF verdict first |
| **3:05 PM** | London Prep | `tools/funding.py` | Check funding on candidates |
| **3:10 PM** | London Open | `tools/scanner.py` | Find movers and SMC picks |
| **3:20 PM** | London Open | `tools/scalper.py X` | Grade A setups only |
| **9:00 PM** | Pre-NY | `tools/market_bias.py` | Re-confirm bias |
| **9:05 PM** | Pre-NY | `tools/scanner.py` | Re-scan for NY session |
| **9:15 PM** | Pre-NY | `tools/scalper.py X` | Final analysis on top picks |
| **9:30 PM** | NY Overlap | - | **Enter** if score >= 6, all checks pass |
| **11:30 PM** | Late NY | `tools/manage.py` | Management only |
| **12:00 AM** | Hard stop | - | No new entries |
| **Post-trade** | Any | `tools/journal.py log` | Log every completed trade |
| **Weekend** | - | `tools/journal.py review` | Mandatory weekly review |

Session notes:

- **9:30 PM - 12:00 AM** (London-NY overlap): prime window, both sessions
  active, enter on score >= 6.
- **12:00 AM+** (off-hours): no new entries regardless of setup quality.

## The four mandatory output sections

Every analysis script (scalper, swing, and others) outputs exactly 4 sections:

1.  **Session check**: current PHT window + quality rating. Blocks entries if
    Asian/Midnight.
1.  **Market structure summary**: high timeframe and low timeframe trends,
    recent BOS/ChoCh, nearest FVG and OB, and liquidity pools.
1.  **Trade plan** (if score >= 6) OR waiting room (if score < 6 or blocked):
    - Trade plan: precise entry, ATR-based stops, RR >= 1:2, graded position
      sizing.
    - Waiting room: replaces dead-end "BLOCKED". Tells you exactly what to wait
      for, key levels, and the next check time.
1.  **Telegram summary**: compact output sent to the channel.

## Directory structure

```text
ai-trading-analyst/
  AGENTS.md              # AI assistant instructions (read by any AI tool)
  README.md              # Public landing page
  config/
    trading.json.example # Copy to trading.json and customize (gitignored)
    trading_profile.md   # Your personal profile (gitignored, see docs/trading_profile.md template)
  docs/
    PROJECT.md           # This file
    trading_rules.md     # Non-negotiable rules, sizing, grading
    trading_routine.md   # Daily session windows and prep checklist
    trading_indicators.md# SMC / indicator reference + indicator math
    trading_math.md      # Quantitative edge: expectancy, Kelly, ruin, stats
    trading_profile.md   # Trader profile template
  .agents/skills/        # Cross-tool skills (see SKILL.md in each folder)
  tools/               # Python engines + shared trading/ package
```

## Script location convention

All Python execution helpers live in the repo `tools/` folder as
`tools/<name>.py`. Skills (the prompts/workflows) live in
`.agents/skills/<skill-name>/SKILL.md` and reference these scripts from the
repo root. The shared `tools/trading` package is imported directly from the
same folder (no sys.path bootstrap). `config/trading.json` (copied from
`.example`) overrides the built-in sizing defaults at runtime.

## Recommended workflow

```text
1. "scan the market"  (Scanner)
     Finds movers, outputs SMC-ranked list.
     Pick a priority coin and run: "scalp [SYMBOL]"

2. "hunt"             (Hunter)
     Scans for pre-breakout coils.
     If qualified (score >= 6), outputs full trade plan.
     No need to run scalper after.

3. "swing [SYMBOL]"   (Swing)
     Checks 1W macro trend, sets entry at 1D FVG,
     calculates 4H ATR stop.
```

## Telegram configuration

Bot token / channel ID: loaded from `.env` (`TG_TOKEN`, `TG_CHAT`) at repo
root. Leave empty to run scripts locally without Telegram dispatch.

## Account sizing reference (built-in defaults)

**Max risk**: $3.00 - $4.00 per trade. If actual risk exceeds this, margin is
automatically reduced.

**Min RR**: 1:2 (TP1 must be >= 2x SL distance).

These are the defaults baked into the `tools/trading` package - override via
`config/trading.json` (see `config/trading.json.example`).

**Scalping (scanner / scalper / hunter)**:

| Token type | Leverage | Full margin | Half margin | Max SL% |
| :--- | :--- | :--- | :--- | :--- |
| Major (BTC/ETH/BNB) | 10x | $10 | $5 | 3% |
| Mid-cap | 5x | $7 | $3.50 | 8.5% |
| New/Meme/AI | 3x | $5 | $2.50 | 20% |

**Swing (swing skill)**:

| Token type | Leverage | Full margin | Half margin | Max SL% |
| :--- | :--- | :--- | :--- | :--- |
| Major (BTC/ETH/BNB) | 5x | $10 | $5 | 6% |
| Mid-cap | 3x | $7 | $3.50 | 14% |
| New/Meme/AI | 2x | $5 | $2.50 | 30% |

Grade A (score 8-10) -> full margin. Grade B (score 6-7) -> half margin.
Grade C -> waiting room.

## See also

- [Trading math](trading_math.md)
- [Trading rules](trading_rules.md)
- [Trading routine](trading_routine.md)
- [Trading indicators](trading_indicators.md)
- [Trading profile](trading_profile.md)