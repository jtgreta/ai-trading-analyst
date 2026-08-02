---
name: hunter
description: >
  Institutional pre-breakout scanner. Scans all Binance Futures tickers for coins
  coiling at key levels before a directional break. Applies SMC overlay: BOS/ChoCh
  context for breakout direction, Fair Value Gap detection as the breakout target,
  Order Block identification at the coil zone, and ATR-based stop/position sizing.
  Scores each setup 0–10 (range contraction + volume + structure + FVG + relVol +
  inducement bonus). Produces a full trade plan for setups scoring ≥ 6. No need to
  run Scalper after.
version: institutional
---

# HUNTER — Institutional Pre-Breakout Scanner

## What Changed from Retail (and Why)
The original hunter (and the "moonshot" variant) had two separate personalities
that conflicted: one looking for tight coils, the other looking for low-volatility
accumulation bases. Institutional Edition consolidates back to the core purpose:

**Find coins that are ABOUT TO MOVE, not ones that HAVE moved.**

Key upgrades:
- SMC market structure replaces pure MA trend check for direction (Component C)
- ChoCh on 1H is treated as a bonus signal — a structural micro-breakout happening
  inside the coil = institutional hand being revealed early
- FVG is now a coil scoring component: if price is compressing INTO an unfilled
  FVG, the gap is the magnet driving the eventual breakout
- RSI deduction added: overbought compressing setup = exhausted, not coiling
- ATR-based stops replace the flat max_sl% calculation
- Inducement + OB Confluence bonus: liquidity grab at an Order Block = institutional
  positioning confirmed. Highest-conviction coil signal.

---

## Runtime Notes
- PowerShell runs internally — use `python` or `curl.exe`
- Wrap all URLs in double quotes when using curl.exe
- trading_utils.py must be in the same directory
- Ensure VPN is active on hotspot — Binance API may be restricted
- Fetch ALL data before computing — do not compute mid-fetch

---

## ⚠️ PYTHON FILE NAMING CONVENTION — MANDATORY

When creating any Python helper file for this skill, name it:
`skill_hunter_<purpose>.py`

Examples:
- `skill_hunter_scan.py`    — full pipeline (preferred single file)
- `skill_hunter_filter.py`  — ticker fetch + pre-breakout filter only
- `skill_hunter_coil.py`    — coil scoring + trade plan for named symbols

**Before creating a new file, ALWAYS check if it already exists:**
```powershell
Test-Path "C:\Users\Jerome\gemini-trading-analyst\skill_hunter_scan.py"
Test-Path "C:\Users\Jerome\gemini-trading-analyst\skill_hunter_filter.py"
Test-Path "C:\Users\Jerome\gemini-trading-analyst\skill_hunter_coil.py"
```
If found, run directly. Do not rewrite.

