---
name: swing
description: >
  Institutional multi-day swing trading protocol. Analyzes 4H, 1D, and 1W
  timeframes using SMC market structure (BOS/ChoCh), Fair Value Gaps on the
  daily chart as primary entry targets, Order Blocks on 4H as timing zones,
  and ATR-based volatility stops. Hard-gated by 1W macro trend and key-level
  proximity. Grades setup A/B/C with dynamic margin sizing. Targets 2–14 day
  holds of 15–40%+. Optimized for $100 account.
version: institutional
---

# Swing Trader — Institutional Trend + Pullback Protocol

## What Changed from Retail (and Why)
The original swing skill checked MA stacks and "pullback near MA" with fixed
stops. This worked in trending markets but failed when:
- Price was near an MA but no structural reason to hold it (MA ≠ order flow)
- Stops were too fixed — volatile alts needed wider stops, major pairs needed tighter
- No check for whether the weekly macro trend was actually intact

Institutional Edition fixes all three:
- 1W market structure is the hard gate (not just MA20 check)
- 1D FVGs replace "near MA" as the primary entry trigger
- 4H ATR × 2.0 replaces fixed max_sl% as the stop engine

---

## Runtime Notes
- PowerShell runs internally — use `python` or `curl.exe`
- Wrap URLs in double quotes
- trading_utils.py must be in the same directory
- Ensure VPN is active on hotspot

---

## ⚠️ PYTHON FILE NAMING CONVENTION — MANDATORY

When creating any Python helper file for this skill, name it:
`skill_swing_<purpose>.py`

**Before creating, ALWAYS check if it already exists:**
```powershell
Test-Path "C:\Users\Jerome\gemini-trading-analyst\skill_swing_analyze.py"
```
If found, run it directly. Do not rewrite.

All Python files live in:
`C:\Users\Jerome\gemini-trading-analyst\`

---

## Account Settings ($100 — Swing)
- Max risk per trade: $3–$4
- Hold time: 2–14 days
- Max open swing trades: 1–2

| Token Type | Leverage | Margin (A/B/C) | Max SL% |
|---|---|---|---|
| New/Meme/AI | 2x | $5 / $2.50 / blocked | 30% |
| Mid-cap | 3x | $7 / $3.50 / blocked | 14% |
| BTC/ETH/BNB | 5x | $10 / $5 / blocked | 6% |

Grade A (score 8+) → full margin
Grade B (score 6–7) → half margin
Grade C → WAITING ROOM (not a trade)

---

## Session Timing (PHT / UTC+8)
- Swing management is generally timezone-agnostic.
- However, Asian Session is strictly for management, not for new triggers.

## Activation Triggers
- "swing trade [TICKER]"
- "swing [TICKER]"
- "is [TICKER] good for swing?"
- "multi-day trade on [TICKER]"
- "using swing protocol"

---

## Preferred Execution

If `skill_swing_analyze.py` exists:
```powershell
python "C:\Users\Jerome\gemini-trading-analyst\skill_swing_analyze.py" SYMBOL
```

With correlation check:
```powershell
python "C:\Users\Jerome\gemini-trading-analyst\skill_swing_analyze.py" SYMBOL BTCUSDT,SOLUSDT
```

---

## Step 1: Fetch Binance Data

```
curl.exe "https://fapi.binance.com/fapi/v1/klines?symbol=SYMBOL&interval=4h&limit=150"
curl.exe "https://fapi.binance.com/fapi/v1/klines?symbol=SYMBOL&interval=1d&limit=250"
curl.exe "https://fapi.binance.com/fapi/v1/klines?symbol=SYMBOL&interval=1w&limit=52"
curl.exe "https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=SYMBOL"
```

Kline index: [0]=openTime [1]=open [2]=high [3]=low [4]=close [5]=baseVol [7]=quoteVol

---

## Step 2: SMC Analysis Sequence

Run in this order — each level informs the one below it.

### A. Weekly Structure (Macro Gate — most important)
```
ms_1w = detect_market_structure(k1w, lookback=20)
```
- "bullish" → only look for LONG setups on lower timeframes
- "bearish" → only look for SHORT setups on lower timeframes
- "ranging" → HARD FILTER: no swing trade (see HF-1)

The weekly structure overrides everything. A coin with a perfect 1D setup
in a weekly downtrend is still a SKIP — the institutional trend is down.

### B. Daily Structure (Trade Direction)
```
ms_1d = detect_market_structure(k1d, lookback=40)
```
- BOS_up on 1D in a 1W bullish context = highest conviction LONG setup
- ChoCh on 1D = structural reversal — the pullback may become a new trend
  Do not automatically trade the old direction after a daily ChoCh

### C. Fair Value Gaps (1D — Primary Entry Zone)
```
fvgs_1d = detect_fvg(k1d, lookback=20)
```
Daily FVGs are the PRIMARY entry targets for swing trades. Price fills
imbalances — an unfilled bullish FVG below price is where smart money
re-enters in a bull trend. This is more precise than "near MA" because:
- FVGs are created by specific institutional order flow events
- MA levels are lagging and not always defended

Entry priority (in order):
1. FVG midpoint on 1D (if within 3% of price) → highest precision
2. 1D MA50 (±4%) → classic swing support/resistance
3. 1D MA20 (±4%) → shorter-term swing support (no score points, but qualifies)
4. 1D MA200 (±5%) → major structure level (no score points, but qualifies)

If price is not near any of these → HARD FILTER (HF-2): wait for pullback.

### D. Order Blocks (4H — Entry Timing)
```
obs_4h = detect_order_blocks(k4h, lookback=40)
```
When price reaches the 1D entry zone, use 4H OBs for precise timing:
- Bullish OB on 4H at the 1D FVG level = maximum confluence
- Wait for the 4H candle to close at/above the OB zone before entry

### E. Momentum Divergence (1D — Pullback Confirmation)
```
div_1d = detect_divergence(k1d, lookback=40)
```
Bullish divergence on the daily during a pullback = sellers exhausted:
- Price: lower low | RSI: higher low → buyers stepping in → entry signal
- This is when to pull the trigger at the FVG/MA level
- No divergence = wait; the pullback may continue further

---

## Step 3: Hard Filter System

### HF-1: 1W macro trend must be defined
- ms_1w.trend == "ranging" → BLOCKED
- Reason: swing trades need multi-week context. A ranging weekly = no macro tailwind.

### HF-2: Must be at a key entry level
Price must be within tolerance of at least one:
- 1D FVG midpoint (±3%)
- 1D MA50 (±4%)
- 1D MA20 (±4%)
- 1D MA200 (±5%)

If none satisfied → BLOCKED with message: "Wait for pullback — price is extended."
This is the most important filter. It prevents chasing.

Both filters must pass. Failure on either = WAITING ROOM.

---

## Step 4: Confluence Score (0–10)

| Signal | Condition | Points |
|---|---|---|
| 1W macro trend alignment | Price on correct side of 1D MA20 | +2 |
| 1D structure — BOS | BOS event in direction of trade | +2 |
| 1D structure — ChoCh | ChoCh aligns with trade direction | +2 |
| At 1D FVG midpoint | FVG midpoint ±3% | +2 |
| At 1D MA50 | MA50 ±4% (only if no FVG) | +1 |
| 4H reversal confirmed | 4H trend or ChoCh aligned with trade direction | +2 |
| Daily volume | Daily volume > 20D average on current bar | +1 |
| RSI divergence | 1D bullish (long) or bearish (short) RSI divergence | +1 |
| ChoCh deduction | 1D ChoCh AGAINST trade direction | −1 |

Notes:
- MA20 and MA200 as key levels unlock the HF-2 gate but do NOT score points
  (they are qualifiers, not confluence signals).
- Only ONE key level scores: FVG (+2) takes priority over MA50 (+1).
  If at FVG midpoint, do not also add MA50 points even if both are nearby.

| Score | Grade | Decision |
|---|---|---|
| 8–10 | A | Full margin — high conviction |
| 6–7 | B | Half margin — moderate conviction |
| <6 | C | WAITING ROOM — wait for better setup |

---

## Step 5: ATR-Based Stop Calculation

Use 4H ATR (captures intraday volatility relevant to swing entries):

```
atr_4h = ATR(k4h, 14)
sl_distance = min(atr_4h × 2.0, entry × max_sl_pct)

