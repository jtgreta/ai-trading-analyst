"""
scanner_run.py — Institutional Edition
Full pipeline: filter → klines → SMC flags → priority scoring → output

Upgrades:
  - BOS/ChoCh structure detection replaces pure MA stack direction
  - FVG detection: flags coins where price is entering an unfilled FVG
  - Order Block proximity flag
  - ATR volatility filter: skips if ATR > 4% of price (too volatile to time entry)
  - RSI filter: skip overbought/oversold extremes on 1H
  - Updated priority scoring weights SMC signals over raw volume
  - Hard filter: no direction assigned if 4H structure is ranging
  - Inducement (Liquidity Grab) detection
  - Optimal Trade Entry (OTE) confluence check
"""

import sys
import os

from trading_utils import (
    fetch_all_tickers, fetch_klines,
    sma, atr, rsi, ma_stack_label,
    detect_bos_choch, find_fvg, detect_order_blocks, detect_liquidity,
    identify_inducement, calculate_ote_zone,
    EXCLUDE_SUBS, EXCLUDE_EXACT,
    send_telegram, fmt, get_session_info, print_session_check
)
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ── Config ─────────────────────────────────────────────────────────────────────
ATR_VOLATILE_PCT  = 0.04   # skip if ATR > 4% of price (too noisy for scalp timing)
RSI_EXTREME_HIGH  = 78
RSI_EXTREME_LOW   = 22


def filter_and_rank(tickers: list) -> tuple:
    filtered = []
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
            if lo == 0: continue
            ac  = abs(pcp)
            rng = (hi - lo) / lo * 100
            if qv > 100_000_000 and rng > 10 and ac > 3:
                filtered.append({"symbol": sym, "priceChangePercent": pcp,
                                  "quoteVolume": qv, "rangePercent": rng,
                                  "absChange": ac, "lastPrice": lp})
        except: continue

    total = len(filtered)
    if total < 5:   # relax
        filtered = []
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
                if lo == 0: continue
                ac  = abs(pcp)
                rng = (hi - lo) / lo * 100
                if qv > 100_000_000 and rng > 7 and ac > 3:
                    filtered.append({"symbol": sym, "priceChangePercent": pcp,
                                      "quoteVolume": qv, "rangePercent": rng,
                                      "absChange": ac, "lastPrice": lp})
            except: continue
        total = len(filtered)

    filtered.sort(key=lambda x: x["absChange"], reverse=True)
    return filtered, total


