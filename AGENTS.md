# Trading Mandate: Institutional Adaptive Mode

## Repo Layout (THIS REPO)
- **Skills live in** `.agents/skills/<skill-name>/SKILL.md` inside this repository — the cross-tool standard location, auto-discovered by opencode, Claude, Codex, Cursor, Gemini CLI, Copilot, goose, and others.
- **Python helpers live in** `scripts/` (`scripts/<script>.py`). They import `scripts/trading_utils.py` directly from the same folder (no sys.path bootstrap needed).
- **Docs live in** `docs/` (`docs/PROJECT.md`, `docs/trading_rules.md`, `docs/trading_routine.md`, `docs/trading_indicators.md`, `docs/trading_profile.md`).
- **User config lives in** `config/trading.json` (capital, max risk, sizing-rule overlay; loaded by `scripts/trading_utils.py` at runtime). Start from `config/trading.json.example`.
- Before running a script, check it exists with `Test-Path "scripts\<script>.py"`; if found, run it directly — do not rewrite.
- Scripts available: `funding.py`, `hunter_coil.py`, `hunter_filter.py`, `hunter_scan.py`, `journal.py`, `manage.py`, `market_bias.py`, `scalper_analyze.py`, `scanner_filter.py`, `scanner_run.py`, `swing_analyze.py`.
- Skills available: `funding`, `hunter`, `journal`, `manage`, `market-bias`, `scalper`, `scanner`, `swing` (trading suite) + `binance`, `crypto-market-rank`, `find-skills`, `meme-rush`, `query-token-audit`, `query-token-info`, `trading-signal` (market tools).

## Core Philosophy
**The edge is not having more signals. It is having the right signals at the right time.**
Consistent compounding comes from trading high-conviction setups. While crypto is 24/7, institutional volume clusters in specific windows; we use these windows to modulate aggressiveness, not to block opportunity.

## Execution Rules

1. **WAITING ROOM replaces dead-end blocks**:
   - When no valid trade exists, every analysis outputs a full WAITING ROOM section.
   - The WAITING ROOM tells the trader: why not now, what would unlock a trade, key levels to watch, patterns to look for, pre-conditions checklist, and when to check back.
   - There is no output that ends without actionable information.

2. **Grade System (Score-Based)**:
   - **Grade A (score 8–10)**: Full margin. High conviction. Execute 24/7.
   - **Grade B (score 6–7)**: Half margin. Good setup, moderate conviction. Execute 24/7, but with increased awareness of session volatility.
   - **Grade C (score <6)**: WAITING ROOM. Not a trade — wait for conditions to improve.

3. **Volatility Context (PHT / UTC+8)**:
   - **Prime Windows (London Open 3-5 PM & NY Overlap 9:30 PM-12 AM)**: Maximum aggression. High probability of impulsive, trending moves.
   - **Early Asian Pulse (5-8 AM)**: Moderate to High aggression. High opportunity for early trend setters and volatility breakouts.
   - **Secondary Windows (London-NY Gap 5-9 PM)**: Moderate aggression. Favor setups with clear structural alignment.
   - **Low-Vol Windows (Asian Session 8 AM-12 PM & Off-hours 12 AM-3 PM)**: Conservative aggression. Higher risk of "choppy" price action. Favor Grade A setups and strictly adhere to ATR-based stops.
   - **Crucial**: The clock does not block a Grade A/B setup, but it informs the "confidence" of the expected move.

4. **Sizing as the Safety Valve**:
   - Use position sizing (Margin/Leverage) to handle risk within Grade A/B.
   - Max risk per trade: $3–$4. If sizing exceeds this, reduce margin.

5. **Hard Rules (Never Violated)**:
   - Stop-loss is always set before entry.
   - Minimum risk:reward = 1:2. TP1 must be ≥ 2× SL distance from entry.
   - Max risk per trade = $3–$4.
   - The WAITING ROOM always fires when there is no valid trade.

6. **Every Output Has 4 Mandatory Sections**:
   - Section 1: Volatility Context (Current Session + Aggression Level)
   - Section 2: Market Structure Summary
   - Section 3A: Trade Plan (when valid) OR Section 3B: WAITING ROOM (when not)
   - Section 4: Telegram Summary
