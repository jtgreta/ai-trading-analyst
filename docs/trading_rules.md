# Trading Rules: Institutional Discipline Mode

These rules are non-negotiable. No exceptions. No "just this once."

[TOC]

## Capital and position sizing

**Total trading capital**: $100 (update when this changes)

**Max risk per trade**: $3.00 - $4.00 (3-4% of current capital)

### Sizing table (Binance Futures)

Position size must be calculated based on the stop-loss distance to ensure the
total risk never exceeds $4.

| Token type | Leverage | Margin | Max SL% | Risk cap |
| :--- | :--- | :--- | :--- | :--- |
| **Majors (BTC/ETH/BNB)** | 10x | $10 | 3% | <= $4 |
| **Mid-cap altcoins** | 5x | $7 | 8.5% | <= $4 |
| **Memes / New / AI** | 3x | $5 | 20% | <= $4 |

- **Formula**: `Position Size = (Capital x 0.03) / Stop-Loss Distance`
- **Rule**: `Margin x Leverage x SL%` must always be <= $4. See
  [trading_math.md](trading_math.md) for *why* this cap exists.

## Stop-loss and take-profit rules

### Stop-loss (SL)

- Set before entry: the SL must be entered into the system *before* the trade
  is opened.
- No moving backwards: the SL is never moved to increase the risk.
- Acceptance: if you feel the urge to move the SL, close the trade instead.

### Take-profit (TP)

- Minimum RR: 1:2 (TP1 must be >= 2x SL distance).
- Partial exits:
  - **Scalps**: TP1 (35%), TP2 (40%), TP3 (trail remainder).
  - **Swings**: TP1 (30%), TP2 (40%), TP3 (trail remainder).
- Risk management: after TP1 is hit, move SL to **breakeven**. After TP2,
  activate a trailing stop.

## Volatility context (PHT / UTC+8)

Trade 24/7 based on signal quality, but adjust aggression levels based on
institutional volume clusters.

| Session | PHT time | Volatility context | Rule |
| :--- | :--- | :--- | :--- |
| **Early Asian pulse** | 5:00 AM - 8:00 AM | Yellow/Green mod-high vol | Increased aggression. Early trend setters |
| **Asian session** | 8:00 AM - 12:00 PM | Yellow low vol | Conservative. Grade A favored. Higher risk of chop |
| **London open** | 3:00 PM - 5:00 PM | Green high vol | **Prime window.** Maximum aggression. Impulsive moves |
| **London-NY gap** | 5:00 PM - 9:00 PM | Yellow moderate | Moderate aggression. Favor clear structural alignment |
| **NY overlap** | 9:30 PM - 12:00 AM | Green high vol | **Prime window.** Maximum aggression. High liquidity |
| **Off-hours** | 12:00 AM+ | Yellow low vol | Conservative. Grade A favored. Watch for fakeouts |

### Daily routine (guideline, not hard block)

- **9:00 PM**: run Scanner -> get shortlist.
- **9:15 PM**: run Scalper/Hunter on top 1-2 coins.
- **9:30 PM**: enter if score >= 6 and all checklist items pass.

## AI signal and grading system

Do not override the AI signal based on gut feeling.

- **Grade A (score 8-10)**: full margin. High conviction.
- **Grade B (score 6-7)**: half margin. Moderate conviction.
- **Grade C (score <6)**: WAITING ROOM. Not a trade. Wait for conditions to
  improve.

**Rule**: if you disagree with the signal, skip the trade. Do not take the
opposite.

The mathematics of why 1:2 RR + grading works is in
[trading_math.md](trading_math.md).

## Entry principles (SMC framework)

Avoid retail traps. Use institutional markers.

1.  **Trend alignment**: check 1H and 4H direction. Only look for longs in a
    bullish HTF trend and shorts in a bearish HTF trend.
1.  **The retest rule**: never chase the first breakout candle. Wait for the
    price to return to:
    - A bullish/bearish Order Block (OB).
    - A Fair Value Gap (FVG) fill.
1.  **Volume validation**: ensure volume is rising on the reversal/continuation
    move. Fading volume = weak momentum.
1.  **Liquidity grab**: look for "stop hunts" (price dipping below a low then
    snapping back) before entering.

## Daily session limits

If these are hit, close the platform and walk away.

- **Max daily loss**: 3% of capital.
- **Max scalps per day**: 5 trades.
- **Max simultaneous trades**: 2-3 positions.
- **Max consecutive losses**: 3 (triggers immediate 24h cooldown).

