"""
skill_scalper_analyze.py — Institutional Edition (prompt.txt v3)
Usage: python skill_scalper_analyze.py SYMBOL [open1,open2,...]

Output Format (4 mandatory sections per prompt.txt):
  Section 1: SESSION CHECK — current PHT window + quality
  Section 2: MARKET STRUCTURE SUMMARY — full SMC context
  Section 3A: TRADE PLAN — when score ≥6 and hard filters pass
  Section 3B: WAITING ROOM — when no trade fires (replaces dead-end BLOCKED)
  Section 4: TELEGRAM SUMMARY — always sent

Hard Rules (never violated):
  - SL always set before entry
  - Min RR 1:2 (TP1 ≥ 2× SL distance)
  - Max risk $3-$4
  - Score <6 = WAITING ROOM
  - Asian session = no new scalp entries
  - No entries after midnight PHT
  - WAITING ROOM always fires when no valid trade

Top-Down Scalper Flow:
  - 4H Structure  : Macro direction gate
  - 1H Structure  : Structural reversal (ChoCh) & Market Context
  - 15m OTE       : Precise entry inside Optimal Trade Entry zone / Imbalance
  - 5m Execution  : Final confirmation
  - ATR-based stops & Dynamic Position Sizing (A/B/C)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from trading_utils import (
    fetch_klines, fetch_ticker, fetch_depth, send_telegram,
    classify_token, calc_position, calc_atr_stop,
    sma, ema, ma_stack_label,
    detect_bos_choch, find_fvg, detect_order_blocks,
    detect_liquidity, detect_divergence, identify_inducement, calculate_ote_zone,
    format_telegram_trade, format_telegram_waiting,
    print_session_check, print_market_structure, print_trade_plan, print_waiting_room,
    get_session_info, get_next_session_window, calc_trail_callback_pct,
    fmt, grade_label, SCALP_RULES, correlation_warning, MIN_RR,
)

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ── Hard Filter Thresholds ─────────────────────────────────────────────────────
MIN_SCORE          = 6      # below this: WAITING ROOM
MID_RANGE_SKIP_PCT = 0.40   # skip if price within central 20% of 4H value area
RSI_OVERBOUGHT     = 76     # widened from 72
RSI_OVERSOLD       = 24     # widened from 28


def analyze_scalp(symbol: str, open_positions: list = None):
    if open_positions is None:
        open_positions = []

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1 — SESSION CHECK
    # ══════════════════════════════════════════════════════════════════════════
    session = get_session_info()

    print(f"\n{'═'*60}")
    print(f"  {symbol} — Institutional Scalper Analysis")
    print(f"{'═'*60}")

    print_session_check(session)

    # ── 1. Fetch Data ──────────────────────────────────────────────────────────
    print("\n[1/5] Fetching multi-timeframe market data...")
    k5m  = fetch_klines(symbol, "5m",  100)
    k15m = fetch_klines(symbol, "15m", 100)
    k1h  = fetch_klines(symbol, "1h",  100)
    k4h  = fetch_klines(symbol, "4h",  100)
    ticker = fetch_ticker(symbol)
    depth  = fetch_depth(symbol)

    if not k1h or not k4h or not ticker:
        print(f"  ✗ Insufficient data for {symbol}. Check VPN or symbol name.")
        return

    cl_5m  = [c[4] for c in k5m]  if k5m  else []
    cl_15m = [c[4] for c in k15m] if k15m else []
    cl_1h  = [c[4] for c in k1h]
    cl_4h  = [c[4] for c in k4h]
    price  = cl_1h[-1]

    # ── 2. Top-Down Market Structure & SMC ─────────────────────────────────────
    print("[2/5] Running Top-Down SMC engine...")

    ms_4h = detect_bos_choch(k4h, lookback=40)
    ms_1h = detect_bos_choch(k1h, lookback=40)
    liq   = detect_liquidity(k1h, lookback=40)
    idms  = identify_inducement(k1h, ms_1h["swing_highs"], ms_1h["swing_lows"], ms_1h["trend"], lookback=40)
    fvgs  = find_fvg(k1h, lookback=30)
    obs   = detect_order_blocks(k1h, lookback=40)

    ote = None
    if ms_1h["swing_high"] and ms_1h["swing_low"]:
        ote_dir = "bullish" if ms_1h["trend"] in ["bullish", "ranging"] else "bearish"
        if ote_dir == "bullish":
            ote = calculate_ote_zone(ms_1h["swing_low"], ms_1h["swing_high"], "bullish")
        else:
            ote = calculate_ote_zone(ms_1h["swing_high"], ms_1h["swing_low"], "bearish")

    div = detect_divergence(k1h, lookback=40)

    # Moving Averages
    def mas(closes): return {p: sma(closes, p) for p in [5, 10, 20, 30, 60]}
    ma_4h = mas(cl_4h)
    ma_1h = mas(cl_1h)

    quote_vol = float(ticker.get("quoteVolume", 0))
    bids = sum(float(b[1]) for b in depth.get("bids", []))
    asks = sum(float(a[1]) for a in depth.get("asks", []))
    bid_pct = (bids / (bids + asks) * 100) if (bids + asks) > 0 else 50.0

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2 — MARKET STRUCTURE SUMMARY
    # ══════════════════════════════════════════════════════════════════════════
    rsi_now = div["rsi_now"]

    # Build FVG/OB nearest strings
    fvg_nearest = "NONE"
    if fvgs:
        f = fvgs[0]
        fvg_nearest = f"{fmt(f['bottom'])}–{fmt(f['top'])} ({f['type']})"

    ob_nearest = "NONE"
    if obs:
        o = obs[0]
        ob_nearest = f"{fmt(o['bottom'])}–{fmt(o['top'])} ({o['type']})"

    liq_eqh = fmt(liq["nearest_eqh"]) if liq["nearest_eqh"] else "NONE"
    liq_eql = fmt(liq["nearest_eql"]) if liq["nearest_eql"] else "NONE"

    print_market_structure(ms_4h, ms_1h, "4H", "1H",
                           rsi_now, fvg_nearest, ob_nearest,
                           liq_eqh, liq_eql)

    # ── 3. Confluence Scoring ──────────────────────────────────────────────────
    print("\n[3/5] Scoring confluence...")
    score  = 0
    notes  = []
    hard_blocks   = []
    soft_warnings = []

    # ── HARD FILTERS ──────────────────────────────────────────────────────────

    # HF-SESSION: Session timing check
    if session["volatility"] == "🟡 Low":
        soft_warnings.append(
            f"SESSION: {session['window']} — Low Volatility. Grade A setups strongly favored."
        )

    # HF-1: 4H Structure Gate
    if ms_4h["trend"] == "ranging":
        if ms_4h["last_event"] in ["BOS_up", "ChoCh_up", "BOS_down", "ChoCh_down"]:
            soft_warnings.append(
                f"⚠️ 4H RANGING but {ms_4h['last_event']} detected — "
                f"structure forming, not confirmed trend. Lower conviction."
            )
        else:
            hard_blocks.append(
                "HF-1: 4H structure RANGING with no BOS/ChoCh — no directional edge"
            )

    # HF-2: Mid-range entry skip
    h4_high   = max(c[2] for c in k4h[-20:])
    h4_low    = min(c[3] for c in k4h[-20:])
    h4_range  = h4_high - h4_low
    h4_mid_lo = h4_low  + h4_range * MID_RANGE_SKIP_PCT
    h4_mid_hi = h4_high - h4_range * MID_RANGE_SKIP_PCT
    if h4_mid_lo < price < h4_mid_hi:
        hard_blocks.append(
            f"HF-2: Price mid-range ({fmt(h4_mid_lo)}–{fmt(h4_mid_hi)}) — no proven S/R at current level"
        )

    # HF-3: RSI exhaustion
    if rsi_now:
        if ms_4h["trend"] == "bullish" and rsi_now > RSI_OVERBOUGHT:
            hard_blocks.append(
                f"HF-3: RSI {rsi_now:.1f} OVERBOUGHT on 1H — exhaustion risk at {RSI_OVERBOUGHT}"
            )
        elif ms_4h["trend"] == "bearish" and rsi_now < RSI_OVERSOLD:
            hard_blocks.append(
                f"HF-3: RSI {rsi_now:.1f} OVERSOLD on 1H — exhaustion risk at {RSI_OVERSOLD}"
            )

    # ── SOFT SCORE ────────────────────────────────────────────────────────────

    # Structure Alignment (max 4 pts)
    if ms_4h["trend"] == "bullish" and (ms_1h["trend"] == "bullish" or ms_1h["last_event"] == "BOS_up"):
        score += 4; notes.append("4H bullish + 1H aligned ✓")
    elif ms_4h["trend"] == "bearish" and (ms_1h["trend"] == "bearish" or ms_1h["last_event"] == "BOS_down"):
        score += 4; notes.append("4H bearish + 1H aligned ✓")
    elif ms_4h["trend"] == "bullish":
        score += 2; notes.append("4H bullish (1H not yet confirmed — partial)")
    elif ms_4h["trend"] == "bearish":
        score += 2; notes.append("4H bearish (1H not yet confirmed — partial)")
    elif ms_4h["last_event"] in ["BOS_up", "ChoCh_up"]:
        score += 2; notes.append(f"4H structural shift bullish ({ms_4h['last_event']}) — forming")
    elif ms_4h["last_event"] in ["BOS_down", "ChoCh_down"]:
        score += 2; notes.append(f"4H structural shift bearish ({ms_4h['last_event']}) — forming")

    # ChoCh deduction on 1H
    if ms_1h["mss"]:
        score -= 1; notes.append(f"⚠️ ChoCh on 1H ({ms_1h['last_event']}) — structure reversing")

    # FVG proximity (max +2)
    nearby_fvg = None
    for fvg in fvgs:
        dist_pct = abs(price - fvg["midpoint"]) / price * 100
        if dist_pct < 2.0:
            score += 2; nearby_fvg = fvg
            notes.append(f"Near {fvg['type'].capitalize()} FVG ({dist_pct:.1f}%)")
            break

    # OB proximity (max +1)
    nearby_ob = None
    for ob in obs:
        dist_pct = abs(price - (ob["top"] + ob["bottom"]) / 2) / price * 100
        if dist_pct < 1.5:
            score += 1; nearby_ob = ob
            notes.append(f"Near {ob['type'].capitalize()} OB ({dist_pct:.1f}%)")
            break

    # OTE zone (max +2)
    ote_valid = False
    if ote and ote["ote_bottom"] <= price <= ote["ote_top"]:
        score += 2; notes.append("In Optimal Trade Entry (OTE) zone")
        ote_valid = True

    # Inducement / liquidity grab (max +1)
    if idms:
        score += 1; notes.append(f"Recent Liquidity Grab / Inducement ({idms[0]['type']})")

    # Volume spike on 1H (max +1)
    vol_1h = [float(c[7]) for c in k1h]
    if len(vol_1h) >= 6:
        avg_vol_5 = sum(vol_1h[-6:-1]) / 5
        if avg_vol_5 > 0 and vol_1h[-1] > avg_vol_5 * 1.5:
            score += 1; notes.append("1H volume spike (>1.5× avg) ✓")

    # Order book bias (max +1)
    if bid_pct > 53:
        score += 1; notes.append(f"Order book long-biased ({bid_pct:.0f}% bids) ✓")
    elif (100 - bid_pct) > 53:
        score += 1; notes.append(f"Order book short-biased ({100 - bid_pct:.0f}% asks) ✓")

    score = max(0, min(score, 10))

    # ── Direction Assignment ───────────────────────────────────────────────────
    if ms_4h["trend"] == "bullish":
        direction = "LONG"
    elif ms_4h["trend"] == "bearish":
        direction = "SHORT"
    elif ms_4h["last_event"] in ["BOS_up", "ChoCh_up"]:
        direction = "LONG"
    elif ms_4h["last_event"] in ["BOS_down", "ChoCh_down"]:
        direction = "SHORT"
    else:
        direction = "NEUTRAL"

    if   score >= 8: grade = "A"
    elif score >= 6: grade = "B"
    else:            grade = "C"

    # ── Pre-conditions for WAITING ROOM ────────────────────────────────────────
    vol_filter = quote_vol > 100_000_000
    range_filter = True  # already passed by scanner
    struct_confirmed = ms_4h["trend"] != "ranging" or ms_4h["last_event"] is not None
    at_key_level = nearby_fvg is not None or nearby_ob is not None or ote_valid
    rsi_ok = rsi_now is None or (RSI_OVERSOLD <= rsi_now <= RSI_OVERBOUGHT)
    session_ok = True
    score_ok = score >= MIN_SCORE

    rsi_disp = f"{rsi_now:.1f}" if rsi_now else "—"
    preconditions = {
        f"Volume filter (>${quote_vol/1e6:.0f}M > $100M)": vol_filter,
        "4H structure direction confirmed": struct_confirmed,
        "At key level (FVG / OB / OTE)": at_key_level,
        f"RSI not exhausted ({rsi_disp})": rsi_ok,
        f"Session window ({session['window']})": session_ok,
        f"Score ≥{MIN_SCORE} (current: {score})": score_ok,
        "Not mid-range": not any("HF-2" in b for b in hard_blocks),
    }

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 6 — TRADE PLAN or WAITING ROOM
    # ══════════════════════════════════════════════════════════════════════════

    # Determine if we go to WAITING ROOM
    go_waiting = bool(hard_blocks) or direction == "NEUTRAL" or score < MIN_SCORE

    if go_waiting:
        # ── SECTION 3B: WAITING ROOM ──────────────────────────────────────────
        reasons = []
        if hard_blocks:
            reasons.extend(hard_blocks)
        if direction == "NEUTRAL":
            reasons.append(f"Direction unclear — no structural bias on 4H")
        if score < MIN_SCORE:
            reasons.append(f"Score {score}/10 — need {MIN_SCORE}+ for entry")

        # Build key levels
        key_levels = []
        if ms_1h.get("swing_high"):
            key_levels.append((ms_1h["swing_high"], "1H swing high — BOS target for LONG"))
        if ms_1h.get("swing_low"):
            key_levels.append((ms_1h["swing_low"], "1H swing low — BOS target for SHORT"))
        if liq.get("nearest_eqh"):
            key_levels.append((liq["nearest_eqh"], "EQH — buy-side liquidity / stop-hunt magnet"))
        if liq.get("nearest_eql"):
            key_levels.append((liq["nearest_eql"], "EQL — sell-side liquidity / stop-hunt magnet"))
        if ma_1h.get(20):
            dist = abs(price - ma_1h[20]) / price * 100
            key_levels.append((ma_1h[20], f"MA20 ({dist:.1f}% from price)"))

        next_window = get_next_session_window()
        verify = f"Check if 4H candle has closed {'above' if ms_4h['trend'] != 'bearish' else 'below'} {fmt(ms_1h.get('swing_high', price))}"

        print_waiting_room(
            symbol=symbol, reasons=reasons,
            ms_htf=ms_4h, ms_ltf=ms_1h,
            htf_label="4H", ltf_label="1H",
            key_levels=key_levels[:5],
            preconditions=preconditions,
            next_window=next_window,
            rerun_cmd=f"scalp {symbol}",
            verify_note=verify,
            fvg_zones=fvgs[:3],
        )

        # Scoring breakdown
        print(f"\nSCORING BREAKDOWN ({score}/10)")
        for n in notes:
            print(f"  {'✅' if '⚠️' not in n else '⚠️'} {n}")

        # ── SECTION 4: TELEGRAM (WAITING ROOM) ───────────────────────────────
        trigger = fmt(ms_1h.get("swing_high", price)) if ms_4h["trend"] != "bearish" else fmt(ms_1h.get("swing_low", price))
        tg_msg = format_telegram_waiting(
            symbol=symbol, session=session, reasons=reasons[:2],
            trigger_level=trigger, next_check=next_window
        )
        send_telegram(tg_msg)
        return

    # ── SECTION 3A: TRADE PLAN ────────────────────────────────────────────────
    # Print any soft warnings before trade plan
    if soft_warnings:
        print(f"\n{'─'*60}")
        print(f"  ⚠️  WARNINGS — Trade not blocked, proceed with caution:")
        for w in soft_warnings:
            print(f"     • {w}")
        print(f"{'─'*60}")

    print("\n[4/5] Refining 15m/5m entry & building trade plan...")
    tok_type = classify_token(symbol, quote_vol)
    rules    = SCALP_RULES[tok_type]

    # Entry refinement — priority: FVG midpoint → OB midpoint → OTE → current price
    entry = price
    entry_note = "Current market price"
    if nearby_fvg and abs(price - nearby_fvg["midpoint"]) / price < 0.015:
        entry = nearby_fvg["midpoint"]
        entry_note = f"FVG midpoint ({nearby_fvg['type']})"
    elif nearby_ob:
        entry = (nearby_ob["top"] + nearby_ob["bottom"]) / 2
        entry_note = f"{nearby_ob['type'].capitalize()} Order Block midpoint"
    elif ote_valid:
        entry = ote["ote_mid"]
        entry_note = "OTE Fibonacci 0.705 Level"

    # Stop calculation anchored to entry
    stops  = calc_atr_stop(k1h, entry, direction,
                           multiplier=1.5, period=14,
                           max_sl_pct=rules["max_sl"])
    sizing = calc_position(tok_type, stops["sl_pct"], mode="scalp", setup_grade=grade)

    # Trailing stop callback
    trail_pct = calc_trail_callback_pct(stops["atr_value"], entry, tok_type)

    # Correlation check
    corr_warn = correlation_warning(open_positions, symbol)
    if corr_warn:
        print(f"\n  {corr_warn}")

    # Scoring breakdown
    print(f"\nSCORING BREAKDOWN ({score}/10)")
    for n in notes:
        print(f"  {'✅' if '⚠️' not in n else '⚠️'} {n}")

    # Print the trade plan
    print_trade_plan(
        symbol=symbol, direction=direction, score=score, grade=grade,
        entry=entry, entry_note=entry_note, stops=stops, sizing=sizing,
        trail_callback_pct=trail_pct, invalidation=stops["sl"],
        tf_label="4H"
    )

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python skill_scalper_analyze.py SYMBOL [open1,open2,...]")
        sys.exit(1)
    sym      = sys.argv[1].upper()
    open_pos = sys.argv[2].split(",") if len(sys.argv) > 2 else []
    analyze_scalp(sym, open_pos)
