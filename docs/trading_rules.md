# Trading Rules: Institutional Discipline Mode

These rules are non-negotiable. No exceptions. No "just this once."

## 1. Capital & Position Sizing
**Total trading capital: $100** (Update when this changes)
**Max risk per trade: $3.00 – $4.00** (3–4% of current capital)

### Sizing Table (Binance Futures)
Position size must be calculated based on the stop-loss distance to ensure the total risk never exceeds $4.

| Token Type | Leverage | Margin | Max SL% | Risk Cap |
| :--- | :--- | :--- | :--- | :--- |
| **Majors (BTC/ETH/BNB)** | 10x | $10 | 3% | $\le$ $4 |
| **Mid-cap Altcoins** | 5x | $7 | 8.5% | $\le$ $4 |
| **Memes / New / AI** | 3x | $5 | 20% | $\le$ $4 |

**Formula:** $	ext{Position Size} = \frac{	ext{Capital} 	imes 0.03}{	ext{Stop-Loss Distance}}$
**Rule:** $	ext{Margin} 	imes 	ext{Leverage} 	imes 	ext{SL\%}$ must always be $\le$ $4.

## 2. Stop-Loss & Take-Profit Rules

### Stop-Loss (SL)
* **Set Before Entry**: SL must be entered into the system *before* the trade is opened.
* **No Moving Backwards**: SL is never moved to increase the risk.
* **Acceptance**: If you feel the urge to move the SL, close the trade instead.

### Take-Profit (TP)
* **Minimum RR**: 1:2 (TP1 must be $\ge 2	imes$ SL distance).
* **Partial Exits**:
  - **Scalps**: TP1 (35%), TP2 (40%), TP3 (Trail remainder).
  - **Swings**: TP1 (30%), TP2 (40%), TP3 (Trail remainder).
* **Risk Management**: After TP1 is hit, move SL to **Breakeven**. After TP2, activate a trailing stop.

## 3. Volatility Context (PHT / UTC+8)
Trade 24/7 based on signal quality, but adjust aggression levels based on institutional volume clusters.

| Session | PHT Time | Volatility Context | Rule |
| :--- | :--- | :--- | :--- |
| **Early Asian Pulse** | 5:00 AM – 8:00 AM | 🟡/🟢 **Mod-High Vol** | Increased aggression. Early trend setters. |
| **Asian Session** | 8:00 AM – 12:00 PM | 🟡 **Low Vol** | Conservative. Grade A favored. Higher risk of chop. |
| **London Open** | 3:00 PM – 5:00 PM | 🟢 **High Vol** | **Prime Window.** Maximum aggression. Impulsive moves. |
| **London–NY Gap**| 5:00 PM – 9:00 PM | 🟡 **Moderate** | Moderate aggression. Favor clear structural alignment. |
| **NY Overlap** | **9:30 PM – 12:00 AM**| 🟢 **High Vol** | **Prime Window.** Maximum aggression. High liquidity. |
| **Off-hours** | 12:00 AM+ | 🟡 **Low Vol** | Conservative. Grade A favored. Watch for fakeouts. |

**Daily Routine (Guideline, not Hard Block):**
* **9:00 PM**: Run Scanner $\rightarrow$ Get shortlist.
* **9:15 PM**: Run Scalper/Hunter on top 1–2 coins.
* **9:30 PM**: Enter if **Score $\ge$ 6** and all checklist items are ✅.


## 4. AI Signal & Grading System
Do not override the AI signal based on gut feeling.

* **Grade A (Score 8–10)**: Full Margin. High conviction.
* **Grade B (Score 6–7)**: Half Margin. Moderate conviction.
* **Grade C (Score < 6)**: **WAITING ROOM**. Not a trade. Wait for conditions to improve.

**Rule**: If you disagree with the signal, skip the trade. Do not take the opposite.

## 5. Entry Principles (SMC Framework)
Avoid retail traps. Use institutional markers.

1. **Trend Alignment**: Check 1H and 4H direction. Only look for longs in a bullish HTF trend and shorts in a bearish HTF trend.
2. **The Retest Rule**: Never chase the first breakout candle. Wait for the price to return to:
   - A **Bullish/Bearish Order Block (OB)**.
   - A **Fair Value Gap (FVG)** fill.
3. **Volume Validation**: Ensure volume is rising on the reversal/continuation move. Fading volume = weak momentum.
4. **Liquidity Grab**: Look for "stop hunts" (price dipping below a low then snapping back) before entering.

## 6. Daily Session Limits
If these are hit, close the platform and walk away.

* **Max Daily Loss**: 3% of capital.
* **Max Scalps per Day**: 5 trades.
* **Max Simultaneous Trades**: 2–3 positions.
* **Max Consecutive Losses**: 3 (triggers immediate 24h cooldown).

## 7. Entry Checklist
All boxes must be checked before entry:
- [ ] Signal score $\ge$ 6 (Grade B or A).
- [ ] 1H + 4H trend aligns with direction.
- [ ] Entry is on a **retest/FVG fill**, not a chase.
- [ ] Volume supports the move.
- [ ] Stop-loss is identified and pre-set.
- [ ] Position size is calculated ($\text{Risk} \le \$4$).
- [ ] Risk-to-Reward is $\ge$ 1:2.
- [ ] Daily loss limit NOT hit.
- [ ] Emotional state is neutral (not anxious or revenge-seeking).

## 8. Forbidden Behaviors
❌ Revenge trading or doubling down.
❌ Moving SL to "give the trade room."
❌ Trading without a stop-loss "temporarily."
❌ Chasing breakout candles.
❌ Ignoring the AI "Waiting Room" result.
❌ Overtrading in Low-Vol windows with Grade B setups.

## 9. Weekly Review
Every weekend, review the log:
* Compliance rate: Did I follow the signals exactly?
* Rule violations: Where did I deviate?
* Performance: Actual Win Rate vs. Average RR.
* Psychology: Did I trade emotionally?

Last updated: June 2026