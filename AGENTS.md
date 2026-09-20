# Trading Mandate: Institutional Adaptive Mode

This is the operating mandate for any AI agent working in this repository.
Follow these rules whenever you run a trading analysis or a skills workflow.

[TOC]

## Repo layout

- **Skills live in** `.agents/skills/<skill-name>/SKILL.md`, the cross-tool
  standard location. They are auto-discovered by opencode, Claude, Codex,
  Cursor, Gemini CLI, Copilot, goose, and others.
- **Python helpers live in** `tools/` (`tools/<script>.py`). Engines import
  the shared `tools/trading` package (public API mirrors the former
  `trading_utils.py`) directly from the same folder - no sys.path bootstrap or
  pip install needed.
- **Docs live in** `docs/` (`PROJECT.md`, `trading_rules.md`,
  `trading_routine.md`, `trading_indicators.md`, `trading_math.md`,
  `trading_profile.md`). `trading_math.md` is the quantitative foundation
  (expectancy, Kelly sizing, risk of ruin, streak statistics). Consult it when
  explaining why a rule exists or when sizing and session questions come up.
- **User config lives in** `config/`: `config/trading.json` (capital, max risk,
  sizing-rule overlay; loaded by the `tools/trading` package at runtime. Start
  from `config/trading.json.example`) and `config/trading_profile.md` (the
  filled trader profile - gitignored, never committed; read it when coaching).
- Before running a script, check it exists with
  `Test-Path "tools\<script>.py"`. If found, run it directly - do not rewrite.
- Scripts available: `chart_gen.py`, `funding.py`, `hunter_coil.py`,
  `hunter_filter.py`, `hunter.py`, `journal.py`, `manage.py`, `market_bias.py`,
  `scalper.py`, `scanner_filter.py`, `scanner.py`, `swing.py`.
- Skills available: `chart-gen`, `funding`, `hunter`, `journal`, `manage`,
  `market-bias`, `scalper`, `scanner`, `swing` (trading suite) plus `binance`,
  `crypto-market-rank`, `find-skills`, `meme-rush`, `query-token-audit`,
  `query-token-info`, `trading-signal` (market tools).

## Core philosophy

**The edge is not having more signals. It is having the right signals at the
right time.**

Consistent compounding comes from trading high-conviction setups. While crypto
runs 24/7, institutional volume clusters in specific windows; we use those
windows to modulate aggressiveness, not to block opportunity.

## Execution rules

### Waiting room replaces dead-end blocks

- When no valid trade exists, every analysis outputs a full WAITING ROOM
  section.
- The WAITING ROOM tells the trader: why not now, what would unlock a trade,
  key levels to watch, patterns to look for, pre-conditions checklist, and when
  to check back.
- There is no output that ends without actionable information.

### Grade system (score based)

- **Grade A (score 8-10)**: full margin, high conviction, execute 24/7.
- **Grade B (score 6-7)**: half margin, good setup, moderate conviction,
  execute 24/7 with increased awareness of session volatility.
- **Grade C (score <6)**: WAITING ROOM. Not a trade - wait for conditions to
  improve.

### Volatility context (PHT / UTC+8)

- **Prime windows** (London open 3-5 PM and NY overlap 9:30 PM-12 AM): maximum
  aggression. High probability of impulsive, trending moves.
- **Early Asian pulse** (5-8 AM): moderate to high aggression. High opportunity
  for early trend setters and volatility breakouts.
- **Secondary windows** (London-NY gap 5-9 PM): moderate aggression. Favor
  setups with clear structural alignment.
- **Low-vol windows** (Asian session 8 AM-12 PM and off-hours 12 AM-3 PM):
  conservative aggression. Higher risk of choppy price action. Favor Grade A
  setups and strictly adhere to ATR-based stops.
- **Crucial**: the clock does not block a Grade A/B setup, but it informs the
  confidence of the expected move.

### Sizing as the safety valve

- Use position sizing (margin/leverage) to handle risk within Grade A/B.
- Max risk per trade: $3-$4. If sizing exceeds this, reduce margin.

### Hard rules (never violated)

- Stop-loss is always set before entry.
- Minimum risk:reward = 1:2. TP1 must be >= 2x SL distance from entry.
- Max risk per trade = $3-$4.
- The WAITING ROOM always fires when there is no valid trade.

### Four mandatory output sections

- Section 1: volatility context (current session + aggression level).
- Section 2: market structure summary.
- Section 3A: trade plan (when valid) or section 3B: WAITING ROOM (when not).
- Section 4: Telegram summary.

## See also

- [Trading math](docs/trading_math.md)
- [Trading rules](docs/trading_rules.md)
- [Trading routine](docs/trading_routine.md)
- [Trading indicators](docs/trading_indicators.md)
- [Project overview](docs/PROJECT.md)