---
name: scanner
description: >
  Institutional Binance Futures scanner. Fetches all tickers in one call, filters
  by volume >$100M and range >10%, then runs SMC analysis per coin: BOS/ChoCh
  market structure on 4H and 1H, Fair Value Gap proximity, Order Block detection,
  Inducement/Liquidity Grab detection, OTE zone check, ATR volatility filter,
  RSI extreme filter, and liquidity pool proximity.
  Scores and ranks by SMC-weighted priority. Outputs shortlist with full SMC
  context per coin and priority picks. Use before Scalper or Hunter.
version: institutional
---

# Scanner Ã¢â‚¬â€ Institutional Market Discovery

## What Changed from Retail (and Why)
The retail scanner used MA stacks + coiling + relative volume to rank coins.
This produced directional signals for coins where the direction was actually
ambiguous Ã¢â‚¬â€ any coin with a bullish 1H/4H MA stack got labeled "SCALP LONG"
even if it was in the middle of a 4H range with no structural edge.

Institutional Edition changes the ranking engine to SMC-first:
- Direction is assigned from 4H market structure (BOS/ChoCh), not MA stacks
- 4H "ranging" structure = Ã¢ÂÂ³ SKIP (no fake direction labels), with MA fallback
- FVG proximity is the highest-weight signal (3 pts) Ã¢â‚¬â€ price in a gap = institutional magnet
- Inducement (liquidity grab + reversal) scores 3 pts = equal to FVG
- ATR filter eliminates coins that are too volatile to time entry on
- RSI extremes are a hard deduction (Ã¢Ë†â€™2 pts), not ignored

---

## Runtime Notes
- PowerShell runs internally Ã¢â‚¬â€ use `python` or `curl.exe`
- Do NOT loop API calls per symbol in Step 1 Ã¢â‚¬â€ batch process only
- trading_utils.py lives in scripts/trading_utils.py (no repo-root dependency) - scripts import it directly from the same folder
- Ensure VPN is active on hotspot

---

## Ã¢Å¡Â Ã¯Â¸Â PYTHON FILE NAMING CONVENTION Ã¢â‚¬â€ MANDATORY

When creating any Python helper file for this skill, put it in the `scripts/` folder of this repo:
`scripts/scanner_<purpose>.py`

Examples:
- `scripts/scanner_run.py`     Ã¢â‚¬â€ full SMC pipeline (preferred)
- `scripts/scanner_filter.py`  Ã¢â‚¬â€ ticker fetch + filter only (standalone utility)

**Before creating, ALWAYS check if it already exists:**
```powershell
Test-Path "scripts\scanner_run.py"
Test-Path "scripts\scanner_filter.py"
```
If found, run it directly. Do not rewrite.

