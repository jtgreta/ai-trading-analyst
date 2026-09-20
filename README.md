# AI Trading Analyst

Institutional-grade, AI-assisted crypto trading analysis on Binance Futures,
delivered as portable AI skills.

This repo turns any AI coding agent (opencode, Claude, Codex, Cursor, Gemini
CLI, Copilot, goose, and more) into a manual-analysis trading copilot. It runs
a full institutional workflow - market bias, funding check, scanner,
scalper/hunter/swing analysis, position management, trade journal - all through
natural-language prompts, with a complete graded trade plan and optional
Telegram dispatch.

[TOC]

> **Important:** Use this at your own risk. This is an AI-assisted analysis
> tool, not financial advice. All outputs are AI-generated and may contain
> errors - they are **not** guarantees of accuracy or future performance.
> Trading derivatives carries substantial risk of loss, including total loss of
> capital. **The authors and contributors are NOT responsible for any losses
> you may incur.** See full [Disclaimer & Risk Disclosure](DISCLAIMER.md) before
> using this Software.

## Highlights

- **SMC-based analysis engine**: BOS/ChoCh structure, Fair Value Gaps, Order
  Blocks, OTE Fibonacci, inducement/liquidity, ATR volatility stops.
- **Score-based grading**: Grade A/B/C with dynamic position sizing and a hard
  $3-$4 risk per trade by default.
- **WAITING ROOM discipline**: when there is no valid trade, every analysis
  explains *why not now* and *what would unlock one*.
- **Portable across AI tools**: skills in `.agents/skills/` (the cross-tool
  standard), helpers in `tools/`, config in `config/`, docs in `docs/`. Any
  compliant agent can run it.
- **4 mandatory output sections**: session check, market structure, trade plan
  or waiting room, Telegram summary.

## Repository layout

```text
ai-trading-analyst/
  AGENTS.md                  # Instructions read by any AI agent (the mandate)
  README.md                  # This file
  config/
    trading.json.example     # Copy to trading.json and customize
    trading_profile.md       # Your personal trader profile (gitignored)
  docs/
    PROJECT.md               # Project overview + full workflow
    trading_rules.md         # Non-negotiable rules, sizing, grading
    trading_routine.md       # Daily session windows & prep checklist
    trading_indicators.md    # SMC / indicator reference + indicator math
    trading_math.md          # Quantitative edge: expectancy, Kelly, ruin math
    trading_profile.md       # Trader profile template
  .agents/skills/            # Cross-tool skills (funding, hunter, scalper, ...)
  tools/                   # Python engines + shared trading/ package
```

## Quick start

### Prerequisites

- Python 3.9+ with `requests` (`pip install requests`).
- A Binance Futures account (analysis uses public endpoints only; no API key
  required to scan).
- Optional: a Telegram bot token + chat id for signal dispatch.

### Install

```powershell
git clone <this-repo-url>
cd ai-trading-analyst
pip install requests
```

### Configure (optional)

Copy the config template and set your account truth (capital, max risk per
trade, sizing rules):

```powershell
Copy-Item config\trading.json.example config\trading.json
```

Fill `.env` for Telegram (with no `.env` the scripts still run - they just
skip Telegram):

```text
TG_TOKEN=<bot token>
TG_CHAT=<chat id>
```

> `journal.json`, `config/trading_profile.md`, `config/trading.json`, and `.env` are
> gitignored - your personal data never gets committed.

## Usage

Open the repo in your AI agent and just ask. Example prompts:

| You say | What happens |
| :--- | :--- |
| `run the market bias` | BTC/ETH structure + funding + long/short ratio -> RISK ON/OFF verdict |
| `scan the market` | Finds movers, ranks by SMC priority, outputs shortlist |
| `hunt` | Pre-breakout coil scan across all tickers -> trade plan if score >= 6 |
| `scalp BTCUSDT` | 5-timeframe scalper analysis -> graded plan or waiting room |
| `swing SOLUSDT` | 1W/1D/4H swing analysis -> FVG entry, ATR stops |
| `check my position` | Live P&L + management advice from your entry/SL/TPs |
| `journal log ...` | Trade logging + weekly compliance review |
| `journal review` | Mandatory weekly compliance and performance review |

You can also run the engines directly:

```powershell
python tools/market_bias.py
python tools/scanner.py
python tools/scalper.py BTCUSDT
python tools/hunter.py
python tools/funding.py
python tools/manage.py BTCUSDT LONG 65000 64000 67000 69000
python tools/journal.py review
```

Full details in [PROJECT.md](docs/PROJECT.md) and
[trading_routine.md](docs/trading_routine.md).

## Skills

- Trading suite: `market-bias`, `funding`, `scanner`, `scalper`, `hunter`,
  `swing`, `manage`, `journal`.
- Market tools: `binance`, `crypto-market-rank`, `meme-rush`,
  `query-token-audit`, `query-token-info`, `trading-signal`.

Each lives in `.agents/skills/<name>/SKILL.md` and is auto-discovered by
skill-aware AI agents.

## How the mandate works

The trading philosophy is enforced through [AGENTS.md](AGENTS.md) and the docs:

1.  **Grade system**: Grade A (score 8-10) full margin, Grade B (6-7) half
    margin, Grade C (<6) goes to the WAITING ROOM.
1.  **Volatility windows**: aggression is tuned to PHT institutional sessions
    (London open, NY overlap), never blocking a valid setup.
1.  **Sizing is the safety valve**: max risk per trade (default $3-$4) via
    margin/leverage, enforced in the `tools/trading` package.
1.  **Hard rules never violated**: stop-loss set before entry, minimum RR 1:2,
    waiting room when nothing qualifies.

## License and disclaimer

MIT - see [LICENSE](LICENSE). Use it, fork it, modify it, learn from it.

**Before using this Software, you MUST read and agree to the
[Disclaimer & Risk Disclosure](DISCLAIMER.md).** The authors and contributors
are not responsible for any trading losses. If this tool helps you - congrats.
If it doesn't - that's on you, not us.

## See also

- [Project overview](docs/PROJECT.md)
- [Trading math](docs/trading_math.md)
- [Trading rules](docs/trading_rules.md)
- [Trading routine](docs/trading_routine.md)
- [Trading indicators](docs/trading_indicators.md)