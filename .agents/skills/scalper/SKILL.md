---
name: scalper
description: >
  Institutional multi-timeframe crypto scalping protocol. Fetches live Binance
  Futures data across 5 timeframes. Runs SMC market structure analysis (BOS/ChoCh),
  detects Fair Value Gaps and Order Blocks as entry zones, computes Optimal Trade
  Entry (OTE) Fibonacci zones, identifies inducement/liquidity grabs, applies
  ATR-based volatility stops, filters with hard gates (mid-range skip, RSI
  exhaustion, ranging structure), grades the setup A/B/C, and outputs a complete
  trade plan with dynamic position sizing. Sends summary to Telegram.
version: institutional
---

# Scalper Ã¢â‚¬â€ Institutional SMC Protocol

## Runtime Notes
- PowerShell runs internally Ã¢â‚¬â€ use `python` or `curl.exe`
- Wrap all URLs in double quotes when using curl.exe
- Ensure VPN is active on hotspot Ã¢â‚¬â€ Binance API may be restricted
- trading_utils.py lives in scripts/trading_utils.py (no repo-root dependency) - scripts import it directly from the same folder

---

## Ã¢Å¡Â Ã¯Â¸Â PYTHON FILE NAMING CONVENTION Ã¢â‚¬â€ MANDATORY

When creating any Python helper file for this skill, put it in the `scripts/` folder of this repo:
`scripts/scalper_<purpose>.py`

**Before creating, ALWAYS check if it already exists:**
```powershell
Test-Path "scripts\scalper_analyze.py"
```
If found, run it directly. Do not rewrite.

