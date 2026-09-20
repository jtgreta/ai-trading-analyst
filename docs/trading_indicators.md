# Trading Indicators: SMC and Technical Reference

Technical analysis relies on indicators to simplify price action, spot trends,
and identify potential reversal points. Understanding how these tools work
individually, and how they complement each other, is key to building a reliable
trading strategy.

[TOC]

## Smart Money Concepts (SMC): the core framework

Unlike traditional indicators, SMC focuses on identifying where institutional
"smart money" is entering the market, focusing on liquidity and market
structure rather than lagging averages.

### Market structure

- **BOS (Break of Structure)**: occurs when the price breaks a previous high
  (in an uptrend) or low (in a downtrend), confirming the continuation of the
  current trend.
- **ChoCh (Change of Character)**: the first sign of a potential trend
  reversal. It happens when the price breaks the last structural high/low that
  led to the most recent BOS.

### Supply and demand zones

- **Order Block (OB)**: the last opposite-colored candle before a strong
  impulsive move that breaks structure. These act as high-probability
  support/resistance zones where institutions have "left" orders.
- **FVG (Fair Value Gap) / Imbalance**: a three-candle sequence where there is
  a gap between the first candle's wick and the third candle's wick. Price acts
  like a magnet to these gaps, often returning to "fill" them before
  continuing.

### Liquidity

- **Liquidity pools**: areas where many retail stop-losses are clustered (for
  example, equal highs/lows, previous day's high/low). Smart Money often
  drives price into these pools to "grab liquidity" before reversing direction.

## Core technical indicators

### Moving average (MA)

A moving average smooths out price data to create a single flowing line,
making it easier to identify the overall trend direction.

- **Simple Moving Average (SMA)**: calculates the average price over a
  specific number of periods.
- **Exponential Moving Average (EMA)**: gives more weight to recent prices,
  reacting faster to sudden market changes.
- **How to use it**: when price is above the MA, the trend is generally
  upward; when below, downward. A crossover of a short-term MA (like the
  50-period) over a long-term MA (like the 200-period) signifies a trend shift.

### MACD (Moving Average Convergence Divergence)

MACD is a trend-following momentum indicator that shows the relationship
between two moving averages of a security price.

- **Components**: the MACD line (difference between two EMAs), the Signal line
  (EMA of the MACD line), and the Histogram (the visual difference between the
  two lines).
- **How to use it**: a bullish signal occurs when the MACD line crosses above
  the signal line. A bearish signal occurs when it crosses below. Centerline
  crossovers (moving above or below zero) also indicate changing momentum.

### RSI (Relative Strength Index)

RSI is a momentum oscillator that measures the speed and change of price
movements on a scale from 0 to 100.

- **Thresholds**: traditionally, an RSI above 70 indicates overbought
  (potentially primed for a pullback); below 30 indicates oversold (potentially
  primed for a bounce).
- **How to use it**: look for extreme readings to anticipate reversals, or
  watch for divergences where the price makes a new high but the RSI fails to
  do so, signaling weakening momentum.

### Bollinger bands

Bollinger bands measure market volatility using a three-line structure
overlaid directly on the price chart.

- **Components**: a middle band (usually a 20-period SMA) and two outer bands
  calculated using standard deviations from the middle line.
- **How to use it**: the bands expand when volatility is high and contract
  when volatility is low. Price tends to bounce off the outer bands (the
  Bollinger bounce). A breakout outside the bands can signal a strong
  continuation of the trend.

## The most critical metric: volume and VWAP

The most critical missing piece from basic indicators is **volume**, or
specifically **VWAP (Volume-Weighted Average Price)**. While other indicators
are derived from price, volume is the "fuel".

### Why volume/VWAP is essential

- **Validates trends**: a price breakout accompanied by high volume indicates
  strong institutional conviction. A breakout on low volume is highly likely
  to fail.
- **Institutional benchmark**: large institutions use VWAP as a target
  execution guide. If the price is below VWAP, it is considered a good value
  for buyers; if above, it favors sellers.

## The mathematics behind the indicators

What each indicator actually computes, why the numbers are those numbers, and
how it links to the quantitative framework in
[trading_math.md](trading_math.md).

### SMA and EMA

```text
SMA(n)  = (P1 + P2 + ... + Pn) / n             every bar weighted equally
EMA(n)  = a x P + (1 - a) x EMA(previous), a = 2 / (n + 1)
```

The EMA smoothing constant `a = 2/(14+1) = 0.133` (for the 14-period) means the
most recent bar carries 13.3% of the weight and the "memory" halves roughly
every 5 bars. This matters: too short an EMA is noise, too long is lag. The
repo's 5/10/20 MA stack is a *regime* filter (is price above or below the
stack - a consensus of momentum), not a timing signal. A bull stack
(`price > 5 > 10 > 20`) is the momentum equivalent of RSI being in the >50
zone.

