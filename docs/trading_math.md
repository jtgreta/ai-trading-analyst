# Trading Math: Probability, Risk and Long-Run Growth

This document is the mathematical foundation under everything else in this
repo. Every rule in [trading_rules.md](trading_rules.md) exists because of a
formula in here. If you only read one section, read Expectancy and Kelly
sizing.

[TOC]

## The honest truth (read first)

**There is no strategy that wins continuously.** Not the trend followers with
million-dollar research budgets, not the market makers, not this system.
Anyone who tells you a strategy "wins continuously" is describing a backtest,
a scam, or a lucky stretch.

What a good strategy does:

1.  **Have positive expectancy** - the average trade nets more than it costs,
    across hundreds of trades, not every trade.
1.  **Size positions so ruin is essentially impossible** - so you live long
    enough for the positive expectancy to compound.
1.  **Take fewer, higher-quality bets** - because every trade pays transaction
    costs, spread, and adds variance drag. Less is literally more.

That is the entire secret. This document gives you the maths for all three.

The two must-master equations that govern everything:

| What stays the same over time | Fundamental law |
| :--- | :--- |
| Arithmetic average trade result | Drives the *mean* of your equity: (T1 + T2) / 2 |
| Geometric average per-trade growth | Drives your *compound* growth (most important) |

Per period, realized compound growth is approximately:

```text
compound growth ~ arithmetic mean - (1/2) x variance
```

This gap is called **volatility drag**. Every extra, correlated, sloppy trade
adds variance and *shrinks* your compound growth even when it doesn't lose
money. This is the mathematical reason the system grades setups and sits in
the WAITING ROOM 90% of the time.

## Expectancy: measuring profitability

### The R-multiple framework

Measure every trade in units of **risk (R)** = 1x the stop-loss distance.

- A loss at the stop = **-1R**.
- TP1 at 2x the SL distance = **+2R**.
- TP2 at 3.5x = **+3.5R**.
- Breakeven exit = **0R**.

```text
Expectancy = WinRate x AvgWin(R) - LossRate x AvgLoss(R)
```

The journal (`tools/journal.py`) already computes this every week.
Example: 45% win rate, average win 2.2R, average loss 1.0R:

```text
E = 0.45 x 2.2 - 0.55 x 1.0 = 0.99 - 0.55 = +0.44R per trade
```

Positive expectancy. Over 100 trades that is roughly +44R of total profit
before variance.

### The breakeven win rate: the single most important number

For a fixed risk/reward, the breakeven win rate (where expectancy = 0) is:

```text
p* = 1 / (1 + RR)       where RR = average reward in R
```

| Win rate (p) | Breakeven RR | Meaning |
| :--- | :--- | :--- |
| 50% | 1.00 | A coin flip. Must get 1:1 |
| 45% | 1.22 | Still a losing game unless RR > 1.22 |
| 33.3% | 2.00 | This system's floor. With a 1:2 minimum, you only need to win 1 in 3 |
| 30% | 2.33 | Wins under a third of the time and still profits |

The system enforces "minimum RR = 1:2". That means its breakeven is **33.3%**.
Every trading day, before the first candle, you already have a massive
structural edge by picking asymmetric odds instead of trying to be right 60%
of the time.

> **Key insight - why this beats "high win rate" systems:** a 70%-win-rate
> system with 1:1 RR has expectancy 0.7 - 0.3 = +0.4R. A 40%-win-rate system
> with 1:3 RR has 1.2 - 0.6 = +0.6R - *better* with a third more losses.
> Win rate alone is meaningless; **expectancy in R is the only truth.**

### Partial exits change the math (and protect it)

The system closes in stages: TP1 (35% of position at 2R), TP2 (40% at 3.5R),
TP3 (25% by trailing stop). Two mathematical effects:

1.  **Variance reduction**: realizing part of the profit early flattens the
    per-trade equity swing. Compound growth roughly equals mean minus half
    variance, so lower variance directly increases long-run growth for the
    same expectancy.