All Python scripts live in:
`scripts\`

---

## Account ($100)
Max risk: $3Ã¢â‚¬â€œ$4 per trade | Max open trades: 2Ã¢â‚¬â€œ3

| Token Type | Leverage | Margin | Position | Max SL% |
|---|---|---|---|---|
| New/Meme/AI | 3x | $5 full / $2.50 B | $15 / $7.50 | 20% |
| Mid-cap | 5x | $7 full / $3.50 B | $35 / $17.50 | 8.5% |
| BTC/ETH/BNB | 10x | $10 full / $5 B | $100 / $50 | 3% |

Setup Grade:
- A (score 8Ã¢â‚¬â€œ10) Ã¢â€ â€™ full margin
- B (score 6Ã¢â‚¬â€œ7) Ã¢â€ â€™ half margin
- C (score <6) Ã¢â€ â€™ WAITING ROOM (not a trade)

---

## Session Timing (PHT / UTC+8)
- 8:00 AM Ã¢â‚¬â€œ 12:00 PM (Asian) Ã¢â€ â€™ No new scalp entries. Manage only.
- 3:00 PM Ã¢â‚¬â€œ 5:00 PM (London) Ã¢â€ â€™ Grade A setups only.
- 9:30 PM Ã¢â‚¬â€œ 12:00 AM (Overlap) Ã¢â€ â€™ PRIME. Best setups.
- 12:00 AM+ (Off-hours) Ã¢â€ â€™ No new entries.

---

## Activation
- "scalp [TICKER]" or "analyze [TICKER]" Ã¢â€ â€™ Full Mode
- "quick scalp [TICKER]" Ã¢â€ â€™ Quick Mode (15m/1h/4h only)
- "long or short [TICKER]"

---

## Preferred Execution

If `scripts/scalper_analyze.py` exists:
```powershell
python "scripts\scalper_analyze.py" SYMBOL
```

With open positions (correlation check):
```powershell
python "scripts\scalper_analyze.py" SYMBOL ETHUSDT,SOLUSDT
```

---

## Step 1: Fetch Binance Data

```
curl.exe "https://fapi.binance.com/fapi/v1/klines?symbol=SYMBOL&interval=5m&limit=100"
curl.exe "https://fapi.binance.com/fapi/v1/klines?symbol=SYMBOL&interval=15m&limit=100"
curl.exe "https://fapi.binance.com/fapi/v1/klines?symbol=SYMBOL&interval=1h&limit=100"
curl.exe "https://fapi.binance.com/fapi/v1/klines?symbol=SYMBOL&interval=4h&limit=100"
curl.exe "https://fapi.binance.com/fapi/v1/klines?symbol=SYMBOL&interval=1d&limit=50"
curl.exe "https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=SYMBOL"
curl.exe "https://fapi.binance.com/fapi/v1/depth?symbol=SYMBOL&limit=20"
```

Kline index: [0]=openTime [1]=open [2]=high [3]=low [4]=close [5]=baseVol [7]=quoteVol

---

## Step 2: SMC Analysis (Primary Ã¢â‚¬â€ runs before MA scoring)

### A. Market Structure Shift (BOS / ChoCh)
Detect on 1H and 4H candles using swing pivot method (n=2):

**BOS (Break of Structure)** Ã¢â‚¬â€ trend continuation:
- Bullish BOS: price breaks above a confirmed swing high in a bullish trend
- Bearish BOS: price breaks below a confirmed swing low in a bearish trend
- Interpretation: healthy trend Ã¢â‚¬â€ enter on pullback after BOS

**ChoCh (Change of Character / MSS)** Ã¢â‚¬â€ reversal signal:
- ChoCh_up:   price breaks swing high in a bearish/ranging context Ã¢â€ â€™ bullish reversal
- ChoCh_down: price breaks swing low in a bullish/ranging context Ã¢â€ â€™ bearish reversal
- Interpretation: old trend may be ending Ã¢â‚¬â€ wait for confirmation candle

Rules:
- If 4H trend = "ranging" with no BOS/ChoCh Ã¢â€ â€™ HARD FILTER: no trade
- If 4H trend = "ranging" but BOS/ChoCh present Ã¢â€ â€™ soft warning, lower conviction
- If 1H shows ChoCh in the direction you want to trade Ã¢â€ â€™ bonus signal
- If 1H shows ChoCh AGAINST your trade direction Ã¢â€ â€™ deduct 1 point

### B. Fair Value Gap (FVG)
3-candle pattern: candle[i-2].high < candle[i].low (bullish FVG)
or candle[i-2].low > candle[i].high (bearish FVG)

- Unfilled FVGs are PRIMARY entry targets Ã¢â‚¬â€ price is drawn to them
- If price is inside a bullish FVG Ã¢â€ â€™ prefer LONG entry at FVG midpoint
- If price is inside a bearish FVG Ã¢â€ â€™ prefer SHORT entry at FVG midpoint
- FVG midpoint is more precise than "current market price" for entry

### C. Order Block (OB)
Last bearish candle before a strong bullish impulse = Bullish OB (demand zone)
Last bullish candle before a strong bearish impulse = Bearish OB (supply zone)

- Unmitigated OB = institutional footprint still active
- If price returns to OB zone Ã¢â€ â€™ high-probability entry/rejection point
- Use OB bottom (bullish) or OB top (bearish) as alternative entry anchor

### D. Optimal Trade Entry (OTE)
Fibonacci retracement of the most recent 1H swing leg:
- Bullish OTE zone: 61.8%Ã¢â‚¬â€œ78.6% retracement of the up-leg (discount zone)
- Bearish OTE zone: 61.8%Ã¢â‚¬â€œ78.6% retracement of the down-leg (premium zone)
- Sweet spot: 70.5% (Fib 0.705 level)
- If price is inside the OTE zone Ã¢â€ â€™ institutional pullback entry confirmed

### E. Liquidity (Equal Highs / Equal Lows)
- EQH (Equal Highs above price) = buy-side liquidity = stop-hunt magnet
- EQL (Equal Lows below price) = sell-side liquidity = stop-hunt magnet
- Price moves toward liquidity before reversing Ã¢â‚¬â€ do not place stops at EQH/EQL

### F. Inducement (Liquidity Grab)
- A minor swing level swept then reversed = smart money trapped retail stops
- Confirmed inducement (swept + reversed within 5 candles) = entry signal
- More powerful when it occurs at an OB or FVG zone simultaneously

---

## Step 3: Hard Filter System (must pass all or trade is blocked)

### HF-SESSION: Session timing
- Asian Session (8 AMÃ¢â‚¬â€œ12 PM) Ã¢â€ â€™ BLOCKED
- Off-hours (12 AM+) Ã¢â€ â€™ BLOCKED

### HF-1: No ranging 4H structure (without BOS/ChoCh)
- If detect_market_structure(k4h).trend == "ranging" AND no BOS/ChoCh present Ã¢â€ â€™ BLOCKED
- If ranging BUT BOS/ChoCh detected Ã¢â€ â€™ soft warning, proceed with caution

### HF-2: No mid-range entries
- Calculate 4H value area: [20-candle high, 20-candle low]
- Skip zone: low + 40% of range Ã¢â€ â€™ high - 40% of range (central 20% window)
- If price is inside this zone Ã¢â€ â€™ BLOCKED

### HF-3: No RSI exhaustion entries
- If 4H stack is Bullish AND RSI(1H, 14) > 76 Ã¢â€ â€™ BLOCKED
- If 4H stack is Bearish AND RSI(1H, 14) < 24 Ã¢â€ â€™ BLOCKED

All hard filters must pass. One failure = WAITING ROOM. Score does not override.

---

## Step 4: Confluence Score (0Ã¢â‚¬â€œ10)

| Signal | Condition | Points |
|---|---|---|
| 4H + 1H structure aligned | Both bullish BOS or bearish BOS | +4 |
| 4H + 1H partial alignment | Same trend, 1H weaker or forming | +2 |
| ChoCh deduction | MSS detected on 1H (structural reversal) | Ã¢Ë†â€™1 |
| FVG nearby | Price within 2% of unfilled FVG midpoint | +2 |
| OTE zone | Price inside 61.8Ã¢â‚¬â€œ78.6% Fibonacci retracement zone | +2 |
| Order Block nearby | Price within 1.5% of unmitigated OB zone | +1 |
| Inducement confirmed | Liquidity grab detected (swept + reversed) | +1 |
| Volume spike on 1H | Last candle > vol MA5 Ãƒâ€” 1.5 | +1 |
| Order book | Bids >53% long / asks >53% short | +1 |

Note: RSI divergence is detected and displayed in Market Structure but is **not
currently included in the score**. It is shown as context for manual judgment.

| Score | Grade | Decision |
|---|---|---|
| 8Ã¢â‚¬â€œ10 | A | Trade full margin |
| 6Ã¢â‚¬â€œ7 | B | Trade half margin |
| <6 | C | WAITING ROOM (No Trade) |

Maximum theoretical score: 4+2+2+1+1+1+1 = 12, clamped to 10.
Score > 10 can occur before clamping Ã¢â‚¬â€ this is normal for maximum confluence.

---

## Step 5: ATR-Based Stop Calculation

Replace fixed % stop with ATR Ãƒâ€” 1.5 (volatility-adjusted):

```
atr_14 = ATR(k1h, 14)
sl_distance = min(atr_14 Ãƒâ€” 1.5, entry Ãƒâ€” max_sl_pct)

