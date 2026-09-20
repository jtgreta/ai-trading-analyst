# Trader Profile (Template)

Fill this out and keep it at `config/trading_profile.md` (gitignored - your
personal copy never gets committed). The AI agent references it when giving
advice, so it can coach you as an individual rather than generically.

> How to use this template: replace the `(...)` placeholders with your own
> `Option` choices from the values given, or write custom answers. Delete
> sections that don't apply. Then save it as `config/trading_profile.md`.

> Example filled profiles live in `config/trading_profile.md` (user-specific,
> not committed).

[TOC]

## Basic profile

- **Trading style**: (scalping | day trading | swing trading | investing |
  combination) - pick primary, list secondary.
- **Market**: (crypto - Binance Futures | crypto - spot | forex | stocks |
  futures).
- **Experience level**: (beginner | intermediate - not consistently
  profitable | intermediate - break-even | advanced - consistently
  profitable).
- **Trading platform**: (Binance | Bybit | BrokerX | ...).
- **Current capital**: ($ amount).

## AI signal system

Describe the stages and how the AI output feeds your decisions. For this
repo's default system:

- **Stage 1 - Scanner (momentum discovery)**: volume > $100M, 24H range
  > 10%, ranked by SMC priority (BOS, FVG, OB). Activation: `scan the
  market`, `what's moving`.
- **Stage 2 - Scalper (precision execution)**: 4H structure gate, entries at
  FVG/OB, score 0-10 -> Grade A (full margin) / B (half) / C (waiting room).
  Activation: `scalp [TICKER]`.
- **Stage 3 - Hunter (pre-breakout)**: 15M range contraction + 1H ChoCh
  inside an FVG. Activation: `hunt`.
- **Stage 4 - Swing (macro trend)**: 1W/1D/4H, 1D FVG entry, 2-14 day holds.
  Activation: `swing [TICKER]`.

**Core challenge**: (write the single biggest reason the system fails for you
- for example, "discipline; I override signals on FOMO").

## Known weaknesses

(pick from the common set below, add your own)

| Weakness | How it shows up |
| :--- | :--- |
| System disobedience | Taking trades the system didn't signal, ignoring a "Waiting Room" result |
| Revenge trading | Entering immediately after a loss to "recover" funds |
| Overconfidence | Increasing size/frequency after a winning streak |
| Emotional overrides | Letting "gut feeling" bypass the grading system (for example, taking a Grade C) |
| Stop-loss neglect | Moving stops to avoid a loss or not setting them before entry |
| Chasing candles | Entering on the first breakout candle instead of waiting for the retest/FVG fill |
| Overtrading | Too many low-quality setups during low-volume sessions |

## Goals

- **Short term (next 3 months)**: (for example, at least 80% compliance with
  the system, strict $3-$4 max risk, don't blow the account).
- **Medium term (3-12 months)**: (for example, positive expectancy over 100+
  trades, compound capital, refine SMC logic from logged data).
- **Long term**: (for example, reliable secondary income, master
  institutional discipline).

## What I need from the agent

(pick from:)

- **Be a discipline coach** - honest and firm, not encouraging, when I break
  rules.
- **Objective review** - "Which rule did you follow?" / "Why did you override
  the signal?"
- **SMC expertise** - help refine BOS / ChoCh / FVG logic.
- **Accountability** - remind me of this profile when I try to justify
  emotional trades.
- **No validation** - do not validate revenge trading or "gut feeling"
  reasoning.

## Rules I struggle with most

(list the 3-5 rules the agent should be extra firm about, for example:)

1.  Following the system signal (overriding the score/grade too often).
1.  The hard stop - walking away after the daily loss limit.
1.  The retest - waiting for the FVG/OB retest instead of chasing.
1.  Pre-set stops - setting the SL before clicking "Buy/Sell".

## See also

- [Trading rules](trading_rules.md)
- [Trading math](trading_math.md)