1.  **Breakeven is a free option**: after TP1, the stop moves to entry. Worst
    case on the remaining 65% is 0R, best case is +3.5R+. You now own a trade
    that cannot lose below +0.7R (35% x 2R realized) - with positive payoff
    skew.

A single-target system bets the whole position on the route to one number.
The staged exit bets 35% short-term and 65% long-term - the professional
consensus of how to convert expectancy into consistent compound growth.

### Profit factor (the trader's Sharpe)

```text
Profit factor = gross wins / gross losses
Profit factor > 1.0   <=>   expectancy > 0
```

It is expectancy's friction-free twin: same information, different unit. Log
it weekly in the journal.

## Losing streaks: the truth behind the 3-loss rule

If each trade wins with probability `p` independently, the chance of `k`
losses in a row is `q^k` where `q = 1 - p`.

| Win rate | 3 losses in a row | 5 losses in a row |
| :--- | :--- | :--- |
| 40% | 21.6% | 7.8% |
| 45% | 16.6% | 5.0% |
| 50% | 12.5% | 3.1% |

The longest expected losing streak in `n` trades is approximately:

```text
L_streak ~ ln(n) / ln(1/q)
```

At a 45% win rate over 100 trades: `ln(100) / ln(1.818) ~ 7.7` - you WILL see
an about-8-loss streak roughly once per 100 trades, no matter how good the
system is.

This is not failure. Losses are guaranteed to cluster - market regimes are
correlated, so streaks are even longer than the independence formula suggests
(bad trades cluster in chop, in a rotation, in one over-extended week).

**This is why the rules exist:**

- Max risk $3-$4: an 8-loss streak costs at most $32, not your account.
- 3 consecutive losses -> 24h cooldown: breaks the *emotional* chain, not
  because 3 losses are dangerous mathematically, but because after 3 losses
  traders stop executing the system (revenge trading follows).
- The WAITING ROOM exists to stop you *adding* discretionary trades on top of
  a statistical certainty you don't control.

Never, ever tell yourself that a 16.6% (3-loss) or 5% (5-loss) streak is
"rare" and therefore yours to override. At your trade frequency those streaks
are ordinary events. The system is built to survive them, not to avoid them -
avoiding them is impossible.

## Kelly sizing: how much to risk

### Full Kelly

Kelly's criterion maximizes the **long-run geometric growth rate**. For a
trade with win prob `p`, loss prob `q = 1 - p`, reward `R` (in units of risk):

```text
f* = p - q / R       (fraction of capital to risk per trade)
```

| Win rate | R:R = 1:2 | Full Kelly f* |
| :--- | :--- | :--- |
| 35% | 1:2 | 0.35 - 0.65/2 = 0.025 -> risk 2.5% |
| 40% | 1:2 | 0.40 - 0.60/2 = 0.10 -> risk 10% |
| 45% | 1:2 | 0.45 - 0.55/2 = 0.175 -> risk 17.5% |
| 50% | 1:2 | 0.50 - 0.50/2 = 0.25 -> risk 25% |

### Why the system uses 3-4% instead of Kelly

Full Kelly means **10-25% of your account on a single trade**. The maths:

- Kelly maximizes *geometric* growth only if you know `p` exactly, which you
  never do.
- Estimating `p` too high by a few points makes Kelly **lose money** faster
  than someone betting a tiny fraction (Kelly is famously over-optimistic:
  betting 1.5x Kelly halves growth AND roughly doubles risk of ruin).
- The drop from full Kelly is a mathematical consequence of **estimation
  error** plus **drawdown size**: at full Kelly, an 8-loss streak (guaranteed
  above) costs 1 - (1 - 0.175)^8 ~ 78% of the account.

So the system's $3-$4 on $100 = **3-4% risk = roughly one-fifth to one-quarter
Kelly**. That is the professional range: *fractional Kelly* (1/5 to 1/3 Kelly)
trades a little growth for a dramatic reduction in drawdown and estimation
risk.

> Rule of thumb: if a trade is sized so full Kelly would tell you 10%+ and the
> system caps you at 3-4%, the system is deliberately (and correctly) choosing
> survival-first growth.