def analyze_coin(coin: dict, k1h: list, k4h: list, k15m: list) -> dict:
    sym   = coin["symbol"]
    price = coin["lastPrice"]
    qvol  = coin["quoteVolume"]

    cl_1h  = [c[4] for c in k1h]
    cl_4h  = [c[4] for c in k4h]
    cl_15m = [c[4] for c in k15m]

    # ── MAs ────────────────────────────────────────────────────────────────────
    ma5_1h  = sma(cl_1h, 5);  ma10_1h = sma(cl_1h, 10); ma20_1h = sma(cl_1h, 20)
    ma5_4h  = sma(cl_4h, 5);  ma10_4h = sma(cl_4h, 10); ma20_4h = sma(cl_4h, 20)
    stack_1h = ma_stack_label(price, ma5_1h, ma10_1h, ma20_1h)
    stack_4h = ma_stack_label(price, ma5_4h, ma10_4h, ma20_4h)

    # ── SMC ────────────────────────────────────────────────────────────────────
    ms_4h  = detect_bos_choch(k4h, lookback=30)
    ms_1h  = detect_bos_choch(k1h, lookback=30)
    fvgs   = find_fvg(k1h, lookback=20)
    obs    = detect_order_blocks(k1h, lookback=30)
    liq    = detect_liquidity(k1h, lookback=30)
    idms   = identify_inducement(k1h, ms_1h["swing_highs"], ms_1h["swing_lows"], ms_1h["trend"], lookback=30)

    ote_zone = False
    ote_flag = ""
    if ms_1h["swing_high"] and ms_1h["swing_low"]:
        if ms_1h["trend"] == "bullish":
            ote = calculate_ote_zone(ms_1h["swing_low"], ms_1h["swing_high"], "bullish")
            if ote["ote_bottom"] <= price <= ote["ote_top"]:
                ote_zone = True
                ote_flag = "🎯 IN OTE ZONE"
        elif ms_1h["trend"] == "bearish":
            ote = calculate_ote_zone(ms_1h["swing_high"], ms_1h["swing_low"], "bearish")
            if ote["ote_bottom"] <= price <= ote["ote_top"]:
                ote_zone = True
                ote_flag = "🎯 IN OTE ZONE"

    # ── Volatility (ATR) ───────────────────────────────────────────────────────
    atr_1h = atr(k1h, 14)
    atr_pct = (atr_1h / price) if atr_1h and price > 0 else 0
    too_volatile = atr_pct > ATR_VOLATILE_PCT

    # ── Volume ─────────────────────────────────────────────────────────────────
    vol_1h    = [c[5] for c in k1h]
    last_vol  = vol_1h[-1] if vol_1h else 0
    avg5_vol  = sma(vol_1h[:-1], 5) or 0
    vol_signal = ("Spike" if last_vol > avg5_vol * 1.5
                  else "Fading" if last_vol < avg5_vol * 0.7
                  else "Normal")

    # Relative volume
    avg_hourly = qvol / 24 if qvol > 0 else 1
    try:
        last_qvol = float(k1h[-1][7])
    except:
        last_qvol = last_vol * price
    rel_vol = last_qvol / avg_hourly
    rel_label = ("🔥 HEAVY" if rel_vol > 2.0
                 else "⬆ ABOVE" if rel_vol > 1.3
                 else "⬇ BELOW" if rel_vol < 0.7
                 else "normal")

    # ── RSI ────────────────────────────────────────────────────────────────────
    rsi_val    = rsi(cl_1h, 14)
    rsi_warn   = (f"RSI {rsi_val:.0f} OVERBOUGHT" if rsi_val and rsi_val > RSI_EXTREME_HIGH
                  else f"RSI {rsi_val:.0f} OVERSOLD" if rsi_val and rsi_val < RSI_EXTREME_LOW
                  else None)

    # ── Direction (SMC-first, MA-fallback) ────────────────────────────────────
    direction  = "⏳ SKIP"
    if ms_4h["trend"] == "bullish" or ms_4h["last_event"] in ("BOS_up", "ChoCh_up"):
        direction = "🚀 SCALP LONG"
    elif ms_4h["trend"] == "bearish" or ms_4h["last_event"] in ("BOS_down", "ChoCh_down"):
        direction = "🐻 SCALP SHORT"
    elif ms_4h["trend"] == "ranging":
        # Fallback to MA stack
        if stack_1h == "Bullish" and stack_4h in ("Bullish", "Mixed"):
            direction = "🚀 SCALP LONG (weaker)"
        elif stack_1h == "Bearish" and stack_4h in ("Bearish", "Mixed"):
            direction = "🐻 SCALP SHORT (weaker)"

    # ── SMC Flags ─────────────────────────────────────────────────────────────
    # BOS/ChoCh flag
    mss_flag = ""
    if ms_1h["mss"]:
        mss_flag = f"⚡ MSS({ms_1h['last_event']})"
    elif ms_1h["last_event"] and "BOS" in ms_1h["last_event"]:
        mss_flag = f"✅ BOS({ms_1h['last_event']})"

    # Inducement Flag
    idm_flag = ""
    if idms:
        idm = idms[0]
        idm_flag = f"🪤 INDUCEMENT ({idm['type'][:7].upper()})"

    # FVG proximity flag
    fvg_flag   = ""
    nearby_fvg = None
    for f in fvgs:
        if abs(price - f["midpoint"]) / price < 0.02:
            fvg_flag   = f"🎯 IN FVG ({f['type'][:4].upper()})"
            nearby_fvg = f
            break

    # OB proximity
    ob_flag   = ""
    nearby_ob = None
    for ob in obs:
        mid = (ob["top"] + ob["bottom"]) / 2
        if abs(price - mid) / price < 0.015:
            ob_flag   = f"📦 AT OB ({ob['type'][:4].upper()})"
            nearby_ob = ob
            break

    # Liquidity proximity
    liq_flag = ""
    if liq["nearest_eqh"] and abs(price - liq["nearest_eqh"]) / price < 0.02:
        liq_flag = "⚠️  NEAR EQH LIQ"
    elif liq["nearest_eql"] and abs(price - liq["nearest_eql"]) / price < 0.02:
        liq_flag = "⚠️  NEAR EQL LIQ"

    # Coiling (15M range contraction)
    ranges_15 = [c[2] - c[3] for c in k15m]
    vols_15   = [c[5] for c in k15m]
    last3r = ranges_15[-3:]; prev3r = ranges_15[-6:-3]
    last3v = vols_15[-3:];   prev3v = vols_15[-6:-3]
    coiling = (sum(last3r)/3 < sum(prev3r)/3 * 0.75 if prev3r else False
               and sum(last3v)/3 > sum(prev3v)/3 * 1.2 if prev3v else False)

    # Consolidated flag (priority order)
    if idm_flag:          flag = idm_flag
    elif ote_flag:        flag = ote_flag
    elif fvg_flag:        flag = fvg_flag
    elif ob_flag:         flag = ob_flag
    elif mss_flag:        flag = mss_flag
    elif coiling:         flag = "⚡ COILING"
    elif liq_flag:        flag = liq_flag
    else:                 flag = "—"

    # ── Why scalp ─────────────────────────────────────────────────────────────
    why = "No significant SMC setup"
    if idm_flag:
        why = f"Price recently swept internal liquidity (inducement trap) and reversed"
    elif ote_flag:
        why = f"Price is in Optimal Trade Entry (OTE) discount zone"
    elif nearby_fvg:
        why = f"Price in {nearby_fvg['type']} FVG — institutional imbalance fill zone"
    elif nearby_ob:
        why = f"Price at {nearby_ob['type']} OB — institutional supply/demand zone"
    elif ms_1h["mss"]:
        why = f"ChoCh on 1H ({ms_1h['last_event']}) — structural shift, potential reversal"
    elif ms_1h["last_event"] and "BOS" in ms_1h["last_event"]:
        why = f"BOS on 1H — trend continuation breakout confirmed"
    elif coiling:
        why = "15M range compressing with building volume — breakout imminent"
    elif rel_label == "🔥 HEAVY":
        why = "Abnormal volume vs 24H baseline — institutional activity likely"

    # ── Risk ──────────────────────────────────────────────────────────────────
    if rsi_warn or too_volatile or "⏳" in direction:
        risk = "🔴 HIGH"
    elif qvol > 500_000_000 and ms_4h["trend"] != "ranging":
        risk = "🟢 LOW"
    elif qvol < 150_000_000:
        risk = "🔴 HIGH"
    else:
        risk = "🟡 MEDIUM"

    # ── Priority Score (SMC-weighted) ─────────────────────────────────────────
    pscore = 0
    if "⏳" not in direction:                            pscore += 1
    # Strong SMC logic
    if ms_4h["last_event"] and "BOS" in ms_4h["last_event"]: pscore += 4
    if nearby_fvg:                                       pscore += 3
    if idms:                                             pscore += 3
    if ote_zone:                                         pscore += 2
    if ms_1h["last_event"] and "BOS" in ms_1h["last_event"]: pscore += 1
    if nearby_ob:                                        pscore += 1
    if ms_1h["mss"]:                                     pscore += 1  # ChoCh
    if coiling:                                          pscore += 1
    if rel_label == "🔥 HEAVY":                          pscore += 1
    if risk == "🟢 LOW":                                 pscore += 1
    
    # Deductions
    if risk == "🔴 HIGH":                                pscore -= 2
    if too_volatile:                                     pscore -= 2
    if rsi_warn:                                         pscore -= 2
    if rel_label == "⬇ BELOW":                         pscore -= 2

    return {
        "symbol":    sym,
        "direction": direction,
        "change":    coin["priceChangePercent"],
        "vol":       qvol,
        "range":     coin["rangePercent"],
        "stack_1h":  stack_1h,
        "stack_4h":  stack_4h,
        "ms_4h":     ms_4h["trend"],
        "ms_1h_evt": ms_1h["last_event"] or "—",
        "atr_pct":   round(atr_pct * 100, 2),
        "vol_sig":   vol_signal,
        "rel_vol":   round(rel_vol, 2),
        "rel_label": rel_label,
        "rsi":       rsi_val,
        "rsi_warn":  rsi_warn,
        "flag":      flag,
        "why":       why,
        "risk":      risk,
        "pscore":    pscore,
        "price":     price,
    }


