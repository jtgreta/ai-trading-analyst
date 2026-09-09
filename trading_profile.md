Trader Profile

This file gives Claude context about who I am as a trader — my background, tendencies, weaknesses, and goals. Reference this when giving advice.


1. Basic Profile

Trading style: Scalping (primary), swing trading (secondary)
Market: Crypto — Binance Futures
Experience level: Intermediate — has been trading for some time but not consistently profitable
Trading platform: Binance (Futures)
Current capital: $100


2. My AI Signal System (SMC Upgraded)
I use a multi-stage AI signal system powered by custom skills. The system has evolved from simple MA confluence to an institutional "Smart Money Concepts" (SMC) framework.

### Stage 1 — Scanner (Momentum Discovery)
**Goal**: Identify high-volume movers and rank them by institutional priority.
* **Logic**: Filters for volume >$100M and 24H range >10%.
* **Ranking**: Ranks coins by SMC priority: BOS (Break of Structure), FVG (Fair Value Gap), and OB (Order Block).
* **Output**: A ranked shortlist with direction bias.
* **Activation**: "scan the market", "find something to scalp", "what's moving"

### Stage 2 — Scalper (Precision Execution)
**Goal**: Quick wins by riding existing structural trends.
* **Logic**: Enforces a 4H structure gate. Identifies high-probability entries at FVG/OB levels.
* **Scoring**: Confluence score 0–10.
  - **Grade A (8–10)**: Full Margin.
  - **Grade B (6–7)**: Half Margin.
  - **Grade C (<6)**: WAITING ROOM (No trade).
* **Activation**: "scalp [TICKER]", "analyze [TICKER]"

### Stage 3 — Hunter (Pre-Breakout / Accumulation)
**Goal**: Asymmetric returns by finding coins coiling before an explosion.
* **Logic**: Scans for 15M range contraction + 1H structural shifts (ChoCh) occurring inside an FVG.
* **Goal**: Catch the "moon-bag" moves early.
* **Activation**: "hunt"

### Stage 4 — Swing (Macro Trend)
**Goal**: Multi-day holds (2–14 days) for 15–40%+ gains.
* **Logic**: 1W macro trend alignment. Primary entry is the 1D FVG midpoint.
* **Risk**: Lower leverage, wider stops.
* **Activation**: "swing [TICKER]"

### Signal Output & Logging
All skills output 4 mandatory sections: Session Check, Market Structure, Trade Plan/Waiting Room, and a Telegram Summary. The summary is sent to a private channel for logging.

**Core Challenge**: The system is technically sound; the failure point is **discipline**. I often override the AI signal based on gut feeling or FOMO.


3. Known Weaknesses
These are patterns I have repeated. Call them out when you see signs of them:

| Weakness | How it shows up |
| :--- | :--- |
| **System Disobedience** | Taking trades the AI didn't signal, or ignoring a "Waiting Room" result. |
| **Revenge Trading** | Entering immediately after a loss to "recover" funds. |
| **Overconfidence** | Increasing position size or frequency after a winning streak. |
| **Emotional Overrides** | Letting "gut feeling" bypass the Grading System (e.g., taking a Grade C). |
| **Stop-Loss Neglect** | Moving stops to avoid a loss or not setting them before entry. |
| **Chasing Candles** | Entering on the first breakout candle instead of waiting for the retest/FVG fill. |
| **Overtrading** | Taking too many low-quality setups during low-volume sessions. |

4. Goals
**Short-term (next 3 months)**
* Maintain $\ge 80\%$ compliance with AI signals.
* Strictly adhere to the $3–$4 max risk per trade.
* Not blow the account.

**Medium-term (3–12 months)**
* Achieve positive expectancy over a 100+ trade sample.
* Grow capital through consistent compounding, not aggressive gambling.
* Refine the SMC logic in the skills based on logged trade data.

**Long-term**
* Transition trading into a reliable secondary income stream.
* Master the psychological aspect of institutional discipline.


5. What I Need From Claude

* **Be a Discipline Coach**: Be honest and firm, not encouraging, when I show signs of breaking rules.
* **Objective Review**: Help me review trades by asking: "Which rule did you follow?" or "Why did you override the AI signal?"
* **SMC Expertise**: Help me refine the technical implementation of BOS, ChoCh, and FVG logic in my scripts.
* **Accountability**: Remind me of this profile when I attempt to justify emotional trades.
* **No Validation**: Do not validate revenge trading or "gut feeling" reasoning.


6. Rules I Struggle With Most
(Be extra firm about these)
1. **Following the AI Signal**: I override the score/grade too often.
2. **The Hard Stop**: Walking away after hitting the daily loss limit.
3. **The Retest**: Waiting for the FVG/OB retest instead of chasing the breakout.
4. **Pre-set Stops**: Setting the SL before clicking "Buy/Sell".

Last updated: June 2026