All Python scripts live in:
`scripts\`

---

## Activation Triggers
- "scan the market"
- "find something to scalp"
- "what's moving"
- "show me movers"
- "what to trade"
- "market scan"
- "scan binance futures"
- "find me a trade"

---

## Session Timing (PHT / UTC+8)
- Scanner automatically fetches and evaluates the current session quality.
- Warns against entries during Asian Session (8 AM Ã¢â‚¬â€œ 12 PM).
- Highlights PRIME windows (London-NY overlap).

---

## Preferred Execution

If `scripts/scanner_run.py` exists:
```powershell
python "scripts\scanner_run.py"
```

---

## Step 1: Fetch All Futures Tickers

```
curl.exe "https://fapi.binance.com/fapi/v1/ticker/24hr"
```

Key fields: symbol, priceChangePercent, highPrice, lowPrice, lastPrice, quoteVolume
Do NOT loop per symbol Ã¢â‚¬â€ process full response at once.

---

## Step 2: Cast All Numeric Fields Ã¢â‚¬â€ MANDATORY

Cast to float before any filter or sort:
```
quoteVolume        = float(ticker.quoteVolume)
priceChangePercent = float(ticker.priceChangePercent)
highPrice          = float(ticker.highPrice)
lowPrice           = float(ticker.lowPrice)
lastPrice          = float(ticker.lastPrice)
absChange          = abs(priceChangePercent)
rangePercent       = (highPrice - lowPrice) / lowPrice * 100
```

---

## Step 3: Filter

Keep symbols matching ALL (using float values):
- quoteVolume > 100,000,000
- rangePercent > 10
- absChange > 3

Exclude substrings: USDC, BUSD, TUSD, DAI, FDUSD
Exclude exact: BTCDOMUSDT, DEFIUSDT, ALTUSDT

If fewer than 5 pass Ã¢â€ â€™ lower rangePercent threshold to 7.

---

## Step 4: Rank by Absolute Move Ã¢â‚¬â€ All Matched (no top-10 cap in filter)

Sort by absChange DESC. Analyze all matched coins Ã¢â‚¬â€ priority scoring will
determine which are actually worth trading.

---

## Step 5: Fetch Klines

For each coin (fetch ALL before computing Ã¢â‚¬â€ do not compute mid-fetch):
```
1H: limit=100  (needed for SMC swing high/low detection)
4H: limit=100
15M: limit=50
```

Kline index: [0]=openTime [1]=open [2]=high [3]=low [4]=close [5]=baseVol [7]=quoteVol

---

## Step 6: SMC Analysis Per Coin

### A. Market Structure (4H + 1H)
```
ms_4h = detect_market_structure(k4h, lookback=30)
ms_1h = detect_market_structure(k1h, lookback=30)
```

Direction assignment (SMC-first):
- ms_4h.trend == "bullish" OR last_event in (BOS_up, ChoCh_up) Ã¢â€ â€™ Ã°Å¸Å¡â‚¬ SCALP LONG
- ms_4h.trend == "bearish" OR last_event in (BOS_down, ChoCh_down) Ã¢â€ â€™ Ã°Å¸ÂÂ» SCALP SHORT
- ms_4h.trend == "ranging" Ã¢â€ â€™ fallback to MA stack (weaker signal, labeled accordingly)
- MA stack fallback still conflicting Ã¢â€ â€™ Ã¢ÂÂ³ SKIP

### B. ATR Volatility Filter
```
atr_1h = ATR(k1h, 14)
atr_pct = atr_1h / price * 100
```
- If atr_pct > 4.0% Ã¢â€ â€™ coin is too volatile to time entry reliably
  Still show the coin but deduct 2 pts and flag it
- atr_pct is displayed in the output for manual judgment

### C. RSI Filter
```
rsi_1h = RSI(closes_1h, 14)
```
- rsi_1h > 78 Ã¢â€ â€™ flag "OVERBOUGHT" Ã¢â€ â€™ deduct 2 pts (late long = bad entry)
- rsi_1h < 22 Ã¢â€ â€™ flag "OVERSOLD" Ã¢â€ â€™ deduct 2 pts (late short = bad entry)
- Show RSI value in output for all coins

### D. Fair Value Gap Proximity (1H)
```
fvgs = detect_fvg(k1h, lookback=20)
```
- If price is within 2% of an unfilled FVG midpoint Ã¢â€ â€™ flag "Ã°Å¸Å½Â¯ IN FVG (BULL/BEAR)"
  This is a top-priority signal Ã¢â‚¬â€ price inside a gap = institutional magnet

### E. Order Block Proximity (1H)
```
obs = detect_order_blocks(k1h, lookback=30)
```
- If price is within 1.5% of an unmitigated OB midpoint Ã¢â€ â€™ flag "Ã°Å¸â€œÂ¦ AT OB"

### F. Inducement / Liquidity Grab (1H)
```
idms = identify_inducement(k1h, swing_highs, swing_lows, trend, lookback=30)
```
- Confirmed inducement (swept minor swing + reversed within 5 candles) Ã¢â€ â€™
  flag "Ã°Å¸ÂªÂ¤ INDUCEMENT (BULL/BEAR)"
- Highest-confidence signal: smart money has already shown its hand

### G. OTE Zone Check (1H)
```
ote = calculate_ote_zone(swing_low, swing_high, direction)
if ote_bottom <= price <= ote_top: flag "Ã°Å¸Å½Â¯ IN OTE ZONE"
```
- Price in the Fibonacci 61.8Ã¢â‚¬â€œ78.6% retracement zone = institutional pullback entry

### H. Liquidity Pools (1H)
```
liq = detect_liquidity(k1h, lookback=30)
```
- If price within 2% of EQH Ã¢â€ â€™ flag "Ã¢Å¡Â Ã¯Â¸Â NEAR EQH LIQ" (buy-side stop cluster)
- If price within 2% of EQL Ã¢â€ â€™ flag "Ã¢Å¡Â Ã¯Â¸Â NEAR EQL LIQ" (sell-side stop cluster)

### I. Coiling (15M Ã¢â‚¬â€ retained)
```
last3_ranges avg vs prev3_ranges avg  (< 0.75x = shrinking)
last3_vol avg vs prev3_vol avg        (> 1.2x = building)
```
- Both conditions met Ã¢â€ â€™ Ã¢Å¡Â¡ COILING (breakout imminent)

### J. Volume Signal (1H)
```
vol_signal: Spike (> 1.5x avg5), Fading (< 0.7x), Normal
relVol: last 1H quote volume / (24H quote volume / 24)
```

---

## Step 7: SMC-Weighted Priority Scoring

| Signal | Condition | Points |
|---|---|---|
| Direction assigned | "Ã¢ÂÂ³ SKIP" not in direction | +1 |
| 4H BOS | ms_4h last_event contains "BOS" | +4 |
| FVG | Price within 2% of unfilled FVG midpoint | +3 |
| Inducement confirmed | Liquidity grab + reversal (idms not empty) | +3 |
| OTE zone | Price in 61.8Ã¢â‚¬â€œ78.6% Fibonacci retracement | +2 |
| BOS on 1H | ms_1h last_event contains "BOS" | +1 |
| Order Block | Price within 1.5% of unmitigated OB | +1 |
| ChoCh on 1H | ms_1h.mss = True | +1 |
| Coiling 15M | range shrinking + volume building | +1 |
| RelVol HEAVY | relVol > 2.0x avg | +1 |
| Risk LOW | high vol + clean structure | +1 |

**Deductions:**
| Signal | Condition | Points |
|---|---|---|
| Risk HIGH | low vol or extended structure | Ã¢Ë†â€™2 |
| Too volatile | atr_pct > 4.0% | Ã¢Ë†â€™2 |
| RSI extreme | Overbought (>78) or oversold (<22) | Ã¢Ë†â€™2 |
| RelVol BELOW | relVol < 0.7x | Ã¢Ë†â€™2 |

Minimum to qualify as a priority pick: **4 points**

Note: The "4H structure not ranging (+2)" and "Direction not SKIP (+3)" entries
from earlier spec versions were consolidated. The 4H BOS event now directly
scores +4 (stronger signal than just "trend = bullish").

---

## Step 8: Terminal Output

Print top 10 by priority score with full detail. Then summary table. Then picks.

```
Ã¢Å¡Â¡ BINANCE FUTURES SCANNER  (SMC Edition)
[datetime PHT]
Filters: Vol >$100M | Range >10% | |Change| >3% | [X] matched
SMC Engine: BOS/ChoCh + FVG + IDM + OB + OTE + ATR

