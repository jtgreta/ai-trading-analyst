"""Console output helpers and Telegram message formatters.

Every engine emits the same professional 4-section layout (Session → Structure →
Trade Plan / WAITING ROOM → Telegram summary). All text content mirrors the
original tool suite byte-for-byte so downstream parsing and workflows keep
working unchanged.
"""

from __future__ import annotations

import sys
from typing import Any, Optional


def fmt(price: Optional[float]) -> str:
    """Format a price with adaptive precision based on magnitude."""
    if price is None:
        return "N/A"
    if price >= 1000:
        return f"{price:,.2f}"
    if price >= 1:
        return f"{price:.4f}"
    if price >= 0.01:
        return f"{price:.5f}"
    return f"{price:.8f}"


def grade_label(grade: str) -> str:
    return {
        "A": "🏆 Grade A (Full)",
        "B": "✅ Grade B (Half)",
        "C": "⚡ Grade C (Waiting)",
    }.get(grade, grade)


def print_session_check(session: dict) -> None:
    print(f"""
⏰ SESSION CHECK  [{session['time_str']}]
Current window : {session['window']}
Volatility     : {session['volatility']}
Aggression     : {session['aggression']}
Advice         : {session['advice']}""")


def print_market_structure(
    ms_htf: dict, ms_ltf: dict, htf_label: str, ltf_label: str,
    rsi_val: Optional[float], fvg_nearest: str, ob_nearest: str,
    liq_eqh: str, liq_eql: str,
) -> None:
    mss_status = "✅ None"
    if ms_ltf.get("mss") or ms_htf.get("mss"):
        evt = ms_ltf.get("last_event") or ms_htf.get("last_event") or "unknown"
        mss_status = f"⚠️ YES — structural reversal signal ({evt})"
    rsi_label = "—"
    if rsi_val is not None:
        if rsi_val > 70:
            rsi_label = f"{rsi_val:.1f}  ⚠️ Overbought"
        elif rsi_val < 30:
            rsi_label = f"{rsi_val:.1f}  ⚠️ Oversold"
        else:
            rsi_label = f"{rsi_val:.1f}  🟢 Normal"
    print(f"""
MARKET STRUCTURE
  {htf_label} Trend  : {ms_htf['trend'].upper()}  |  Last event: {ms_htf['last_event'] or '—'}
  {ltf_label} Trend  : {ms_ltf['trend'].upper()}  |  Last event: {ms_ltf['last_event'] or '—'}
  MSS (ChoCh)  : {mss_status}
  FVG nearest  : {fvg_nearest}
  OB nearest   : {ob_nearest}
  Liquidity    : EQH at {liq_eqh} / EQL at {liq_eql}
  RSI ({ltf_label})     : {rsi_label}""")


def print_trade_plan(
    symbol: str, direction: str, score: int, grade: str, entry: float,
    entry_note: str, stops: dict, sizing: dict, trail_callback_pct: float,
    invalidation: float, tf_label: str = "4H",
) -> None:
    dir_emoji = "🚀" if direction == "LONG" else "🐻"
    quality = "🟢 PRIME" if score >= 8 else "🟡 GOOD"
    sl_pct = stops['sl_pct'] * 100
    sl_dist = abs(stops["sl"] - entry)
    rr1 = abs(stops["tp1"] - entry) / sl_dist if sl_dist > 0 else 0
    rr2 = abs(stops["tp2"] - entry) / sl_dist if sl_dist > 0 else 0
    inv_dir = "below" if direction == "LONG" else "above"
    print(f"""
{dir_emoji} {direction} — {quality}  Score: {score}/10  Grade: {grade}

Entry          : {fmt(entry)}  ← {entry_note}
Stop-Loss      : {fmt(stops['sl'])}  ({sl_pct:.2f}%  |  ATR × 1.5)
TP1 (35%)      : {fmt(stops['tp1'])}  → RR 1:{rr1:.1f}  → on hit: move SL to breakeven
TP2 (40% of rem.)  : {fmt(stops['tp2'])}  → RR 1:{rr2:.1f}  → on hit: activate trailing stop
TP3 (remaining)    : Trailing Stop — runner after TP2
                  Activation        : {fmt(stops['tp2'])}  (= TP2)
                  Size              : 100% of remaining position
                  Callback/variance : {trail_callback_pct:.2f}%  (ATR-derived)

Position
  {sizing['label']} | {sizing['lev']}x leverage | Margin: ${sizing['margin']} | Max risk: ${sizing['risk']:.2f}

Invalidation   : {tf_label} close {inv_dir} {fmt(invalidation)} → exit entire position.""")