### Risk is a function of stop distance, not margin

```text
Dollar risk = position notional x stop% = margin x leverage x stop%
```

The sizing engine (`tools/trading/sizing.py`) enforces
`margin x leverage x SL% <= $4`. That is the cap from this section - the whole
position-sizing architecture is the Kelly cap made operational.

## Risk of ruin

For fixed-fractional staking with per-trade log-drift `mu` and variance
`sigma^2`, the (approximate, Brownian) probability of ever drawing down to a
fraction `x` of equity remaining is:

```text
RoR(x) ~ exp( -2 x mu x (-ln x) / sigma^2 )

where:
  mu     = p x ln(1 + f x R) + q x ln(1 - f)     per-trade log growth
  sigma^2 = p x [ln(1 + f x R)]^2 + q x [ln(1 - f)]^2 - mu^2
  f      = fraction risked per trade
  x      = survival fraction (for example, 0.5 = 50% drawdown)
```

**Worked example** - the system's regime: p = 45%, R = 2, f = 0.03 (3% risk
per trade):

```text
mu     = 0.45 x ln(1.06) + 0.55 x ln(0.97)
       = 0.45 x 0.0583 + 0.55 x (-0.0305) = +0.0095

sigma^2 = 0.45 x (0.0583)^2 + 0.55 x (0.0305)^2 - (0.0095)^2
       = 0.00153 + 0.00051 - 0.00009 = 0.00195

RoR(50% drawdown) ~ exp(-2 x 0.0095 x 0.693 / 0.00195) ~ exp(-6.75) ~ 0.12%
```

Risking **3%** gives about a 0.12% chance of ever hitting a 50% drawdown.
Risking **10%** (full Kelly, correct edge) on the same game:

```text
mu     = 0.45 x ln(1.20) + 0.55 x ln(0.90)
       = 0.45 x 0.1823 + 0.55 x (-0.1054) = +0.0241

sigma^2 = 0.45 x (0.1823)^2 + 0.55 x (0.1054)^2 - (0.0241)^2
       = 0.01496 + 0.00611 - 0.00058 = 0.02049

RoR(50% drawdown) ~ exp(-2 x 0.0241 x 0.693 / 0.02049) ~ exp(-1.63) ~ 19.6%
```

**Risking 10% makes a 50% wipeout about 160x more likely than risking 3%
(19.6% vs 0.12%).** That is the entire argument for fractional Kelly and the
$3-$4 cap, in one number.

### What the daily limits mean in probability space

| Daily limit | Probability consequence |
| :--- | :--- |
| Stop at 3% daily loss | Caps single-day variance so one bad day can't start a cascade |
| Max 2-3 simultaneous positions | Caps correlation: N correlated positions ~ Nx risk, not N positions of risk |
| Max 5 scalps/day | Caps fee + variance bleed; quality gating by session windows |

## The statistics of knowing your edge

### How many trades until you know the system works

Win-rate estimation standard error:

```text
SE(p) = sqrt( p(1-p) / n )
```

Two useful sample sizes (alpha = 0.05, power = 80%):

1.  **To prove win rate > 33.3% breakeven** (is the 1:2 RR game actually
    +EV?): about **130 trades** at a true 45% win rate.
1.  **To estimate win rate within +-5pp** with 95% confidence: about
    **384 trades**.

**This is why the journal's milestone is 100+ trades.** Fewer than ~100
trades, a profitable record is statistically indistinguishable from luck. The
research finding: most retail "consistent winners" over fewer than 50 trades
have recorded nothing meaningful - their profit/loss distribution is within
noise.

### The danger of curve-fitting (multiple testing)

If you tweak parameters and keep the best backtest result, you are selecting
the **maximum of N random results** - and the maximum of many coin flips looks
like an edge.

- Test 20 indicator variants -> the best one looks profitable even when ALL
  are noise.
- The correction (Bonferroni / nominal p): with N tests, a result must beat
  `p < 0.05/N` to count. With N = 20, you need `p < 0.0025`.