LONG:  SL = entry - sl_distance
SHORT: SL = entry + sl_distance

TP1 = entry ± sl_distance × 2.0   RR 1:2  (close 30%)
TP2 = entry ± sl_distance × 3.5   RR 1:3.5 (close 40%)
TP3 = Trailing Stop (trail distance = sl_distance) (30%)
```

Why 4H ATR for swing (not 1D)? Daily ATR is too wide for a $100 account —
it would push sl_distance beyond max_sl% on most altcoins. 4H ATR × 2.0
gives a stop that breathes through intraday noise but closes out on a
genuine structural break.

---

## Step 6: Dynamic Position Sizing

```
Grade A: full margin (see table)
Grade B: margin × 0.50
Grade C: WAITING ROOM — not a trade

Hard risk cap: if (margin × leverage × sl_pct) > $4.00:
  margin = $4.00 / (leverage × sl_pct)
  Recompute position = margin × leverage
```

---

## Step 7: Terminal Output (4 Mandatory Sections)

Print in this exact order:

**Section 1: SESSION CHECK**
- Current PHT window + quality rating.

**Section 2: MARKET STRUCTURE SUMMARY**
- 1W Trend, 1D Trend, MSS flag
- Nearest 1D FVG and 4H OB
- Liquidity (EQH/EQL on 1D)
- RSI state + divergence

**Section 3A: TRADE PLAN (If score ≥ 6 and both hard filters pass)**
- Direction, grade, entry zone (FVG midpoint preferred → MA fallback)
- 4H ATR-based stops (SL, TP1 30%, TP2 40%, TP3 Trail)
- Position sizing ($3-$4 max risk)
- Invalidation: "1D candle close [above/below] [SL level]"
- Management note: check morning and evening only

**Section 3B: WAITING ROOM (If score < 6 or blocked)**
- Why not now
- What would unlock a trade (specific level for LONG and SHORT)
- Key levels to watch
- Pre-conditions status checklist
- Next check time: "Daily close (8 AM PHT)" and re-run command

---

## Step 8: Send Telegram

```powershell
# Telegram credentials are now read from the .env file in the root directory.
# Ensure TG_TOKEN and TG_CHAT are configured there.
```

Include: direction, score/grade, hold period, 1W/1D/4H trend, MSS flag,
divergence, daily MAs, trade plan, position grade.
Truncate at 4093 chars.

---

## Rules Unchanged from Retail
1. 1W trend is the master — never fight it (now enforced as hard filter)
2. Only enter at a key level (now: FVG preferred over MA)
3. Check once or twice daily — not every 5 minutes
4. TP1 quickly to lock profit, let TP2/TP3 run

---

## ACTIVATION KEYWORDS
swing | swing trade | multi-day | is SYMBOL good for swing |
swing protocol | hold SYMBOL | longer trade SYMBOL