All Python files live in:
`C:\Users\Jerome\gemini-trading-analyst\`

---

## CAPITAL & POSITION SIZING RULES

Total capital: $100 | Max risk: $3.00 | Min RR: 1:2

| Type | Leverage | Margin (A/B) | Max SL% |
|---|---|---|---|
| New/Meme/AI | 3x | $5 / $2.50 | 20% |
| Mid-cap | 5x | $7 / $3.50 | 8.5% |
| BTC/ETH/BNB | 10x | $10 / $5 | 3% |

Grade A (score 8–10) → full margin
Grade B (score 6–7) → half margin

Partial exit rules:
- TP1 = 35% closed → move SL to breakeven
- TP2 = 40% closed → activate trailing stop
- TP3 = 25% trail remainder

---

## Activation Triggers
- "hunt" / "hunter" / "snipe" / "ambush" / "go hunting"
- "hunt breakouts" / "find me a breakout" / "coil scan"
- "what's about to move" / "what's loading up" / "pre-breakout scan"
- "find the next move" / "stalk the market"

---

## Session Timing (PHT / UTC+8)
- Pre-breakout coils usually trigger during London/NY open volatility.
- The script checks current session quality and advises if the market is too illiquid (Asian session) for a breakout.

---

## Preferred Execution

If `skill_hunter_scan.py` exists:
```powershell
python "C:\Users\Jerome\gemini-trading-analyst\skill_hunter_scan.py"
```

This handles full pipeline: filter → score → trade plan → output → Telegram.

To analyze specific symbols directly:
```powershell
python "C:\Users\Jerome\gemini-trading-analyst\skill_hunter_coil.py" SOLUSDT ETHUSDT
```

To get the filter list only:
```powershell
python "C:\Users\Jerome\gemini-trading-analyst\skill_hunter_filter.py" --verbose
```

---

## Step 1: Filter Candidates

Fetch:
```
curl.exe "https://fapi.binance.com/fapi/v1/ticker/24hr"
```

Keep symbols where (all float-cast):
- quoteVolume > 100,000,000
- 3 < rangePercent < 25
- absChange < 15

Exclude substrings: USDC, BUSD, TUSD, DAI, FDUSD
Exclude exact: BTCDOMUSDT, DEFIUSDT, ALTUSDT
Relax range max to 30 if fewer than 5 pass.

---

## Step 2: Fetch Klines Per Candidate

```
15M: limit=50
1H: limit=100
4H: limit=100
```

Kline index: [0]=openTime [1]=open [2]=high [3]=low [4]=close [5]=baseVol [7]=quoteVol
Use index -1 as forming candle (excluded from scoring). Use [-5:-1] for last 4 closed.

---

## Coil Score Components (0–10)

### A. Range Contraction on 15M (max 3 pts)
```
last4_ranges = [k15[i][2] - k15[i][3] for i in range(-5, -1)]
prev4_ranges = [k15[i][2] - k15[i][3] for i in range(-9, -5)]
contraction  = avg(last4) / avg(prev4)
```
- < 0.50 → 3 pts  |  < 0.65 → 2 pts  |  < 0.80 → 1 pt  |  ≥ 0.80 → 0

### B. Volume Behaviour on 15M (max 2 pts)
```
vol_ratio = avg(last4_vol) / avg(prev4_vol)
```
- > 1.4 → 2 pts  |  > 1.1 → 1 pt  |  ≤ 1.1 → 0

### C. Market Structure on 1H + 4H (max 2 pts)
```
ms_4h = detect_market_structure(k4h, lookback=30)
ms_1h = detect_market_structure(k1h, lookback=30)
```
- 4H bullish + 1H bullish/ranging → 2 pts, direction = LONG
- 4H bearish + 1H bearish/ranging → 2 pts, direction = SHORT
- 4H bullish only (1H conflicting) → 1 pt, direction = LONG (weaker)
- 4H bearish only (1H conflicting) → 1 pt, direction = SHORT (weaker)
- 4H ranging → 0 pts; fallback to MA lean (still 1 pt if clear MA direction)

**Why this replaces MA trend check:**
MA trend says "price has been above MA recently." BOS says "price just broke
a confirmed swing high — institutions committed." BOS is a real event; MA lean is a lag.

### D. ChoCh Bonus (max 1 pt)
```
if ms_1h.mss == True: score += 1
```
A ChoCh (Market Structure Shift) on 1H inside a coiling setup = the coil is
actually a structural reversal building. Institutions are already stepping in.
This is not a deduction — it's a confirmation that the coil has an SMC catalyst.

### E. FVG Proximity (max 1 pt)
```
fvgs = detect_fvg(k1h, lookback=25)
if any FVG midpoint within 1.5% of price: score += 1
```
A coin coiling inside or adjacent to an unfilled FVG has a price target already
defined by institutional imbalance. The FVG is the destination of the breakout.
This makes the setup more predictable — not just "will it break?" but "where to."

### F. Relative Volume vs 24H Baseline (max 1 pt)
```
rel_vol = last_1h_quote_vol / (24h_quote_vol / 24)
```
- > 1.5 → 1 pt

### BONUS. Inducement + Order Block Confluence (max +3 pts)
```
idms = identify_inducement(k1h, swing_highs, swing_lows, trend, lookback=30)
obs  = detect_order_blocks(k1h, lookback=30)
nearby_ob = any OB midpoint within 1.5% of price

if idms and nearby_ob: score += 3   # liquidity grab + OB confluence
elif idms:             score += 1   # liquidity grab only (no OB)
```
A confirmed liquidity grab (inducement sweep that reversed) at an unmitigated
Order Block = institutional positioning confirmed. This is the highest-conviction
coil signal because it shows:
1. Smart money swept retail stops (inducement)
2. The reversal happened at a known institutional zone (OB)
3. The coin is now coiling inside that zone — loading for the real move

This is why the score can exceed 10 theoretically — max = 3+2+2+1+1+1+3 = 13,
clamped to 10. In practice, a score of 8+ with IDM+OB = prime setup.

### RSI Deduction
```
rsi_1h = RSI(k1h_closes, 14)
if direction == LONG and rsi_1h > 75: score -= 1
if direction == SHORT and rsi_1h < 25: score -= 1
```
A coil with RSI already extreme means: compression is happening at an exhaustion
point. The breakout, if it comes, may be a fakeout. Deduct and flag.

---

## Coil Score Interpretation
- 8–10 : 🔥 PRIME SETUP  — grade A, full margin
- 6–7  : ✅ GOOD SETUP   — grade B, half margin
- 4–5  : 👀 WATCH ONLY   — not ready, re-scan in 30 min
- 0–3  : ❌ SKIP         — no coil

---

## Step 3: Token Classification

For each coin scoring ≥ 6:
- BTCUSDT, ETHUSDT, BNBUSDT → major: 10x, $10 margin, 3% max SL
- quoteVolume > $500M → midcap: 5x, $7 margin, 8.5% max SL
- Everything else → new: 3x, $5 margin, 20% max SL

---

## Step 4: Build Trade Plan (ATR-based stops)

```
# Entry zone from last 4 closed 15M candles
entry_low  = min([k15[i][3] for i in range(-5,-1)])
entry_high = max([k15[i][2] for i in range(-5,-1)])
entry_mid  = (entry_low + entry_high) / 2