def print_waiting_room(
    symbol: str, reasons: list, ms_htf: dict, ms_ltf: dict,
    htf_label: str, ltf_label: str, key_levels: list, preconditions: dict,
    next_window: str, rerun_cmd: str, verify_note: str,
    fvg_zones: Optional[list] = None, ob_zones: Optional[list] = None,
) -> None:
    print(f"""
⏳ WAITING ROOM  — No trade yet

Why not now:""")
    for r in reasons:
        print(f"  • {r}")
    print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHAT WOULD UNLOCK A TRADE""")
    sh = fmt(ms_ltf.get("swing_high")) if ms_ltf.get("swing_high") else "—"
    sl_val = fmt(ms_ltf.get("swing_low")) if ms_ltf.get("swing_low") else "—"
    bull_fvg_note = ""
    bear_fvg_note = ""
    if fvg_zones:
        for fvg in fvg_zones[:2]:
            if fvg["type"] == "bullish":
                bull_fvg_note = f"\n  🔓 {ltf_label} pullback to bullish FVG at {fmt(fvg['bottom'])}–{fmt(fvg['top'])}"
            elif fvg["type"] == "bearish":
                bear_fvg_note = f"\n  🔓 {ltf_label} pullback to bearish FVG at {fmt(fvg['bottom'])}–{fmt(fvg['top'])}"
    print(f"""
    For LONG to become valid:
    🔓 {htf_label} candle CLOSES above {sh} — confirms BOS{bull_fvg_note}

    For SHORT to become valid:
    🔓 {htf_label} candle CLOSES below {sl_val} — confirms BOS{bear_fvg_note}""")

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("KEY LEVELS TO WATCH")
    for price_val, desc in key_levels:
        print(f"  📍 {fmt(price_val)}  — {desc}")
    trend_word = ms_htf['trend'].capitalize() if ms_htf['trend'] != 'ranging' else 'Directional'
    print(f"""
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    PATTERN TO WATCH FOR
    {trend_word} setup trigger candle:

    1. Engulfing candle on {ltf_label} CLOSING at a key level with volume > 1.5x average
    2. Pin bar (hammer/shooting star) on 15M rejecting off an OB or FVG zone
    3. {ltf_label} BOS after a liquidity sweep of {'EQL' if ms_htf['trend'] != 'bearish' else 'EQH'}

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    PRE-CONDITIONS STATUS""")
    met = sum(1 for p in preconditions.values() if p)
    for name, passed in preconditions.items():
        print(f"  [{'✅' if passed else '❌'}] {name}")
    print(f"\n  {met} of {len(preconditions)} conditions met. Need all {len(preconditions)} for full green light.")
    print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NEXT CHECK

  🕒 Next best window : {next_window}
  📋 Re-run command   : {rerun_cmd}
  ⚡ What to verify   : {verify_note}""")


def format_telegram_trade(
    symbol: str, direction: str, grade: str, session: dict,
    structure: dict, zones: dict, risk: dict, invalidation: float,
) -> str:
    """Compact Telegram summary for a valid trade plan."""
    dir_emoji = "🚀" if direction == "LONG" else "🐻"
    lines = [
        f"⏰ {session['window']} | {session['volatility']}",
        f"{dir_emoji} {symbol} | {direction} | Grade {grade}",
        "",
        f"📐 {structure.get('tf_4h', '—')} | {structure.get('tf_1h', '—')}",
        f"Event: {structure.get('event', '—')}",
        "",
        f"Entry: {fmt(zones.get('entry', 0))}",
        f"SL: {fmt(risk['sl'])} ({risk['sl_pct']:.2f}%)",
        f"TP1: {fmt(risk['tp1'])} | TP2: {fmt(risk['tp2'])}",
        f"Risk: ${risk['risk_usd']:.2f} | Margin: ${risk['margin']} | {risk['lev']}x",
        "",
        f"🚫 Invalidation: {'below' if direction == 'LONG' else 'above'} {fmt(invalidation)}",
    ]
    return "\n".join(lines)[:4090]


def format_telegram_waiting(
    symbol: str, session: dict, reasons: list, trigger_level: str, next_check: str,
) -> str:
    """Compact Telegram summary for a WAITING ROOM."""
    lines = [
        f"⏰ {session['window']} | {session['volatility']}",
        f"⏳ {symbol} — WAITING ROOM",
        "",
        "Why: " + "; ".join(reasons[:2]),
        f"Watch: {trigger_level}",
        f"Next: {next_check}",
    ]
    return "\n".join(lines)[:4090]


# ── Encoding guard ────────────────────────────────────────────────────────────

def ensure_utf8() -> None:
    """Force UTF-8 stdout (emoji/box-chars) on Windows consoles."""
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass