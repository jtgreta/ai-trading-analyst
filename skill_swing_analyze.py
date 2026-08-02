"""
skill_swing_analyze.py — Institutional Edition (prompt.txt v3)
Usage: python skill_swing_analyze.py SYMBOL [open1,open2,...]

Output Format (4 mandatory sections per prompt.txt):
  Section 1: SESSION CHECK — current PHT window + quality
  Section 2: MARKET STRUCTURE SUMMARY — full SMC context (1W/1D)
  Section 3A: TRADE PLAN — when score ≥6 and hard filters pass
  Section 3B: WAITING ROOM — when no trade fires (replaces dead-end BLOCKED)
  Section 4: TELEGRAM SUMMARY — always sent

Hard Rules (never violated):
  - SL always set before entry
  - Min RR 1:2 (TP1 ≥ 2× SL distance)
  - Max risk $3-$4
  - Score <6 = WAITING ROOM
  - WAITING ROOM always fires when no valid trade
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from trading_utils import (
    fetch_klines, fetch_ticker, send_telegram,
    classify_token, calc_position,
    sma, ema,
    detect_bos_choch, find_fvg, detect_order_blocks,
    detect_liquidity, detect_divergence, identify_inducement,
    format_telegram_trade, format_telegram_waiting,
    print_session_check, print_market_structure, print_trade_plan, print_waiting_room,
    get_session_info, get_next_session_window,
    fmt, grade_label, SWING_RULES, correlation_warning, MIN_RR
)

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ── Hard Filter Thresholds ─────────────────────────────────────────────────────
MIN_SCORE = 6

def calc_atr_stop_swing(klines: list, entry_price: float, direction: str, 
                  multiplier: float = 2.0, period: int = 14,
                  max_sl_pct: float = 0.05) -> dict:
    """ATR calculation for swing trades (wider multiplier)."""
    if not klines or len(klines) < period * 2:
        sl = entry_price * (1 - max_sl_pct) if direction == "LONG" else entry_price * (1 + max_sl_pct)
        dist = abs(entry_price - sl)
        return {
            "atr_value": None,
            "sl": round(sl, 4),
            "sl_pct": max_sl_pct,
            "tp1": round(entry_price + (dist * 2.0) if direction == "LONG" else entry_price - (dist * 2.0), 4),
            "tp2": round(entry_price + (dist * 3.5) if direction == "LONG" else entry_price - (dist * 3.5), 4),
            "tp3": "Trailing"
        }

    tr_list = []
    for i in range(1, len(klines)):
        h = float(klines[i][2])
        l = float(klines[i][3])
        pc = float(klines[i-1][4])
        tr = max(h - l, abs(h - pc), abs(l - pc))
        tr_list.append(tr)

    atr = sum(tr_list[-period:]) / period
    atr_dist = atr * multiplier
    max_dist = entry_price * max_sl_pct
    
    sl_dist = min(atr_dist, max_dist)
    
    sl = entry_price - sl_dist if direction == "LONG" else entry_price + sl_dist
    actual_sl_pct = sl_dist / entry_price
    
    return {
        "atr_value": atr,
        "sl": round(sl, 4),
        "sl_pct": actual_sl_pct,
        "tp1": round(entry_price + (sl_dist * 2.0) if direction == "LONG" else entry_price - (sl_dist * 2.0), 4),
        "tp2": round(entry_price + (sl_dist * 3.5) if direction == "LONG" else entry_price - (sl_dist * 3.5), 4),
        "tp3": "Trailing"
    }


def analyze_swing(symbol: str, open_positions: list = None):
    if open_positions is None:
        open_positions = []

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1 — SESSION CHECK
    # ══════════════════════════════════════════════════════════════════════════
    session = get_session_info()

    print(f"\n{'═'*60}")
    print(f"  {symbol} — Institutional Swing Analysis")
    print(f"{'═'*60}")

    # For swing trades, Asian session is fine for management, but still flag it
    print_session_check(session)

    print("\n[1/5] Fetching daily/weekly market data...")
    k4h = fetch_klines(symbol, "4h", 150)
    k1d = fetch_klines(symbol, "1d", 250)
    k1w = fetch_klines(symbol, "1w", 52)
    ticker = fetch_ticker(symbol)

    if not k1d or not k1w or not ticker:
        print(f"  ✗ Insufficient data for {symbol}.")
        return

    cl_1d = [c[4] for c in k1d]
    price = cl_1d[-1]
    quote_vol = float(ticker.get("quoteVolume", 0))

    print("[2/5] Running Multi-Timeframe SMC engine...")
    ms_1w = detect_bos_choch(k1w, lookback=20)
    ms_1d = detect_bos_choch(k1d, lookback=40)
    ms_4h = detect_bos_choch(k4h, lookback=40)

    fvgs_1d = find_fvg(k1d, lookback=20)
    obs_4h  = detect_order_blocks(k4h, lookback=40)
    liq_1d  = detect_liquidity(k1d, lookback=40)
    div_1d  = detect_divergence(k1d, lookback=40)

    def mas(closes): return {p: sma(closes, p) for p in [20, 50, 100, 200]}
    ma_1d = mas(cl_1d)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2 — MARKET STRUCTURE SUMMARY
    # ══════════════════════════════════════════════════════════════════════════
    rsi_now = div_1d["rsi_now"]

    fvg_nearest = "NONE"
    if fvgs_1d:
        f = fvgs_1d[0]
        fvg_nearest = f"{fmt(f['bottom'])}–{fmt(f['top'])} ({f['type']})"

    ob_nearest = "NONE"
    if obs_4h:
        o = obs_4h[0]
        ob_nearest = f"{fmt(o['bottom'])}–{fmt(o['top'])} ({o['type']}) on 4H"

    liq_eqh = fmt(liq_1d["nearest_eqh"]) if liq_1d["nearest_eqh"] else "NONE"
    liq_eql = fmt(liq_1d["nearest_eql"]) if liq_1d["nearest_eql"] else "NONE"

    print_market_structure(ms_1w, ms_1d, "1W Macro", "1D",
                           rsi_now, fvg_nearest, ob_nearest,
                           liq_eqh, liq_eql)

    print("\n[3/5] Scoring swing confluence...")
    score = 0
    notes = []
    hard_blocks = []

    # ── HF-1: Macro Trend Gate ────────────────────────────────────────────────
    if ms_1w["trend"] == "ranging":
        hard_blocks.append("HF-1: 1W macro trend is RANGING — swing trades require macro tailwind")

    # ── Direction Assignment ──────────────────────────────────────────────────
    direction = "NEUTRAL"
    if ms_1w["trend"] == "bullish":
        direction = "LONG"
    elif ms_1w["trend"] == "bearish":
        direction = "SHORT"

    # ── HF-2: Key Level Gate ──────────────────────────────────────────────────
    at_key_level = False
    nearby_fvg = None
    if fvgs_1d:
        dist_pct = abs(price - fvgs_1d[0]["midpoint"]) / price * 100
        if dist_pct < 3.0:
            at_key_level = True
            nearby_fvg = fvgs_1d[0]
            notes.append(f"At 1D FVG ({dist_pct:.1f}% away)")
            score += 2

    # MA Fallbacks for key level
    nearby_ma = None
    if not at_key_level:
        if ma_1d[50] and abs(price - ma_1d[50])/price * 100 < 4.0:
            at_key_level = True; nearby_ma = "MA50"; score += 1
            notes.append("At 1D MA50")
        elif ma_1d[20] and abs(price - ma_1d[20])/price * 100 < 4.0:
            at_key_level = True; nearby_ma = "MA20"
        elif ma_1d[200] and abs(price - ma_1d[200])/price * 100 < 5.0:
            at_key_level = True; nearby_ma = "MA200"

    if not at_key_level:
        hard_blocks.append("HF-2: Price not at a key daily entry level (FVG or MA). Wait for pullback.")

    # ── Soft Scoring ──────────────────────────────────────────────────────────
    
    # 1W alignment (+2)
    if ma_1d[20] and ((direction == "LONG" and price > ma_1d[20]) or (direction == "SHORT" and price < ma_1d[20])):
        score += 2; notes.append("1W Macro trend alignment ✓")

    # 1D structure (+2)
    if ms_1d["last_event"] == ("BOS_up" if direction == "LONG" else "BOS_down"):
        score += 2; notes.append("1D BOS aligns with trade direction ✓")
    elif ms_1d["last_event"] == ("ChoCh_up" if direction == "LONG" else "ChoCh_down"):
        score += 2; notes.append("1D structural shift (ChoCh) aligns with trade direction ✓")
    elif ms_1d["last_event"] == ("ChoCh_down" if direction == "LONG" else "ChoCh_up"):
        score -= 1; notes.append("⚠️ 1D ChoCh AGAINST trade direction — reversal risk")

    # 4H structure/reversal (+2)
    if ms_4h["trend"] == ("bullish" if direction == "LONG" else "bearish"):
        score += 2; notes.append("4H structure aligned (Pullback ending) ✓")
    elif ms_4h["last_event"] == ("ChoCh_up" if direction == "LONG" else "ChoCh_down"):
        score += 2; notes.append("4H structural shift confirms reversal ✓")

    # Volume & Divergence
    vol_1d = [float(c[7]) for c in k1d]
    if len(vol_1d) >= 21:
        avg_vol_20 = sum(vol_1d[-21:-1]) / 20
        if vol_1d[-1] > avg_vol_20:
            score += 1; notes.append("Daily volume > 20D average ✓")

    if div_1d["type"] == ("bullish" if direction == "LONG" else "bearish"):
        score += 1; notes.append(f"1D {div_1d['type']} RSI divergence ✓")

    score = max(0, min(score, 10))

    if   score >= 8: grade = "A"
    elif score >= 6: grade = "B"
    else:            grade = "C"

    # ── Pre-conditions for WAITING ROOM ────────────────────────────────────────
    preconditions = {
        "1W Macro Direction defined": ms_1w["trend"] != "ranging",
        "Price at key 1D Level (FVG or MA)": at_key_level,
        "1D structural alignment": ms_1d["trend"] == ("bullish" if direction == "LONG" else "bearish"),
        "4H reversal confirmed": ms_4h["trend"] == ("bullish" if direction == "LONG" else "bearish") or ms_4h["last_event"] is not None,
        f"Score ≥{MIN_SCORE} (current: {score})": score >= MIN_SCORE
    }

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3 — TRADE PLAN or WAITING ROOM
    # ══════════════════════════════════════════════════════════════════════════

    go_waiting = bool(hard_blocks) or direction == "NEUTRAL" or score < MIN_SCORE

    if go_waiting:
        # ── SECTION 3B: WAITING ROOM ──────────────────────────────────────────
        reasons = []
        if hard_blocks:
            reasons.extend(hard_blocks)
        if direction == "NEUTRAL":
            reasons.append("Direction unclear — 1W macro trend is ranging")
        if score < MIN_SCORE:
            reasons.append(f"Score {score}/10 — need {MIN_SCORE}+ for entry")

        key_levels = []
        if fvgs_1d:
            f = fvgs_1d[0]
            key_levels.append((f["midpoint"], f"1D {f['type'].capitalize()} FVG — Primary institutional target"))
        if ma_1d.get(50):
            key_levels.append((ma_1d[50], "1D MA50 — Classic swing support/resistance"))
        if ms_1d.get("swing_high"):
            key_levels.append((ms_1d["swing_high"], "1D Swing High"))
        if ms_1d.get("swing_low"):
            key_levels.append((ms_1d["swing_low"], "1D Swing Low"))

        verify = f"Check if 1D candle closes {'above' if ms_1w['trend'] != 'bearish' else 'below'} {fmt(ms_1d.get('swing_high', price))}"

        print_waiting_room(
            symbol=symbol, reasons=reasons,
            ms_htf=ms_1w, ms_ltf=ms_1d,
            htf_label="1W", ltf_label="1D",
            key_levels=key_levels[:4],
            preconditions=preconditions,
            next_window="Check daily at 8:00 AM PHT (daily close)",
            rerun_cmd=f"swing {symbol}",
            verify_note=verify,
            fvg_zones=fvgs_1d[:2],
        )

        print(f"\nSCORING BREAKDOWN ({score}/10)")
        for n in notes:
            print(f"  {'✅' if '⚠️' not in n else '⚠️'} {n}")

        # ── SECTION 4: TELEGRAM (WAITING ROOM) ───────────────────────────────
        tg_msg = format_telegram_waiting(
            symbol=symbol, session=session, reasons=reasons[:2],
            trigger_level="1D FVG or MA50 pullback", next_check="Daily close (8 AM PHT)"
        )
        send_telegram(tg_msg)
        return

    # ── SECTION 3A: TRADE PLAN ────────────────────────────────────────────────
    print("\n[4/5] Building Swing Trade Plan...")
    tok_type = classify_token(symbol, quote_vol)
    rules    = SWING_RULES[tok_type]

    # Entry refinement
    entry = price
    entry_note = "Current market price"
    if nearby_fvg:
        entry = nearby_fvg["midpoint"]
        entry_note = f"1D FVG midpoint ({nearby_fvg['type']})"
    elif nearby_ma:
        entry = ma_1d[int(nearby_ma.replace("MA", ""))]
        entry_note = f"1D {nearby_ma}"

    # Use 4H ATR for swing stops
    stops = calc_atr_stop_swing(k4h, entry, direction, 
                          multiplier=2.0, period=14, 
                          max_sl_pct=rules["max_sl"])
                          
    sizing = calc_position(tok_type, stops["sl_pct"], mode="swing", setup_grade=grade)

    corr_warn = correlation_warning(open_positions, symbol)
    if corr_warn:
        print(f"\n  {corr_warn}")

    print(f"\nSCORING BREAKDOWN ({score}/10)")
    for n in notes:
        print(f"  {'✅' if '⚠️' not in n else '⚠️'} {n}")

    # Print the trade plan
    print_trade_plan(
        symbol=symbol, direction=direction, score=score, grade=grade,
        entry=entry, entry_note=entry_note, stops=stops, sizing=sizing,
        trail_callback_pct=5.0, invalidation=stops["sl"],
        tf_label="1D"
    )
    
    print("\nManagement: Swing trades take 2-14 days. Check morning and evening only.")

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 4 — TELEGRAM SUMMARY
    # ══════════════════════════════════════════════════════════════════════════
    print("\n[5/5] Sending Telegram...")
    struct = {
        "tf_4h": f"1W {ms_1w['trend'].capitalize()}",
        "tf_1h": f"1D {ms_1d['trend'].capitalize()}",
        "event": ms_1d["last_event"] or "None"
    }
    zones = {"entry": entry, "fvg": None, "ob": None}
    if nearby_fvg: zones["fvg"] = f"{fmt(nearby_fvg['bottom'])} – {fmt(nearby_fvg['top'])} ({nearby_fvg['type'].capitalize()})"

    risk_data = {
        "sl": stops["sl"], "sl_pct": stops["sl_pct"] * 100,
        "tp1": stops["tp1"], "tp2": stops["tp2"], "tp3": stops["tp3"],
        "risk_usd": sizing["risk"], "margin": sizing["margin"], "lev": sizing["lev"]
    }

    tg_msg = format_telegram_trade(
        symbol=symbol, direction=direction, grade=grade,
        session=session, structure=struct, zones=zones,
        risk=risk_data, invalidation=stops["sl"]
    )
    send_telegram(tg_msg)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python skill_swing_analyze.py SYMBOL [open1,open2,...]")
        sys.exit(1)
    sym = sys.argv[1].upper()
    open_pos = sys.argv[2].split(",") if len(sys.argv) > 2 else []
    analyze_swing(sym, open_pos)