### RSI: a mean-reversion oscillator with a hard limit

```text
RS  = avg(gains) / avg(losses)   over the window (Wilder smoothing)
RSI = 100 - 100 / (1 + RS)       range [0, 100]
```

RSI is a nonlinear map of the up/down momentum ratio onto a fixed 0-100 scale.
The thresholds are not magic:

- RSI = **50** means avg gains = avg losses - momentum-neutral.
- RSI = **76** (this repo's hard block) means avg gains are ~3.17x avg losses,
  a roughly 3-sigma-class overbought state on the bar-to-bar distribution.
  Entering a long there means buying when the short-term statistic has already
  swung ~3:1. The RSI >76 / <24 hard blocks (`HF-3`) are where the `p` in the
  expectancy equation drops below breakeven.

### ATR: the volatility proxy (and how the stop is derived)

```text
TR   = max(high - low, |high - prevClose|, |low - prevClose|)
ATR  = SMA(TR, 14)    ~ one bar's typical move ~ ~1 sigma of bar-to-bar noise
```

ATR estimates the noise band you must stay outside of. The system's
`SL = min(ATR x 1.5, MaxSL%)` is a **1.5 sigma structural stop**: tight enough
to be risk-controlled, wide enough that ordinary noise cannot hunt it. A stop
narrower than ~1x ATR is statistically guaranteed to be hit by noise, not
structure. Trailing callbacks are ATR-derived too
(`calc_trail_callback_pct`) - the trail hugs volatility, never a fixed %,
so it adapts to each token's noise profile.

### VWAP: the volume-weighted consensus price

```text
VWAP = sum(P x Vol) / sum(Vol)    cumulative, resets each session
```

Every trade is a volume-weighted average; VWAP is the weighted center of the
day's realized trades. Above VWAP: the average real dollar is held by buyers.
Below: sellers. The repo treats it as a context layer - price far above VWAP
after a vertical move is the same "extended from value" read as RSI near 76,
from two independent angles.

### Bollinger bands: volatility drawn on price

```text
Middle = SMA(20);   bands = SMA(20) +/- 2 x std(20)
```

A "band squeeze" is a volatility (sigma) collapse - the raw input to the
hunter's coiling logic: range-shortening + volume-building means sigma is
compressed, so the next move is disproportionately large when it breaks
(energy conserved). Breakouts out of a compressed band are the distribution
you want to trade in the Prime windows.

## When to trade: the power of confluence

Trading based on a single indicator often leads to false signals. The best
times to trade occur during **confluence**, where SMC and traditional
indicators align.

**High-probability bullish setup:**

1.  **Structure**: higher timeframe (4H/1D) is bullish.
1.  **SMC**: price pulls back into a bullish Order Block or fills a bullish
    FVG.
1.  **Confirmation**: a ChoCh occurs on a lower timeframe (15M/5M).
1.  **Indicators**: RSI is oversold or MACD shows a bullish crossover.
1.  **Volume**: volume spikes on the reversal move.

## See also

- [Trading math](trading_math.md)
- [Trading rules](trading_rules.md)
- [Project overview](PROJECT.md)