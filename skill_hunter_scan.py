"""
skill_hunter_scan.py — Institutional Edition
Pre-breakout coil scanner with full SMC overlay.
Usage: python skill_hunter_scan.py

Upgrades:
  - SMC: BOS/ChoCh context for breakout direction confirmation
  - FVG: identifies whether the breakout target is an unfilled imbalance
  - Order Block: flags breakout into an OB zone (supply/demand)
  - ATR-based stop calculation for the trade plan
  - RSI overbought/oversold filter on 15M and 1H
  - Coil score enhanced: ChoCh as bonus signal (structural setup)
  - Inducement integration: Liquidity Grab + OB Confluence (+3 pts)
  - Dynamic grade-based position sizing (A/B/C)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from trading_utils import (
    fetch_all_tickers, fetch_klines, fetch_ticker,
    sma, atr, rsi, ma_stack_label,
    detect_bos_choch, find_fvg, detect_order_blocks, detect_liquidity,
    identify_inducement, classify_token, calc_position,
    SCALP_RULES, EXCLUDE_SUBS, EXCLUDE_EXACT,
    send_telegram, fmt, get_session_info, print_session_check
)
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

CAPITAL = 100.0


def get_candidates(tickers: list) -> list:
    candidates = []
    for t in tickers:
        sym = t.get("symbol", "")
        if any(sub in sym for sub in EXCLUDE_SUBS): continue
        if sym in EXCLUDE_EXACT: continue
        try:
            qv  = float(t["quoteVolume"])
            pcp = float(t["priceChangePercent"])
            hi  = float(t["highPrice"])
            lo  = float(t["lowPrice"])
            lp  = float(t["lastPrice"])
            if lo <= 0 or lp <= 0: continue
            rng = (hi - lo) / lo * 100
            ac  = abs(pcp)
            if qv > 100_000_000 and 3 < rng < 25 and ac < 15:
                candidates.append({"symbol": sym, "quoteVolume": qv,
                                   "lastPrice": lp, "pctChange": pcp,
                                   "range24h": rng})
        except: continue

    if len(candidates) < 5:
        for t in tickers:
            sym = t.get("symbol", "")
            if any(sub in sym for sub in EXCLUDE_SUBS): continue
            if sym in EXCLUDE_EXACT: continue
            try:
                qv  = float(t["quoteVolume"])
                pcp = float(t["priceChangePercent"])
                hi  = float(t["highPrice"])
                lo  = float(t["lowPrice"])
                lp  = float(t["lastPrice"])
                if lo <= 0: continue
                rng = (hi - lo) / lo * 100
                ac  = abs(pcp)
                if qv > 100_000_000 and 3 < rng < 30 and ac < 15:
                    if not any(c["symbol"] == sym for c in candidates):
                        candidates.append({"symbol": sym, "quoteVolume": qv,
                                           "lastPrice": lp, "pctChange": pcp,
                                           "range24h": rng})
            except: continue
    return candidates


def score_coin(cand: dict, k15: list, k1h: list, k4h: list) -> dict:
    score     = 0
    direction = "SKIP"
    notes     = []
    price     = cand["lastPrice"]

    closed_15 = k15[:-1]   # exclude forming candle

    # ── A. Range Contraction on 15M (max 3 pts) ─────────────
    if len(closed_15) >= 8:
        last4_r = [c[2] - c[3] for c in closed_15[-4:]]
        prev4_r = [c[2] - c[3] for c in closed_15[-8:-4]]
        avg_last = sum(last4_r) / 4
        avg_prev = sum(prev4_r) / 4
        if avg_prev > 0:
            ratio = avg_last / avg_prev
            if   ratio < 0.50: score += 3; notes.append(f"tight squeeze ({ratio:.2f}x range)")
            elif ratio < 0.65: score += 2; notes.append(f"moderate compression ({ratio:.2f}x range)")
            elif ratio < 0.80: score += 1; notes.append(f"mild compression ({ratio:.2f}x range)")

    # ── B. Volume Building on 15M (max 2 pts) ────────────────────
    if len(closed_15) >= 8:
        last4_v = sum(c[5] for c in closed_15[-4:]) / 4
        prev4_v = sum(c[5] for c in closed_15[-8:-4]) / 4
        if prev4_v > 0:
            vr = last4_v / prev4_v
            if   vr > 1.4: score += 2; notes.append(f"volume building ({vr:.2f}x)")
            elif vr > 1.1: score += 1; notes.append(f"volume slightly up ({vr:.2f}x)")
            else:          notes.append(f"volume flat ({vr:.2f}x)")

    # ── C. Market Structure on 1H + 4H ───
    ms_1h = detect_bos_choch(k1h, lookback=30)
    ms_4h = detect_bos_choch(k4h, lookback=30)

    if ms_4h["trend"] == "bullish" and ms_1h["trend"] in ("bullish", "ranging"):
        score += 2; direction = "LONG";  notes.append("4H bullish structure + 1H aligned")
    elif ms_4h["trend"] == "bearish" and ms_1h["trend"] in ("bearish", "ranging"):
        score += 2; direction = "SHORT"; notes.append("4H bearish structure + 1H aligned")
    elif ms_4h["trend"] == "bullish":
        score += 1; direction = "LONG";  notes.append("4H bullish (1H conflicting)")
    elif ms_4h["trend"] == "bearish":
        score += 1; direction = "SHORT"; notes.append("4H bearish (1H conflicting)")
    else:
        # Fallback to MA if structure is ranging
        cl_1h = [c[4] for c in k1h]
        cl_4h = [c[4] for c in k4h]
        ma10_1h = sma(cl_1h, 10); ma20_1h = sma(cl_1h, 20)
        ma10_4h = sma(cl_4h, 10); ma20_4h = sma(cl_4h, 20)
        bull_1h = ma10_1h and ma20_1h and price > ma10_1h > ma20_1h
        bear_1h = ma10_1h and ma20_1h and price < ma10_1h < ma20_1h
        bull_4h = ma10_4h and ma20_4h and price > ma10_4h > ma20_4h
        bear_4h = ma10_4h and ma20_4h and price < ma10_4h < ma20_4h
        if bull_1h or bull_4h: score += 1; direction = "LONG";  notes.append("MA lean bullish (ranging structure)")
        elif bear_1h or bear_4h: score += 1; direction = "SHORT"; notes.append("MA lean bearish (ranging structure)")

    # ── D. ChoCh Bonus (+1 pt) ──
    if ms_1h["mss"]:
        score += 1
        notes.append(f"ChoCh on 1H ({ms_1h['last_event']}) — structural breakout setup")

    # ── E. Price at FVG (max 1 pt) ────────────────────────────
    fvgs = find_fvg(k1h, lookback=25)
    nearby_fvg = None
    for fvg in fvgs:
        if abs(price - fvg["midpoint"]) / price < 0.015:
            score += 1; nearby_fvg = fvg
            notes.append(f"In {fvg['type']} FVG ({fmt(fvg['bottom'])}–{fmt(fvg['top'])})")
            break

    # Order Blocks
    obs = detect_order_blocks(k1h, lookback=30)
    nearby_ob = None
    for ob in obs:
        mid = (ob["top"] + ob["bottom"]) / 2
        if abs(price - mid) / price < 0.015:
            nearby_ob = ob
            break

    # ── Inducement + OB Confluence (Liquidity Grab) (+3 pts) ──
    idms = identify_inducement(k1h, ms_1h["swing_highs"], ms_1h["swing_lows"], ms_1h["trend"], lookback=30)
    idm_flag = ""
    if idms and nearby_ob:
        score += 3
        idm_flag = "🪤 Liquidity Grab + OB Confluence"
        notes.append(idm_flag)

    # ── F. Relative Volume vs 24H baseline ────────────
    avg_hourly = cand["quoteVolume"] / 24
    try:
        last_1h_qvol = float(k1h[-2][7])
    except:
        last_1h_qvol = k1h[-2][5] * k1h[-2][4]
    rel_vol = last_1h_qvol / avg_hourly if avg_hourly > 0 else 0
    if rel_vol > 1.5:
        score += 1; notes.append(f"rel vol {rel_vol:.2f}x (above avg)")
    else:
        notes.append(f"rel vol {rel_vol:.2f}x")

    # ── RSI filter
    cl_1h_closes = [c[4] for c in k1h]
    rsi_val = rsi(cl_1h_closes, 14)
    rsi_flag = ""
    if rsi_val:
        if direction == "LONG"  and rsi_val > 75:
            score -= 1; rsi_flag = f"⚠️  RSI {rsi_val:.0f} overbought — late entry risk"
        elif direction == "SHORT" and rsi_val < 25:
            score -= 1; rsi_flag = f"⚠️  RSI {rsi_val:.0f} oversold — counter-trend risk"

    # ATR
    atr_val = atr(k1h, 14)
    atr_pct = (atr_val / price * 100) if atr_val and price > 0 else 0

    return {
        "score":      score,
        "direction":  direction,
        "notes":      notes,
        "rel_vol":    rel_vol,
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
        "closed_15":  closed_15,
    }


def build_trade_plan(cand: dict, sig: dict, k1h: list) -> dict:
    """
    Build ATR-based trade plan from coil signal.
    k1h: the actual 1H candle list fetched in main() — used for ATR calculation.
    """
    symbol    = cand["symbol"]
    price     = cand["lastPrice"]
    direction = sig["direction"]

    tok_type = classify_token(symbol, cand["quoteVolume"])
    rules    = SCALP_RULES[tok_type]

    # Grade from coil score
    grade = "A" if sig["score"] >= 8 else "B" if sig["score"] >= 6 else "C"

    # Entry zone from last 4 closed 15M candles
    c15 = sig["closed_15"]
    entry_low  = min(c[3] for c in c15[-4:])
    entry_high = max(c[2] for c in c15[-4:])
    entry_mid  = (entry_low + entry_high) / 2

    # ATR-based stop anchored to entry midpoint
    # Use sig["atr_val"] (pre-computed from k1h in score_coin) directly —
    # avoids calling calc_atr_stop with k1h again while keeping logic consistent.
    if sig["atr_val"] is not None:
        atr_dist = sig["atr_val"] * 1.5
        sl_dist  = min(atr_dist, entry_mid * rules["max_sl"])
    else:
        # Fallback: use entry zone range as proxy for volatility
        range_stop = entry_high - entry_low
        sl_dist    = max(range_stop, entry_mid * rules["max_sl"] * 0.5)

    sl_pct = sl_dist / entry_mid

    if direction == "LONG":
        sl        = entry_mid - sl_dist
        tp1_price = entry_mid + sl_dist * 2.0
        tp2_price = entry_mid + sl_dist * 3.5
    else:
        sl        = entry_mid + sl_dist
        tp1_price = entry_mid - sl_dist * 2.0
        tp2_price = entry_mid - sl_dist * 3.5

    # Refine TP1 to FVG boundary if in breakout direction with ≥ 1.5 RR
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
        "lev":         sizing["lev"],
        "margin":      sizing["margin"],
        "position":    sizing["position"],
        "actual_risk": actual_risk,
        "grade":       grade,
        "wide_stop":   wide_stop,
    }


def print_setup(i: int, cand: dict, sig: dict, plan: dict):
    symbol    = cand["symbol"]
    score     = sig["score"]
    direction = sig["direction"]
    score_lbl = "🔥 PRIME" if score >= 8 else "✅ GOOD"
    dir_emoji = "🚀" if direction == "LONG" else ("🐻" if direction == "SHORT" else "⏳")
    type_lbl  = {"major": "BTC/ETH/BNB", "midcap": "Mid-cap", "new": "New/Meme/AI"}[plan["token_type"]]
    why       = " | ".join(sig["notes"][:3]) or "Coiling at key level"
    risk_ok   = "✅ Within rules" if plan["actual_risk"] <= 4.0 else "⚠️  OVER LIMIT"

    ms4h_txt = sig["ms_4h"]["trend"].upper()
    ms1h_txt = sig["ms_1h"]["last_event"] or "—"
    fvg_txt  = (f"  FVG: {sig['nearby_fvg']['type'].upper()} "
                f"{fmt(sig['nearby_fvg']['bottom'])}–{fmt(sig['nearby_fvg']['top'])}"
                if sig["nearby_fvg"] else "")
    ob_txt   = (f"  OB: {sig['nearby_ob']['type'].upper()} "
                f"{fmt(sig['nearby_ob']['bottom'])}–{fmt(sig['nearby_ob']['top'])}"
                if sig["nearby_ob"] else "")
    idm_txt  = f"  {sig['idm_flag']}" if sig["idm_flag"] else ""
    rsi_txt  = f"  {sig['rsi_flag']}" if sig["rsi_flag"] else ""
    atr_txt  = f"ATR: {fmt(sig['atr_val'])} ({sig['atr_pct']:.2f}%)" if sig["atr_val"] else ""

    print(f"""
{'─'*60}
{i}. {symbol}  Coil Score: {score}/10 [{score_lbl}]  {dir_emoji} {direction}
Type       : {type_lbl}  |  Grade: {plan['grade']} ({"Full" if plan['grade']=='A' else "Half" if plan['grade']=='B' else "25%"} size)
Volume     : ${cand['quoteVolume']/1e6:.1f}M  |  RelVol: {sig['rel_vol']:.2f}x  |  {atr_txt}
Structure  : 4H={ms4h_txt}  |  1H-event={ms1h_txt}
Why now    : {why}{idm_txt}{fvg_txt}{ob_txt}{rsi_txt}

