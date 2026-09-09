"""
hunter_coil.py — Institutional Edition
Coil Scorer + Trade Plan Generator for individual symbols.

Usage:
  python hunter_coil.py SYMBOL [SYMBOL2 SYMBOL3 ...]
  python hunter_coil.py SOLUSDT ETHUSDT PEPEUSDT

Purpose:
  Analyze one or more specific symbols against the Hunter coil criteria.
  Use this when you already know which coins you want to check.
  For a full market-wide scan, use hunter_scan.py instead.

Coil Score Components (0–10, per Hunter SKILL.md):
  A. Range Contraction on 15M     — max 3 pts
  B. Volume Building on 15M       — max 2 pts
  C. Market Structure (1H + 4H)   — max 2 pts (SMC BOS/ChoCh, MA fallback)
  D. ChoCh Bonus on 1H            — max 1 pt  (structural breakout building)
  E. FVG Proximity on 1H          — max 1 pt  (imbalance magnet)
  F. Relative Volume vs 24H avg   — max 1 pt
  BONUS: Inducement + OB Conf.    — +3 pts    (liquidity grab at OB = institutional)
  RSI Deduction                   — -1 pt     (overbought long / oversold short)

Score thresholds:
  8–10 : 🔥 PRIME SETUP  — Grade A, full margin
  6–7  : ✅ GOOD SETUP   — Grade B, half margin
  4–5  : 👀 WATCH ONLY   — re-scan in 30 min
  0–3  : ❌ SKIP

Output Sections:
  1. Session Check
  2. Market Structure Summary (per coin)
  3A. Trade Plan (score ≥ 6)  OR  3B. Watch / Skip notice
  4. Telegram Summary
"""

import sys
import os

from datetime import datetime

from trading_utils import (
    fetch_klines, fetch_ticker,
    sma, atr, rsi,
    detect_bos_choch, find_fvg, detect_order_blocks, detect_liquidity,
    identify_inducement,
    classify_token, calc_position,
    SCALP_RULES, EXCLUDE_SUBS, EXCLUDE_EXACT,
    send_telegram, fmt, get_session_info, print_session_check
)

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