LONG:  SL = entry - sl_distance
SHORT: SL = entry + sl_distance

TP1 = entry Ã‚Â± sl_distance Ãƒâ€” 2.0  (RR 1:2)
TP2 = entry Ã‚Â± sl_distance Ãƒâ€” 3.5  (RR 1:3.5)
TP3 = Trailing Stop (trail distance = sl_distance)
```

Use max_sl_pct as a cap: SL distance never exceeds token type's max SL%.

---

## Step 6: Entry Refinement

Priority order for entry price:
1. FVG midpoint (if within 2% of current price)
2. Order Block midpoint (if within 1.5% of current price)
3. OTE zone midpoint (Fibonacci 0.705 level, if price in OTE zone)
4. Current market price (fallback)

Then recompute ATR stops from the refined entry.

---

## Step 7: Dynamic Position Sizing (Grade-based)

```
Grade A (score 8+): full margin
Grade B (score 6-7): margin Ãƒâ€” 0.50
Grade C: WAITING ROOM Ã¢â‚¬â€ not a trade

If computed risk > $4.00:
  Reduce margin until risk Ã¢â€°Â¤ $4.00
  (margin = $4.00 / (leverage Ãƒâ€” sl_pct))
```

---

## Step 8: Terminal Output (4 Mandatory Sections)

Print in this exact order:

**Section 1: SESSION CHECK**
- Current PHT window + quality rating. Blocks entries if Asian/Midnight.

**Section 2: MARKET STRUCTURE SUMMARY**
- 4H Trend, 1H Trend, MSS flag
- Nearest FVG and OB
- OTE zone (if active)
- Liquidity (EQH/EQL)
- RSI state + divergence (display only)

**Section 3A: TRADE PLAN (If score Ã¢â€°Â¥ 6 and all hard filters pass)**
- Direction, grade, entry zone (refined: FVG Ã¢â€ â€™ OB Ã¢â€ â€™ OTE Ã¢â€ â€™ market price)
- ATR-based stops (SL, TP1 35%, TP2 40%, TP3 Trail)
- Trailing stop callback % (ATR-derived, volatility-adjusted)
- Position sizing ($3-$4 max risk)
- Invalidation: "4H candle close [above/below] [SL level]"

**Section 3B: WAITING ROOM (If score < 6 or hard filter blocked)**
- Why not now (specific reason)
- What would unlock a trade (LONG and SHORT triggers with exact price levels)
- Key levels to watch (swing highs/lows, FVG zones, liquidity)
- Pre-conditions status checklist (all 7 conditions with Ã¢Å“â€¦/Ã¢ÂÅ’)
- Next check time and re-run command

---

## Step 9: Send Telegram

```powershell
# Telegram credentials are now read from the .env file in the root directory.
# Ensure TG_TOKEN and TG_CHAT are configured there.
```

Include: direction, score/grade, structure (4H/1H trend + MSS), FVG/OB nearest,
OTE zone, timeframe summary (one line), trade plan, position grade.
Truncate at 4093 chars.

Success: print "Ã¢Å“â€¦ Telegram sent (X chars)"
Failure: print "Ã¢Å¡Â Ã¯Â¸Â Telegram failed: [error]" and continue

---

## ACTIVATION KEYWORDS
scalp | analyze | quick scalp | long or short | scalper protocol |
scalp SYMBOL | analyze SYMBOL | is SYMBOL a buy