📐 TRADE PLAN  (ATR-based stops)
  Entry Zone : {fmt(plan['entry_low'])} – {fmt(plan['entry_high'])}
               (enter on breakout CLOSE {'above' if direction=='LONG' else 'below'} {fmt(plan['entry_high'] if direction=='LONG' else plan['entry_low'])} + volume)
  Stop-Loss  : {fmt(plan['sl'])}  ({plan['sl_pct']:.2f}% from mid){'  ⚠️  WIDE' if plan['wide_stop'] else ''}
  TP1 (35%)  : {fmt(plan['tp1'])}  — RR 1:2.0 → move SL to breakeven
  TP2 (40%)  : {fmt(plan['tp2'])}  — RR 1:3.5 → activate trailing stop
  TP3 (25%)  : Trailing stop  (trail = {fmt(plan['trail_dist'])})

💰 POSITION SIZING  (Grade {plan['grade']})
  {type_lbl}  |  Margin: ${plan['margin']}  |  Lev: {plan['lev']}x  |  Position: ${plan['position']:.0f}
  Actual Risk: ${plan['actual_risk']:.2f}  ({plan['actual_risk']/CAPITAL*100:.1f}% of capital)  {risk_ok}""")


def build_telegram_msg(qualified, watch_list, verdict_line, now):
    lines = [
        f"🎯 HUNTER — PRE-BREAKOUT SCAN",
        f"{now}",
        f"Vol >$100M | Range 3–25% | SMC Engine\n",
    ]
    if qualified:
        lines.append("🔥 QUALIFIED SETUPS")
        for i, (cand, sig, plan) in enumerate(qualified[:3], 1):
            d   = "🚀" if sig["direction"] == "LONG" else "🐻"
            fvg = f" | FVG:{fmt(sig['nearby_fvg']['bottom'])}-{fmt(sig['nearby_fvg']['top'])}" if sig["nearby_fvg"] else ""
            idm = " | 🪤 IDM Grab" if sig["idm_flag"] else ""
            lines.append(
                f"{i}. {cand['symbol']} {sig['score']}/10 {d} "
                f"${cand['quoteVolume']/1e6:.0f}M | {sig['rel_vol']:.2f}x{fvg}{idm}"
            )
            lines.append(
                f"   Entry:{fmt(plan['entry_low'])}-{fmt(plan['entry_mid'])} "
                f"SL:{fmt(plan['sl'])} TP1:{fmt(plan['tp1'])} TP2:{fmt(plan['tp2'])}"
            )
            lines.append(
                f"   Grade:{plan['grade']} | Risk:${plan['actual_risk']:.2f} | "
                + (sig["notes"][0] if sig["notes"] else "")
            )
    else:
        lines.append("⛔ NO HUNT — no coil setups found")

    if watch_list:
        lines.append("\n👀 WATCHING: " + ", ".join(c["symbol"] for c, _ in watch_list[:4]))

    lines += ["", verdict_line]
    return "\n".join(lines)


def main():
    session = get_session_info()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'═'*60}")
    print(f"  🎯 HUNTER — PRE-BREAKOUT SCAN  (SMC Edition)")
    print(f"  {now} PHT")
    print(f"{'═'*60}")
    
    print_session_check(session)

    print("\n[1/4] Fetching tickers...")
    tickers = fetch_all_tickers()
    if not tickers:
        print("  ✗ No ticker data. Check VPN."); return

    print("[2/4] Filtering candidates...")
    candidates = get_candidates(tickers)
    print(f"  {len(candidates)} coins passed pre-breakout filter")

    print(f"[3/4] Scoring {len(candidates)} coins...")
    qualified  = []
    watch_list = []

    for cand in candidates:
        sym  = cand["symbol"]
        k15  = fetch_klines(sym, "15m", 50)
        k1h  = fetch_klines(sym, "1h",  100)
        k4h  = fetch_klines(sym, "4h",  100)
        if not k15 or not k1h or not k4h: continue
        if len(k15) < 9 or len(k1h) < 30 or len(k4h) < 20: continue

        sig = score_coin(cand, k15, k1h, k4h)

        if sig["score"] >= 6 and sig["direction"] != "SKIP":
            plan = build_trade_plan(cand, sig, k1h)
            qualified.append((cand, sig, plan))
        elif sig["score"] >= 4:
            watch_list.append((cand, sig))

    qualified.sort(key=lambda x: x[1]["score"], reverse=True)
    watch_list.sort(key=lambda x: x[1]["score"], reverse=True)

    print("[4/4] Building output...\n")
    print(f"\n{'═'*60}")
    print(f"  HUNTER  |  {len(candidates)} candidates  |  {len(qualified)} qualified")
    print(f"{'═'*60}")

    print(f"\n\n🔥 QUALIFIED SETUPS (Score ≥ 6 | {len(qualified)} found)")
    if not qualified:
        print("  None.")
    else:
        for i, (cand, sig, plan) in enumerate(qualified[:5], 1):
            print_setup(i, cand, sig, plan)

    if watch_list:
        print(f"\n\n👀 WATCH LIST (Score 4–5 — not ready yet)")
        print(f"{'#':<4} {'Symbol':<14} {'Score':<7} {'Dir':<8} {'Why watching'}")
        print("─" * 60)
        for i, (cand, sig) in enumerate(watch_list[:5], 1):
            why = sig["notes"][0] if sig["notes"] else "Some compression"
            print(f"{i:<4} {cand['symbol']:<14} {sig['score']}/10   {sig['direction']:<8} {why}")

    # Verdict
    print(f"\n\n{'═'*60}")
    if qualified:
        best_cand, best_sig, best_plan = qualified[0]
        dir_e = "🚀 LONG" if best_sig["direction"] == "LONG" else "🐻 SHORT"
        coil_high = max(c[2] for c in best_sig["closed_15"][-4:])
        coil_low  = min(c[3] for c in best_sig["closed_15"][-4:])
        bk_level  = fmt(coil_high if best_sig["direction"] == "LONG" else coil_low)
        verdict   = f"🎯 HUNT READY — {len(qualified)} setup(s) qualified"
        print(f"\n{verdict}")
        print(f"Best     : {best_cand['symbol']} (score {best_sig['score']}/10) — Grade {best_plan['grade']}")
        print(f"Direction: {dir_e}")
        print(f"Trigger  : Candle CLOSES {'above' if best_sig['direction']=='LONG' else 'below'} {bk_level} with volume spike")
        print(f"Structure: 4H={best_sig['ms_4h']['trend'].upper()} | 1H-event={best_sig['ms_1h']['last_event'] or '—'}")
        fvg_note = f"FVG target: {fmt(best_sig['nearby_fvg']['top'])}" if best_sig["nearby_fvg"] else ""
        if fvg_note: print(f"           {fvg_note}")
        print(f"Do NOT chase if price already moved >{fmt(best_plan['sl_dist'])} past zone")
    elif watch_list:
        verdict = "👀 SETUPS FORMING — not ready | re-scan in 30 min"
        print(f"\n{verdict}")
        print("Watching: " + ", ".join(c["symbol"] for c, _ in watch_list[:5]))
    else:
        verdict = "⛔ NO HUNT — nothing coiling"
        reason  = ("No coins passed filter — low liquidity window" if not candidates
                   else "No meaningful coil detected — use SCANNER for momentum plays")
        print(f"\n{verdict}")
        if not session["can_scalp"]:
            print(f"Session: {session['advice']}")
        else:
            print(f"Reason : {reason}")
            print("Re-scan at 9:00 PM PHT (London-NY open)")

    print(f"\n{'─'*60}")
    tg_msg = build_telegram_msg(qualified[:3], watch_list[:3], verdict, now)
    send_telegram(tg_msg)


if __name__ == "__main__":
    main()