SHORTLIST Ã¢â‚¬â€ TOP 10 PRIORITY SETUPS
[#]. [SYMBOL]  [Ã°Å¸â€œË† GAINER / Ã°Å¸â€œâ€° LOSER]
   Direction  : [Ã°Å¸Å¡â‚¬ SCALP LONG / Ã°Å¸ÂÂ» SCALP SHORT / Ã¢ÂÂ³ SKIP]
   24H Change : [X]%  |  Vol: $[X]M  |  Range: [X]%
   Structure  : 4H=[TREND]  1H-event=[EVENT]
   MA Stack   : 1H=[Bullish/Bearish/Mixed]  4H=[Bullish/Bearish/Mixed]
   ATR        : [X.XX]% of price  |  RSI [X]
   Volume     : [Spike/Fading/Normal]  |  RelVol: [X.X]x  ([label])
   SMC Flags  : [Ã°Å¸ÂªÂ¤ INDUCEMENT / Ã°Å¸Å½Â¯ IN OTE / Ã°Å¸Å½Â¯ IN FVG / Ã°Å¸â€œÂ¦ AT OB / Ã¢Å¡Â¡ MSS / Ã¢Å¡Â¡ COILING / Ã¢Å¡Â Ã¯Â¸Â NEAR LIQ / Ã¢â‚¬â€]
   Ã¢Å¡Â Ã¯Â¸Â [rsi warning if applicable]
   Why        : [1Ã¢â‚¬â€œ2 sentences based on dominant SMC signal]
   Risk       : [Ã°Å¸Å¸Â¢/Ã°Å¸Å¸Â¡/Ã°Å¸â€Â´]
   Priority   : [X pts]

SUMMARY TABLE
[# | Symbol | T | Direction | 24H% | $M | ATR% | RSI | Flag | Pts]

Ã°Å¸Å½Â¯ PRIORITY PICKS  (score Ã¢â€°Â¥ 4, SMC-qualified)
  [#]. [SYMBOL] (score: X) Ã¢â‚¬â€ [LONG/SHORT] + [top flag]
       [why Ã¢â‚¬â€ 1 line]
  Ã¢â€ â€™ scalp [SYMBOL] for full SMC analysis

Ã¢â€ºâ€ NO TRADE  (if no picks qualify)
  No SMC confluence. Re-scan in 30 min or check session timing.
```

---

## Step 9: Send Telegram

```powershell
# Telegram credentials are now read from the .env file in the root directory.
# Ensure TG_TOKEN and TG_CHAT are configured there.
```

Include: top 8 coins (1 line each with direction, flags, risk), priority picks,
re-scan suggestion if no picks.
Truncate at 4093 chars.

Success: print "Ã¢Å“â€¦ Scanner sent to Telegram"
Failure: print "Ã¢Å¡Â Ã¯Â¸Â Telegram failed" and continue

---

## Key Principle Change (Retail Ã¢â€ â€™ Institutional)

Retail sent you to scalp a coin because it had a bullish MA stack and high volume.
Institutional sends you to scalp a coin because:
1. The 4H market structure has a confirmed BOS above a swing high (real commitment)
2. Price is in an inducement zone, unfilled FVG, or at an unmitigated Order Block
3. The entry zone has institutional logic Ã¢â‚¬â€ not just "price is above MA"

The difference is whether you're entering where retail enters (after MA confirmation)
or where institutions load positions (at imbalance zones before the move).

---

## ACTIVATION KEYWORDS
scan | scanner | scan the market | what's moving | find something to scalp |
show me movers | what to trade | market scan | scan binance | find me a trade