# ATR-based stop anchored to entry midpoint
atr_1h     = ATR(k1h, 14)
sl_distance = min(atr_1h × 1.5, entry_mid × max_sl_pct)

SL (LONG)  = entry_mid - sl_distance
SL (SHORT) = entry_mid + sl_distance
sl_pct     = sl_distance / entry_mid

TP1 = entry_mid ± sl_distance × 2.0
TP2 = entry_mid ± sl_distance × 3.5
TP3 = Trailing Stop (trail distance = sl_distance)

# Refine TP1: if a nearby FVG exists in breakout direction with RR ≥ 1.5,
# use FVG boundary as TP1 target (more precise than raw RR multiple)
if nearby_fvg and direction == LONG and fvg.top > entry_mid:
    rr_fvg = (fvg.top - entry_mid) / sl_distance
    if rr_fvg >= 1.5: tp1 = fvg.top
if nearby_fvg and direction == SHORT and fvg.bottom < entry_mid:
    rr_fvg = (entry_mid - fvg.bottom) / sl_distance
    if rr_fvg >= 1.5: tp1 = fvg.bottom

# Dynamic sizing based on grade
grade = A if score >= 8 else B
sizing = calc_position(tok_type, sl_pct, mode="scalp", setup_grade=grade)

# Risk cap
if sizing.risk > $4.00: reduce margin until risk ≤ $4.00
```

---

## Step 5: Terminal Output Format

```
═══════════════════════════════════════════════════════
  🎯 HUNTER — PRE-BREAKOUT SCAN  (SMC Edition)
  [datetime PHT]
═══════════════════════════════════════════════════════

🔥 QUALIFIED SETUPS (Coil Score ≥ 6)

[#]. [SYMBOL] — Coil Score: [X]/10 [🔥 PRIME / ✅ GOOD]  [dir_emoji] [LONG/SHORT]
Type       : [token type]  |  Grade: [A/B]  ([Full/Half] margin)
Volume     : $[X]M  |  RelVol: [X.X]x  |  ATR: [X] ([X.X]% of price)
Structure  : 4H=[TREND]  |  1H-event=[EVENT]
Why now    : [1–2 sentences: which coil components + SMC signal fired]

📐 TRADE PLAN  (ATR × 1.5 stops)
Entry Zone : [low] – [high]  (enter on breakout CLOSE [above/below] [trigger] + volume)
Stop-Loss  : [SL]  ([SL%] from mid)
TP1 (35%)  : [TP1] — RR 1:2.0 → move SL to breakeven
TP2 (40%)  : [TP2] — RR 1:3.5 → activate trailing stop
TP3 (25%)  : Trailing ([trail_distance] trail)

💰 POSITION SIZING  (Grade [A/B])
[token type] | [Lev]x | Margin: $[X] | Position: $[X]
Actual Risk: $[X.XX]  ([✅ within rules / ⚠️ WIDE STOP])

───────────────────────────────────────────────────────

👀 WATCH LIST (Score 4–5)
[# | Symbol | score/10 | direction | why watching — 1 line]

VERDICT
[🎯 HUNT READY / 👀 SETUPS FORMING / ⛔ NO HUNT]
[Trigger level, structure context, do-not-chase distance]
```

---

## Step 6: Verdict Block

**If score ≥ 6 with direction:**
```
🎯 HUNT READY — [X] setup(s) qualified
Best setup: [SYMBOL] (score [X]/10) — Grade [A/B]
Structure : 4H=[TREND] | 1H=[EVENT]
Direction : [🚀 LONG / 🐻 SHORT]
Enter when: Candle CLOSES [above entry_high / below entry_low] with volume spike
FVG Target: [if applicable — shows where price is heading]
Do NOT chase if price already moved >[trail_distance] past the zone.
SL and TP must be set before entry.
```

**If only watch-list setups:**
```
👀 SETUPS FORMING — not ready yet
Watching: [symbols]
Re-scan in 30 min — coil needs more time.
```

**If nothing qualifies:**
```
⛔ NO HUNT — nothing is coiling
Reason: [market already moved / low liquidity / no structural compression]
Re-scan at 9:00 PM PHT when London-NY session opens.
```

---

## Step 7: Send Telegram

```powershell
# Telegram credentials are now read from the .env file in the root directory.
# Ensure TG_TOKEN and TG_CHAT are configured there.
```

Include per qualified setup (max 3): symbol, score, direction, grade,
volume, rel_vol, FVG note, IDM flag, entry zone, SL, TP1, TP2, margin, risk, 1-line why.
Then watch list symbols. Then verdict.
Truncate at 4093 chars.

Success: print "✅ Hunter sent to Telegram"
Failure: print "⚠️ Telegram failed — [error]" and continue

---

## ACTIVATION KEYWORDS
hunt | hunter | snipe | ambush | coil | coiling | pre-breakout |
go hunting | what's loading | what's coiling | find the next move |
hunt breakouts | find me a breakout | stalk the market | what's about to move