- **Walk-forward / out-of-sample**: the only honest validation is results on
  data never used to build the system. This repo's SMC rules are *fixed* by
  design - do not "tweak" FVG thresholds to fit last week.

Rule: **he who optimizes the noise owns the noise.** Fixed rules + patience
beat thousands of parameter versions.

### Correlation between trades destroys sample size

If you take 3 overlapping trades in the same market in the same hour, you have
roughly 1 independent observation, not 3. Effective sample size
(approximation):

```text
n_eff ~ n / (1 + 2 x sum of trade correlations)
```

With mean pairwise correlation 0.25 and 10 trades: `n_eff ~ 6.7`. So fewer,
more diversified positions compound faster AND are statistically cleaner. The
"1-2 coins per session" rule is a statistics decision, not a vibe.

## Volatility math: why stops, zones and sessions work

### ATR as a volatility estimator

```text
True range = max(high - low, |high - prevClose|, |low - prevClose|)
ATR = SMA of true range over 14 bars    ~ one bar's typical range ~ ~1 sigma
```

The system's stop = ATR x 1.5, capped by token type:

```text
SL distance = min(ATR_1H x 1.5, entry x maxSL%)
```

Why 1.5 ATR: a ~1 sigma move is ordinary noise and will *always* happen - a
stop tighter than ~1 sigma gets hunted by every normal fluctuation. At 1.5x
ATR you are ~1.5 sigma from entry, outside the noise band wide enough to be
structural. This is the same reason RSI(1H) > 76 and < 24 hard-block entries -
those are > 1.5 sigma momentum states where the odds of a retrace are
statistically loaded.

### The random-walk baseline: your edge has to beat this

For an **unbiased** random walk with stop distance S and target distance T:

```text
P(reach target before stop) = S / (S + T)
```

At the system's 1:2 (S = 1, T = 2): P = 1 / (1 + 2) = **33.3%**. That is
exactly the breakeven. In other words: with no edge, you expect to fail 2 out
of 3 times, and that is a break-even number anyway.

**Implication:** every point of the scoring system (FVG proximity, OB,
inducement, 4H BOS alignment, session window) exists to move `p` from 33% to
40-50%. The structure detection is not decoration - it is the part of the
equation that turns a fair coin into positive expectancy. This is also why
chasing (entering far from the FVG) is mathematically fatal: you preserve the
1:2 payoff but destroy the `p` without which the payoff is worthless.

### Session windows: stitching volatility filters onto the edge

Volatility is not stationary. London/NY overlap have 2-3x the intraday range
of the Asian session. Working in per-trade R terms, the same 1:2 slot has:

- Prime window: real move arrives -> stops placed outside real noise -> `p`
  stays high.
- Chop window: repeated about-1.2-sigma fakeouts -> `p` collapses toward the
  33% coin flip.

The session table in [trading_routine.md](trading_routine.md) is a volatility
filter expressed as a schedule. It is not culture - it is the difference
between trading in the distribution you were validated on and trading in a
different, worse one.

## The complete long-run playbook (synthesis)

Decades of quantitative literature, compressed into the rules this repo
already enforces:

1.  **Build only +EV slots** - 1:2 minimum, SMC-filtered entries.
1.  **Risk about 1/4 Kelly** - $3-$4 on $100.
1.  **Accept clustered losses as a mathematical fact** - cooldowns exist for
    psychology.
1.  **Measure in R and expectancy, never in "wins"**.
1.  **Never curve-fit** - fixed rules, out-of-sample journal.
1.  **Let the compounding do the work** - the single most profitable strategy
    ever documented is not a signal; it is *survival + positive expectancy +
    log-normal compounding time*. At +0.4R per trade, risking 3%, you grow
    about 0.1-0.3% expected per trade. It is slow, boring, and it beats every
    "100% win rate" strategy that ends in a margin call.

## See also

- [Trading rules](trading_rules.md)
- [Trading indicators](trading_indicators.md)
- [Trading routine](trading_routine.md)