## Entry checklist

All boxes must be checked before entry:

- [ ] Signal score >= 6 (Grade B or A).
- [ ] 1H + 4H trend aligns with direction.
- [ ] Entry is on a retest/FVG fill, not a chase.
- [ ] Volume supports the move.
- [ ] Stop-loss is identified and pre-set.
- [ ] Position size is calculated (risk <= $4).
- [ ] Risk-to-reward is >= 1:2.
- [ ] Daily loss limit NOT hit.
- [ ] Emotional state is neutral (not anxious or revenge-seeking).

## Forbidden behaviors

- Revenge trading or doubling down.
- Moving SL to "give the trade room".
- Trading without a stop-loss "temporarily".
- Chasing breakout candles.
- Ignoring the AI "Waiting Room" result.
- Overtrading in low-vol windows with Grade B setups.

## Weekly review

Every weekend, review the log:

- **Compliance rate**: did I follow the signals exactly?
- **Rule violations**: where did I deviate?
- **Performance**: actual win rate vs. average RR.
- **Psychology**: did I trade emotionally?

The journal computes expectancy and win rate for you
(`tools/journal.py review`). The statistical meaning of those numbers is in
[trading_math.md](trading_math.md).

## Why these rules exist (the mathematics)

Every rule above is the operational form of a formula. Full derivations and
worked numbers are in [trading_math.md](trading_math.md). This section is the
"so that's why" reference.

### Why min RR = 1:2

Breakeven win rate for reward `R` is `p* = 1/(1+R)`. At 1:1 you must win 50% -
a coin flip. At **1:2 you only need 33.3%**. The SMC entry filters (FVG/OB/
inducement + 4H BOS alignment) are the tool that pushes the true win rate from
that 33% floor toward 40-50%. The asymmetric payoff IS the edge; the signals
are how you keep `p` above it.

### Why max risk = $3-$4 on $100

Quarter-Kelly reasoning. Full Kelly for a 45%-win, 1:2 system is 17.5% per
trade - an 8-loss streak (a statistical certainty at some point) costs ~78% of
the account. At **3-4% risk**, a 50% drawdown becomes a ~0.1% event, not a ~20%
one. Rule of thumb: risk per trade ~ 3-4% of capital ~ 20-25% of full Kelly.

### Why stops are ATR x 1.5, never tighter

ATR approximates one bar's ~1 sigma noise. A stop tighter than ~1 sigma gets
hit by normal fluctuation every single time. 1.5 sigma keeps the stop outside
the noise band while still bounded by `MaxSL%`. This is a statistics decision,
not a style choice.

### Why losing streaks are expected, not a failure

At a 45% win rate, 3 losses in a row is a 16.6% event; over 100 trades the
expected longest streak is ~8 losses. Bad trades cluster in chop and correlated
sessions, so real streaks run even longer. The rules that follow:

- **Max loss 3%/day**: one bad day can't cascade.
- **3 losses -> 24h cooldown**: psychologically necessary because after 3
  losses traders stop executing the system and start revenge trading, which
  turns a 16% ordinary event into a margin call. The cooldown protects
  execution, not the P&L.
- **$3-$4 cap**: so an 8-loss streak is survivable.

### Why after TP1 the stop moves to breakeven

Breakeven on the remaining 65% turns the trade into a **free option**: worst
case 0R, best case +3.5R. The realized minimum is already +0.7R (35% x 2R).
Asymmetric payoff skew is purely mathematical profit.

### Why fewer trades beats more trades

Compound growth ~ mean - 1/2 x variance. Every correlated extra trade adds
variance drag and fees without adding independent samples. The journal's
100-trade milestone is also the statistical minimum to distinguish a real edge
from the 33.3% breakeven coin flip (~130 trades for 80% power). Discretionary
"just one more" trades corrupt the statistics AND the expectancy.

### Why we never curve-fit

Tweaking thresholds to fit recent data = selecting the max of N coin flips.
The SMC rules are fixed. Your job is compliance and logging, not "improving"
the formulas with vibes.

**Bottom line**: the account grows via *positive expectancy x survival x time*.
The rules exist to keep `p > 33.3%` (entry quality), `risk ~ 1/4 Kelly`
(survival), and streaks survivable (psychology). Everything else is decoration.

## See also

- [Trading math](trading_math.md)
- [Trading routine](trading_routine.md)
- [Trading indicators](trading_indicators.md)
- [Trader profile template](trading_profile.md)