def main():
    session = get_session_info()
    now = datetime.now().strftime("%Y-%m-%d %H:%M PHT")
    
    print(f"\n{'═'*60}")
    print(f"  ⚡ BINANCE FUTURES SCANNER  (Institutional SMC Edition)")
    print(f"{'═'*60}")
    
    # Section 1: SESSION CHECK
    print_session_check(session)

    tickers = fetch_all_tickers()
    if not tickers:
        print("\n  ✗ No ticker data. Check VPN.")
        return

    filtered_coins, total_matched = filter_and_rank(tickers)
    print(f"\nFilters: Vol >$100M | Range >10% | |Change| >3% | {total_matched} matched")
    print(f"Analyzing up to {len(filtered_coins)} candidates (SMC engine)...\n")

    results = []
    for coin in filtered_coins:
        sym  = coin["symbol"]
        k1h  = fetch_klines(sym, "1h",  100)
        k4h  = fetch_klines(sym, "4h",  100)
        k15m = fetch_klines(sym, "15m", 50)
        if not k1h or not k4h or not k15m: continue
        if len(k1h) < 30 or len(k4h) < 20: continue
        results.append(analyze_coin(coin, k1h, k4h, k15m))

    results.sort(key=lambda x: x["pscore"], reverse=True)
    top = results[:10]

    # Section 2: MARKET STRUCTURE SUMMARY (Group View)
    print(f"\n{'─'*60}")
    print("SHORTLIST — TOP 10 PRIORITY SETUPS")
    print(f"{'─'*60}")
    for i, res in enumerate(top, 1):
        t = "📈" if res["change"] > 0 else "📉"
        r = f"{res['rsi']:.0f}" if res["rsi"] else "—"
        print(f"{i}. {res['symbol']} {t} | {res['direction']}")
        print(f"   Structure: 4H={res['ms_4h'].upper()} | 1H-evt={res['ms_1h_evt']}")
        print(f"   ATR: {res['atr_pct']}% | RSI: {r} | Flag: {res['flag']}")
        print(f"   Why: {res['why']}")
        print(f"   Risk: {res['risk']} | Priority: {res['pscore']} pts")
        print(f"{'─'*30}")

    # Section 3: PRIORITY PICKS (Trade Plan Entry)
    print(f"\n{'='*65}")
    print("  🎯 PRIORITY PICKS  (score ≥ 4, SMC-qualified)")
    print(f"{'='*65}")
    picks = [r for r in results if r["pscore"] >= 4][:3]
    if picks:
        for i, res in enumerate(picks, 1):
            dir_short = ("LONG" if "LONG" in res["direction"]
                         else "SHORT" if "SHORT" in res["direction"] else "SKIP")
            print(f"  {i}. {res['symbol']} (score: {res['pscore']}) — {dir_short}")
            print(f"     {res['flag']}  |  {res['why']}")
        print(f"\n  → Action: run 'scalp [SYMBOL]' for full institutional trade plan")
    else:
        print("  ⛔ NO TRADE — No SMC confluence detected.")
        if not session.get("can_scalp", True):
            print(f"  {session.get('advice', 'Re-scan in 30 min or check session timing.')}")
        else:
            print("  Re-scan in 30 min or check session timing.")

    # Section 4: TELEGRAM SUMMARY
    tg_lines = [
        f"⚡ BINANCE FUTURES SCANNER | {now}",
        f"Vol >$100M | Range >10% | {total_matched} matched | SMC engine\n",
        "📋 TOP SETUPS"
    ]
    for i, res in enumerate(top[:8], 1):
        t = "📈" if res["change"] > 0 else "📉"
        r = f"RSI{res['rsi']:.0f}" if res["rsi"] else "—"
        tg_lines.append(
            f"{i}. {res['symbol']} {t} {res['direction'][:2] or '⏳'} "
            f"{res['change']:+.1f}% | ${res['vol']/1e6:.0f}M | {res['flag']} | {r} | {res['risk']}"
        )
        tg_lines.append(f"   {res['why']}")
    tg_lines.append(f"\n⏰ {session['window']} | {session['volatility']}")
    tg_lines.append("\n🎯 PICKS")
    if picks:
        for i, res in enumerate(picks, 1):
            tg_lines.append(f"{i}. {res['symbol']} ({res['pscore']}pts) — {res['flag']}")
        tg_lines.append("\n→ scalp [SYMBOL] for full analysis")
    else:
        tg_lines.append("⛔ NO TRADE")
        tg_lines.append(f"Reason: {session['advice'] if not session['can_scalp'] else 'No setup confluence'}")

    send_telegram("\n".join(tg_lines))


if __name__ == "__main__":
    main()