CAPITAL = 100.0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COIL SCORING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def score_coil(symbol: str, k15: list, k1h: list, k4h: list,
               quote_vol: float, price: float) -> dict:
    """
    Score a single coin on the full Hunter coil criteria.
    k15 / k1h / k4h must be pre-fetched and validated before calling.
    Returns a score dict with every computed component.
    """
    score     = 0
    direction = "SKIP"
    notes     = []

    # Exclude the forming (unclosed) candle from 15M analysis
    closed_15 = k15[:-1]

    # ── A. Range Contraction on 15M (max 3 pts) ──────────────────────────────
    comp_a = 0
    if len(closed_15) >= 8:
        last4_r = [c[2] - c[3] for c in closed_15[-4:]]
        prev4_r = [c[2] - c[3] for c in closed_15[-8:-4]]
        avg_last = sum(last4_r) / 4 if last4_r else 0
        avg_prev = sum(prev4_r) / 4 if prev4_r else 0
        if avg_prev > 0:
            ratio = avg_last / avg_prev
            if ratio < 0.50:
                comp_a = 3
                notes.append(f"A: Tight squeeze ({ratio:.2f}x range)")
            elif ratio < 0.65:
                comp_a = 2
                notes.append(f"A: Moderate compression ({ratio:.2f}x range)")
            elif ratio < 0.80:
                comp_a = 1
                notes.append(f"A: Mild compression ({ratio:.2f}x range)")
            else:
                notes.append(f"A: No compression ({ratio:.2f}x range) → 0 pts")
    score += comp_a

    # ── B. Volume Building on 15M (max 2 pts) ─────────────────────────────────
    comp_b = 0
    if len(closed_15) >= 8:
        last4_v = sum(c[5] for c in closed_15[-4:]) / 4
        prev4_v = sum(c[5] for c in closed_15[-8:-4]) / 4
        if prev4_v > 0:
            vr = last4_v / prev4_v
            if vr > 1.4:
                comp_b = 2
                notes.append(f"B: Volume building ({vr:.2f}x avg)")
            elif vr > 1.1:
                comp_b = 1
                notes.append(f"B: Volume slightly up ({vr:.2f}x avg)")
            else:
                notes.append(f"B: Volume flat ({vr:.2f}x avg) → 0 pts")
    score += comp_b

    # ── C. Market Structure on 1H + 4H (max 2 pts) ───────────────────────────
    ms_1h = detect_bos_choch(k1h, lookback=30)
    ms_4h = detect_bos_choch(k4h, lookback=30)
    comp_c = 0

    if ms_4h["trend"] == "bullish" and ms_1h["trend"] in ("bullish", "ranging"):
        comp_c = 2; direction = "LONG"
        notes.append("C: 4H bullish + 1H aligned/ranging")
    elif ms_4h["trend"] == "bearish" and ms_1h["trend"] in ("bearish", "ranging"):
        comp_c = 2; direction = "SHORT"
        notes.append("C: 4H bearish + 1H aligned/ranging")
    elif ms_4h["trend"] == "bullish":
        comp_c = 1; direction = "LONG"
        notes.append("C: 4H bullish (1H conflicting — weaker signal)")
    elif ms_4h["trend"] == "bearish":
        comp_c = 1; direction = "SHORT"
        notes.append("C: 4H bearish (1H conflicting — weaker signal)")
    else:
        # MA fallback when 4H is ranging
        cl_1h = [c[4] for c in k1h]
        cl_4h = [c[4] for c in k4h]
        ma10_1h = sma(cl_1h, 10); ma20_1h = sma(cl_1h, 20)
        ma10_4h = sma(cl_4h, 10); ma20_4h = sma(cl_4h, 20)
        if ma10_1h and ma20_1h and price > ma10_1h > ma20_1h:
            comp_c = 1; direction = "LONG"
            notes.append("C: MA lean bullish (4H ranging, weaker)")
        elif ma10_1h and ma20_1h and price < ma10_1h < ma20_1h:
            comp_c = 1; direction = "SHORT"
            notes.append("C: MA lean bearish (4H ranging, weaker)")
        else:
            notes.append("C: Structure ranging, no MA lean → 0 pts (SKIP direction)")
    score += comp_c

    # ── D. ChoCh Bonus on 1H (+1 pt) ─────────────────────────────────────────
    comp_d = 0
    if ms_1h["mss"]:
        comp_d = 1
        notes.append(f"D: ChoCh on 1H ({ms_1h['last_event']}) — structural shift, institutional hand revealed")
    score += comp_d

    # ── E. FVG Proximity on 1H (+1 pt) ───────────────────────────────────────
    fvgs = find_fvg(k1h, lookback=25)
    nearby_fvg = None
    comp_e = 0
    for fvg in fvgs:
        dist_pct = abs(price - fvg["midpoint"]) / price * 100
        if dist_pct < 1.5:
            comp_e = 1
            nearby_fvg = fvg
            notes.append(f"E: In {fvg['type']} FVG ({fmt(fvg['bottom'])}–{fmt(fvg['top'])}, {dist_pct:.1f}% away)")
            break
    if not nearby_fvg:
        notes.append("E: No unfilled FVG within 1.5% → 0 pts")
    score += comp_e

    # ── Order Blocks (used for inducement check + plan) ───────────────────────
    obs = detect_order_blocks(k1h, lookback=30)
    nearby_ob = None
    for ob in obs:
        mid = (ob["top"] + ob["bottom"]) / 2
        if abs(price - mid) / price < 0.015:
            nearby_ob = ob
            break

    # ── BONUS: Inducement + OB Confluence (+3 pts) ────────────────────────────
    idms = identify_inducement(k1h, ms_1h["swing_highs"], ms_1h["swing_lows"],
                               ms_1h["trend"], lookback=30)
    idm_flag = ""
    comp_idm = 0
    if idms and nearby_ob:
        comp_idm = 3
        idm_flag = "🪤 Liquidity Grab + OB Confluence"
        notes.append(f"BONUS: {idm_flag}")
    elif idms:
        comp_idm = 1
        idm_flag = "🪤 Liquidity Grab (no nearby OB)"
        notes.append(f"BONUS: {idm_flag}")
    score += comp_idm

    # ── F. Relative Volume vs 24H Baseline (+1 pt) ────────────────────────────
    avg_hourly = quote_vol / 24 if quote_vol > 0 else 1
    try:
        last_1h_qvol = float(k1h[-2][7])
    except Exception:
        last_1h_qvol = float(k1h[-2][5]) * float(k1h[-2][4])
    rel_vol = last_1h_qvol / avg_hourly if avg_hourly > 0 else 0
    comp_f = 0
    if rel_vol > 1.5:
        comp_f = 1
        notes.append(f"F: Relative volume {rel_vol:.2f}x avg (above baseline)")
    else:
        notes.append(f"F: Relative volume {rel_vol:.2f}x avg → 0 pts")
    score += comp_f

    # ── RSI Deduction (-1 pt if exhausted) ────────────────────────────────────
    cl_1h_closes = [c[4] for c in k1h]
    rsi_val  = rsi(cl_1h_closes, 14)
    rsi_flag = ""
    comp_rsi = 0
    if rsi_val:
        if direction == "LONG" and rsi_val > 75:
            comp_rsi = -1
            rsi_flag = f"⚠️ RSI {rsi_val:.0f} overbought — compression at exhaustion, fakeout risk"
            notes.append(rsi_flag)
        elif direction == "SHORT" and rsi_val < 25:
            comp_rsi = -1
            rsi_flag = f"⚠️ RSI {rsi_val:.0f} oversold — counter-trend compression, fakeout risk"
            notes.append(rsi_flag)
    score += comp_rsi
    score  = max(0, score)

    # ── ATR for trade plan ────────────────────────────────────────────────────
    atr_val = atr(k1h, 14)
    atr_pct = (atr_val / price * 100) if atr_val and price > 0 else 0

    return {
        "score":      score,
        "direction":  direction,
        "notes":      notes,
        "ms_4h":      ms_4h,
        "ms_1h":      ms_1h,
        "fvgs":       fvgs,
        "nearby_fvg": nearby_fvg,
        "nearby_ob":  nearby_ob,
        "idms":       idms,
        "idm_flag":   idm_flag,
        "rsi_val":    rsi_val,
        "rsi_flag":   rsi_flag,
        "atr_val":    atr_val,
        "atr_pct":    atr_pct,
        "rel_vol":    rel_vol,
        "closed_15":  closed_15,
        "liq":        detect_liquidity(k1h, lookback=30),
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TRADE PLAN BUILDER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def build_trade_plan(symbol: str, price: float, quote_vol: float,
                     k1h: list, direction: str, sig: dict) -> dict:
    """
    Build ATR-based trade plan from coil signal.
    Entry zone is anchored to the last 4 closed 15M candles.
    SL = ATR × 1.5 from entry midpoint, capped at token max_sl%.
    TP1 refined to FVG top if FVG is in breakout direction and RR ≥ 1.5.

    Args:
        k1h: raw 1H candle list — used directly for ATR calculation.
    """
    tok_type = classify_token(symbol, quote_vol)
    rules    = SCALP_RULES[tok_type]
    grade    = "A" if sig["score"] >= 8 else "B" if sig["score"] >= 6 else "C"

    # Entry zone: last 4 closed 15M candles
    c15        = sig["closed_15"]
    entry_low  = min(c[3] for c in c15[-4:])
    entry_high = max(c[2] for c in c15[-4:])
    entry_mid  = (entry_low + entry_high) / 2

    # ATR-based stop: use live k1h for proper calculation
    if sig["atr_val"]:
        atr_dist = sig["atr_val"] * 1.5
        sl_dist  = min(atr_dist, entry_mid * rules["max_sl"])
    else:
        # Fallback: half of max_sl% if no ATR data
        sl_dist = entry_mid * rules["max_sl"] * 0.5

    sl_pct = sl_dist / entry_mid

    if direction == "LONG":
        sl        = entry_mid - sl_dist
        tp1_price = entry_mid + sl_dist * 2.0
        tp2_price = entry_mid + sl_dist * 3.5
    else:
        sl        = entry_mid + sl_dist
        tp1_price = entry_mid - sl_dist * 2.0
        tp2_price = entry_mid - sl_dist * 3.5

    # Refine TP1: if a FVG boundary is in the breakout direction with ≥1.5 RR, use it
    if sig["nearby_fvg"]:
        fvg = sig["nearby_fvg"]
        if direction == "LONG" and fvg["top"] > entry_mid:
            rr_fvg = (fvg["top"] - entry_mid) / sl_dist
            if rr_fvg >= 1.5:
                tp1_price = fvg["top"]
        elif direction == "SHORT" and fvg["bottom"] < entry_mid:
            rr_fvg = (entry_mid - fvg["bottom"]) / sl_dist
            if rr_fvg >= 1.5:
                tp1_price = fvg["bottom"]

    sizing      = calc_position(tok_type, sl_pct, mode="scalp", setup_grade=grade)
    actual_risk = sizing["risk"]
    wide_stop   = sl_pct > rules["max_sl"] * 0.9

    type_labels = {
        "major":  "BTC/ETH/BNB",
        "midcap": "Mid-cap",
        "new":    "New/Meme/AI",
    }

    return {
        "entry_low":   round(entry_low, 8),
        "entry_high":  round(entry_high, 8),
        "entry_mid":   round(entry_mid, 8),
        "sl":          round(sl, 8),
        "sl_pct":      round(sl_pct * 100, 2),
        "sl_dist":     round(sl_dist, 8),
        "trail_dist":  round(sl_dist, 8),
        "tp1":         round(tp1_price, 8),
        "tp2":         round(tp2_price, 8),
        "token_type":  tok_type,
        "type_label":  type_labels[tok_type],
        "lev":         sizing["lev"],
        "margin":      sizing["margin"],
        "position":    sizing["position"],
        "actual_risk": actual_risk,
        "grade":       grade,
        "wide_stop":   wide_stop,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# OUTPUT PRINTERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def print_coil_analysis(symbol: str, price: float, quote_vol: float, sig: dict, k1h: list):
    """Full per-coin output — all 3 sections (session is printed once by main)."""
    score     = sig["score"]
    direction = sig["direction"]

    # 1. Market Structure Summary (Section 2)
    # Prepare arguments for print_market_structure
    ms_htf = sig["ms_4h"]
    ms_ltf = sig["ms_1h"]
    
    # Find nearest FVG/OB for the summary
    fvg_nearest = "NONE"
    if sig["fvgs"]:
        f = sig["fvgs"][0]
        fvg_nearest = f"{fmt(f['bottom'])}–{fmt(f['top'])} ({f['type']})"
    
    ob_nearest = "NONE"
    if sig["nearby_ob"]:
        o = sig["nearby_ob"]
        ob_nearest = f"{fmt(o['bottom'])}–{fmt(o['top'])} ({o['type']})"
    
    liq = sig["liq"]
    liq_eqh = fmt(liq["nearest_eqh"]) if liq["nearest_eqh"] else "NONE"
    liq_eql = fmt(liq["nearest_eql"]) if liq["nearest_eql"] else "NONE"
    
    rsi_val = sig["rsi_val"]

    print_market_structure(ms_htf, ms_ltf, "4H", "1H", rsi_val, fvg_nearest, ob_nearest, liq_eqh, liq_eql)

    # Score breakdown
    print(f"\nSCORE BREAKDOWN ({score}/10)")
    for note in sig["notes"]:
        if "⚠️" in note:
            icon = "⚠️"
        elif "0 pts" in note or "no " in note.lower() or "flat" in note.lower():
            icon = "  ─"
        else:
            icon = " ✅"
        print(f"  {icon} {note}")
    print(f"  {'─'*40}")
    print(f"  TOTAL: {score}/10")

    # 2. Trade Plan or Waiting Room (Section 3)
    if score >= 6 and direction != "SKIP":
        plan = build_trade_plan(symbol, price, quote_vol, k1h, direction, sig)
        
        # Use standard print_trade_plan
        print_trade_plan(
            symbol=symbol, direction=direction, score=score, grade=plan["grade"],
            entry=plan["entry_mid"], entry_note="Breakout trigger / 15M range mid", 
            stops={"sl": plan["sl"], "sl_pct": plan["sl_pct"]/100, "tp1": plan["tp1"], "tp2": plan["tp2"]}, 
            sizing={"label": plan["type_label"], "lev": plan["lev"], "margin": plan["margin"], "risk": plan["actual_risk"]},
            trail_callback_pct=3.0, invalidation=plan["sl"],
            tf_label="1H"
        )
        return plan
    else:
        # WAITING ROOM
        reasons = []
        if direction == "SKIP":
            reasons.append("Direction unclear — no structural bias on 4H")
        if score < 6:
            reasons.append(f"Score {score}/10 — need 6+ for entry")
        
        # Build key levels
        key_levels = []
        if sig["ms_1h"].get("swing_high"):
            key_levels.append((sig["ms_1h"]["swing_high"], "1H swing high — BOS target for LONG"))
        if sig["ms_1h"].get("swing_low"):
            key_levels.append((sig["ms_1h"]["swing_low"], "1H swing low — BOS target for SHORT"))
        if sig["liq"].get("nearest_eqh"):
            key_levels.append((sig["liq"]["nearest_eqh"], "EQH — buy-side liquidity"))
        if sig["liq"].get("nearest_eql"):
            key_levels.append((sig["liq"]["nearest_eql"], "EQL — sell-side liquidity"))

        # Preconditions
        preconditions = {
            "Range Contraction (15M)": sig["score"] >= 4, # simplified for example
            "Volume Building (15M)": sig["rel_vol"] > 1.1,
            "SMC Structure Aligned": direction != "SKIP",
            "SMC Confluence (FVG/OB)": sig["nearby_fvg"] is not None or sig["nearby_ob"] is not None,
            f"Score >= 6 (current: {score})": score >= 6
        }

        print_waiting_room(
            symbol=symbol, reasons=reasons,
            ms_htf=sig["ms_4h"], ms_ltf=sig["ms_1h"],
            htf_label="4H", ltf_label="1H",
            key_levels=key_levels[:5],
            preconditions=preconditions,
            next_window=get_next_session_window(),
            rerun_cmd=f"hunt {symbol}",
            verify_note="Check for 1H ChoCh or breakout close above/below 15M coil range",
            fvg_zones=sig["fvgs"][:3]
        )
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TELEGRAM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def build_telegram(results: list, session: dict, now: str) -> str:
    qualified  = [(sym, sig, plan) for sym, sig, plan in results if plan is not None]
    watch_list = [(sym, sig) for sym, sig, plan in results if plan is None and sig["score"] >= 4]

    lines = [
        f"🎯 HUNTER COIL | {now}",
        f"{len(results)} analyzed\n",
    ]

    if qualified:
        lines.append("🔥 QUALIFIED (Score ≥ 6)")
        for sym, sig, plan in qualified[:3]:
            d   = "🚀" if sig["direction"] == "LONG" else "🐻"
            fvg = (f" | FVG:{fmt(sig['nearby_fvg']['bottom'])}-{fmt(sig['nearby_fvg']['top'])}"
                   if sig["nearby_fvg"] else "")
            idm = f" | {sig['idm_flag']}" if sig["idm_flag"] else ""
            lines.append(
                f"{sym} {d} {sig['score']}/10 Grade:{plan['grade']}"
                f" ${sig.get('quote_vol', 0)/1e6:.0f}M{fvg}{idm}"
            )
            lines.append(
                f"Entry:{fmt(plan['entry_low'])}-{fmt(plan['entry_high'])} "
                f"SL:{fmt(plan['sl'])} TP1:{fmt(plan['tp1'])} TP2:{fmt(plan['tp2'])}"
            )
            lines.append(
                f"Grade:{plan['grade']} | Risk:${plan['actual_risk']:.2f} | "
                + (sig["notes"][0][:60] if sig["notes"] else "")
            )
    else:
        lines.append("⛔ NO QUALIFIED COILS")

    if watch_list:
        lines.append("\n👀 WATCHING: " + ", ".join(s for s, _ in watch_list[:5]))

    lines += ["", f"⏰ {session['window']} | {session['quality']}"]
    msg = "\n".join(lines)
    return msg[:4093] + "..." if len(msg) > 4093 else msg


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    symbols = [s.upper() for s in sys.argv[1:] if not s.startswith("-")]
    if not symbols:
        print("Usage: python hunter_coil.py SYMBOL [SYMBOL2 ...]")
        print("Example: python hunter_coil.py SOLUSDT ETHUSDT PEPEUSDT")
        sys.exit(1)

    # ── Section 1: Session Check (once, at top) ────────────────────────────────
    session = get_session_info()
    now     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n{'═'*60}")
    print(f"  🎯 HUNTER — COIL SCORER  (SMC Edition)")
    print(f"  {now} PHT  |  {len(symbols)} symbol(s): {', '.join(symbols)}")
    print(f"{'═'*60}")
    print_session_check(session)

    # ── Fetch + Score ──────────────────────────────────────────────────────────
    results = []  # list of (symbol, sig, plan_or_None)

    for symbol in symbols:
        print(f"\n[→] Fetching data for {symbol}...")
        k15  = fetch_klines(symbol, "15m", 50)
        k1h  = fetch_klines(symbol, "1h",  100)
        k4h  = fetch_klines(symbol, "4h",  100)
        tick = fetch_ticker(symbol)

        if not k15 or not k1h or not k4h or not tick:
            print(f"  ✗ Insufficient data for {symbol}. Skipping.")
            continue
        if len(k15) < 9 or len(k1h) < 30 or len(k4h) < 20:
            print(f"  ✗ Not enough candles for {symbol}. Skipping.")
            continue

        price     = float(k1h[-1][4])
        quote_vol = float(tick.get("quoteVolume", 0))

        sig  = score_coil(symbol, k15, k1h, k4h, quote_vol, price)
        plan = print_coil_analysis(symbol, price, quote_vol, sig, k1h)

        # Attach quote_vol to sig for Telegram (convenience)
        sig["quote_vol"] = quote_vol
        results.append((symbol, sig, plan))

    # ── Multi-symbol Summary ───────────────────────────────────────────────────
    if len(symbols) > 1 and results:
        print(f"\n\n{'═'*60}")
        print(f"  COIL SCAN SUMMARY — {len(results)} analyzed")
        print(f"{'═'*60}")
        print(f"\n  {'Symbol':<16} {'Score':<8} {'Dir':<8} {'Status'}")
        print(f"  {'─'*54}")
        for sym, sig, plan in results:
            status = ("🔥 PRIME" if sig["score"] >= 8 else
                      "✅ GOOD"  if sig["score"] >= 6 else
                      "👀 WATCH" if sig["score"] >= 4 else
                      "❌ SKIP")
            print(f"  {sym:<16} {sig['score']}/10    {sig['direction']:<8} {status}")

        qualified = [(s, si, pl) for s, si, pl in results if pl is not None]
        watching  = [(s, si) for s, si, pl in results if pl is None and si["score"] >= 4]

        print()
        if qualified:
            print(f"  🎯 QUALIFIED : {', '.join(s for s, _, _ in qualified)}")
        if watching:
            print(f"  👀 WATCHING  : {', '.join(s for s, _ in watching)}")
        if not qualified and not watching:
            print(f"  ⛔ NO COILS DETECTED — nothing qualifies in this set")
            if not session["can_scalp"]:
                print(f"  {session['advice']}")

    elif not results:
        print("\n  ⛔ No valid data returned for any symbol. Check VPN / symbol names.")

    # ── Section 4: Telegram ───────────────────────────────────────────────────
    tg_msg = build_telegram(results, session, now)
    send_telegram(tg_msg)


if __name__ == "__main__":
    main()
