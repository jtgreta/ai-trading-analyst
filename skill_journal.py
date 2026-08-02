"""
skill_journal.py — Institutional Edition
Trade logger + weekly review + compliance tracker.

Usage:
  python skill_journal.py log SYMBOL DIRECTION ENTRY SL TP1 TP2 GRADE SCORE OUTCOME [NOTE]
  python skill_journal.py review             → weekly review summary
  python skill_journal.py stats              → all-time stats
  python skill_journal.py list [N]           → last N trades (default 10)
  python skill_journal.py delete ID          → remove a trade entry

OUTCOME options:
  win_tp1    → closed at TP1
  win_tp2    → closed at TP2
  win_tp3    → closed at TP3 / trailing stop
  loss_sl    → stopped out at SL
  loss_early → manual early exit (at a loss)
  win_early  → manual early exit (at a profit)
  be         → breakeven (moved SL to BE, hit BE)

GRADE: A, B, or C
SCORE: integer 0-10

Examples:
  python skill_journal.py log SOLUSDT LONG 145.50 140.00 156.00 165.00 B 7 win_tp1
  python skill_journal.py log ETHUSDT SHORT 3200 3320 3080 2970 A 9 loss_sl "news spike"
  python skill_journal.py review
  python skill_journal.py stats

Storage: Trades are saved to journal.json in the same directory.
Purpose: Enables the mandatory weekly review from trading_rules.md.
         Tracks win rate, compliance, average RR achieved, and rule violations.
"""

import sys
import os
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from trading_utils import send_telegram, get_session_info

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

JOURNAL_FILE = os.path.join(os.path.dirname(__file__), "journal.json")

VALID_OUTCOMES = {
    "win_tp1":    ("WIN",  "Closed at TP1 (35%)"),
    "win_tp2":    ("WIN",  "Closed at TP2 (40%)"),
    "win_tp3":    ("WIN",  "Closed at TP3 / trailing"),
    "win_early":  ("WIN",  "Manual exit in profit"),
    "loss_sl":    ("LOSS", "Stopped out at SL"),
    "loss_early": ("LOSS", "Manual early exit (loss)"),
    "be":         ("BE",   "Breakeven"),
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STORAGE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def load_journal() -> list:
    if not os.path.exists(JOURNAL_FILE):
        return []
    try:
        with open(JOURNAL_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_journal(trades: list):
    with open(JOURNAL_FILE, "w", encoding="utf-8") as f:
        json.dump(trades, f, indent=2, ensure_ascii=False)


def next_id(trades: list) -> int:
    return max((t.get("id", 0) for t in trades), default=0) + 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LOG A TRADE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_log(args: list):
    if len(args) < 9:
        print("Usage: journal log SYMBOL DIRECTION ENTRY SL TP1 TP2 GRADE SCORE OUTCOME [NOTE]")
        print("Example: journal log SOLUSDT LONG 145.5 140 156 165 B 7 win_tp1")
        sys.exit(1)

    symbol    = args[0].upper()
    direction = args[1].upper()
    outcome   = args[9].lower() if len(args) > 9 else args[8].lower()
    note      = " ".join(args[10:]) if len(args) > 10 else ""

    # Reorder: SYMBOL DIR ENTRY SL TP1 TP2 GRADE SCORE OUTCOME [NOTE]
    try:
        entry = float(args[2])
        sl    = float(args[3])
        tp1   = float(args[4])
        tp2   = float(args[5])
        grade = args[6].upper()
        score = int(args[7])
        outcome_key = args[8].lower()
        note  = " ".join(args[9:]) if len(args) > 9 else ""
    except (ValueError, IndexError) as e:
        print(f"Parse error: {e}")
        print("Usage: journal log SYMBOL DIRECTION ENTRY SL TP1 TP2 GRADE SCORE OUTCOME [NOTE]")
        sys.exit(1)

    if direction not in ("LONG", "SHORT"):
        print(f"DIRECTION must be LONG or SHORT. Got: {direction}")
        sys.exit(1)
    if grade not in ("A", "B", "C"):
        print(f"GRADE must be A, B, or C. Got: {grade}")
        sys.exit(1)
    if not 0 <= score <= 10:
        print(f"SCORE must be 0–10. Got: {score}")
        sys.exit(1)
    if outcome_key not in VALID_OUTCOMES:
        print(f"OUTCOME must be one of: {', '.join(VALID_OUTCOMES)}")
        sys.exit(1)

    result, desc = VALID_OUTCOMES[outcome_key]

    # Calculate achieved RR
    sl_dist = abs(entry - sl)
    if direction == "LONG":
        if result == "WIN":
            if "tp3" in outcome_key:
                tp_used = tp2   # approximation
            elif "tp2" in outcome_key:
                tp_used = tp2
            else:
                tp_used = tp1
            rr_achieved = (tp_used - entry) / sl_dist if sl_dist > 0 else 0
        elif result == "LOSS":
            rr_achieved = -(sl - entry) / sl_dist if sl_dist > 0 else -1.0
            rr_achieved = max(rr_achieved, -1.0)
        else:
            rr_achieved = 0.0
    else:
        if result == "WIN":
            tp_used = tp1 if "tp1" in outcome_key else tp2
            rr_achieved = (entry - tp_used) / sl_dist if sl_dist > 0 else 0
        elif result == "LOSS":
            rr_achieved = -(entry - sl) / sl_dist if sl_dist > 0 else -1.0
            rr_achieved = max(rr_achieved, -1.0)
        else:
            rr_achieved = 0.0

    # Compliance check: was this a system-compliant trade?
    compliant = grade in ("A", "B") and score >= 6
    violation = None
    if grade == "C" or score < 6:
        violation = f"Grade C or score {score}/10 taken — below minimum threshold"

    trades = load_journal()
    trade = {
        "id":          next_id(trades),
        "timestamp":   datetime.now().strftime("%Y-%m-%d %H:%M"),
        "symbol":      symbol,
        "direction":   direction,
        "entry":       entry,
        "sl":          sl,
        "tp1":         tp1,
        "tp2":         tp2,
        "grade":       grade,
        "score":       score,
        "outcome":     outcome_key,
        "result":      result,
        "rr_achieved": round(rr_achieved, 2),
        "compliant":   compliant,
        "violation":   violation,
        "note":        note,
    }
    trades.append(trade)
    save_journal(trades)

    result_emoji = "🟢" if result == "WIN" else ("🔴" if result == "LOSS" else "🟡")
    print(f"\n  ✅ Trade #{trade['id']} logged")
    print(f"  {result_emoji} {symbol} {direction} | Grade {grade} | Score {score}/10")
    print(f"  Outcome: {desc} | RR: {rr_achieved:+.2f}")
    if violation:
        print(f"  ⚠️  RULE VIOLATION: {violation}")
    if not compliant:
        print(f"  ❌ Non-compliant trade recorded. Track this pattern.")

    tg = (f"📓 TRADE LOGGED #{trade['id']}\n"
          f"{result_emoji} {symbol} {direction} | Grade {grade} | Score {score}/10\n"
          f"Entry: {entry} | SL: {sl} | TP1: {tp1}\n"
          f"Outcome: {desc} | RR: {rr_achieved:+.2f}\n"
          + (f"⚠️ VIOLATION: {violation}" if violation else "✅ Compliant"))
    send_telegram(tg)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STATISTICS ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def compute_stats(trades: list) -> dict:
    if not trades:
        return {}

    total      = len(trades)
    wins       = [t for t in trades if t["result"] == "WIN"]
    losses     = [t for t in trades if t["result"] == "LOSS"]
    bes        = [t for t in trades if t["result"] == "BE"]
    compliant  = [t for t in trades if t["compliant"]]
    violations = [t for t in trades if not t["compliant"]]
    rrs        = [t["rr_achieved"] for t in trades if t["rr_achieved"] is not None]

    win_rate      = len(wins) / total * 100 if total else 0
    compliance    = len(compliant) / total * 100 if total else 0
    avg_rr        = sum(rrs) / len(rrs) if rrs else 0
    avg_win_rr    = sum(t["rr_achieved"] for t in wins) / len(wins) if wins else 0
    avg_loss_rr   = sum(t["rr_achieved"] for t in losses) / len(losses) if losses else 0

    # Expectancy: E = (Win% × avg_win_RR) + (Loss% × avg_loss_RR)
    loss_rate = len(losses) / total if total else 0
    win_rate_dec = len(wins) / total if total else 0
    expectancy = (win_rate_dec * avg_win_rr) + (loss_rate * avg_loss_rr)

    # Streak
    max_loss_streak = 0
    cur_streak = 0
    for t in trades:
        if t["result"] == "LOSS":
            cur_streak += 1
            max_loss_streak = max(max_loss_streak, cur_streak)
        else:
            cur_streak = 0

    # Grade distribution
    grade_counts = {"A": 0, "B": 0, "C": 0}
    for t in trades:
        grade_counts[t.get("grade", "C")] = grade_counts.get(t.get("grade", "C"), 0) + 1

    return {
        "total":           total,
        "wins":            len(wins),
        "losses":          len(losses),
        "bes":             len(bes),
        "win_rate":        win_rate,
        "compliance":      compliance,
        "violations":      len(violations),
        "avg_rr":          avg_rr,
        "avg_win_rr":      avg_win_rr,
        "avg_loss_rr":     avg_loss_rr,
        "expectancy":      expectancy,
        "max_loss_streak": max_loss_streak,
        "grade_counts":    grade_counts,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# REVIEW COMMANDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_stats(trades: list, label: str = "ALL-TIME"):
    s = compute_stats(trades)
    if not s:
        print(f"  No trades in {label} window.")
        return

    comp_icon   = "✅" if s["compliance"] >= 80 else "⚠️"
    expect_icon = "✅" if s["expectancy"] > 0 else "❌"
    wr_icon     = "✅" if s["win_rate"] >= 50 else "⚠️"

    print(f"\n{'═'*55}")
    print(f"  📊 TRADING STATS — {label}")
    print(f"{'═'*55}")
    print(f"\n  Total Trades    : {s['total']}")
    print(f"  {wr_icon} Win Rate       : {s['win_rate']:.1f}%  ({s['wins']}W / {s['losses']}L / {s['bes']}BE)")
    print(f"  {expect_icon} Expectancy    : {s['expectancy']:+.2f}R per trade")
    print(f"  Avg Win RR      : {s['avg_win_rr']:+.2f}R")
    print(f"  Avg Loss RR     : {s['avg_loss_rr']:+.2f}R")
    print(f"  Max Loss Streak : {s['max_loss_streak']}")
    print(f"\n  {comp_icon} Compliance    : {s['compliance']:.1f}%  (target ≥ 80%)")
    print(f"  Rule Violations : {s['violations']}")
    print(f"\n  Grade Mix       : A={s['grade_counts']['A']}  B={s['grade_counts']['B']}  C={s['grade_counts']['C']}")

    if s["compliance"] < 80:
        print(f"\n  ⚠️  Compliance below 80%. Review which rules you broke most.")
    if s["expectancy"] <= 0 and s["total"] >= 10:
        print(f"\n  ❌ Negative expectancy. The system is not being executed correctly.")
        print(f"     Focus on compliance before increasing trade frequency.")
    if s["max_loss_streak"] >= 3:
        print(f"\n  ⚠️  Max 3-loss streak triggered at least once. Did you observe the 24h cooldown rule?")


def cmd_review(trades: list):
    """Weekly review: last 7 days."""
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    week_trades = [
        t for t in trades
        if datetime.strptime(t["timestamp"], "%Y-%m-%d %H:%M") >= week_ago
    ]

    print(f"\n{'═'*55}")
    print(f"  📋 WEEKLY REVIEW  —  {week_ago.strftime('%b %d')} to {now.strftime('%b %d')}")
    print(f"{'═'*55}")

    if not week_trades:
        print("  No trades this week.")
        return

    cmd_stats(week_trades, label="THIS WEEK")

    # Violations this week
    violations = [t for t in week_trades if not t["compliant"]]
    if violations:
        print(f"\n  RULE VIOLATIONS THIS WEEK")
        for t in violations:
            print(f"  ⚠️  #{t['id']} {t['symbol']} {t['direction']} — {t.get('violation', 'Unknown')}")

    # Best and worst trade
    if week_trades:
        best  = max(week_trades, key=lambda x: x["rr_achieved"])
        worst = min(week_trades, key=lambda x: x["rr_achieved"])
        print(f"\n  BEST TRADE  : #{best['id']} {best['symbol']} {best['direction']} | RR {best['rr_achieved']:+.2f}")
        print(f"  WORST TRADE : #{worst['id']} {worst['symbol']} {worst['direction']} | RR {worst['rr_achieved']:+.2f}")

    print(f"\n  REVIEW QUESTIONS")
    print(f"  1. Did you follow every AI signal exactly? (Target: ≥80% compliance)")
    print(f"  2. Did you move any stop-loss to give the trade room?")
    print(f"  3. Did you take any Grade C setups?")
    print(f"  4. Did you enter during Asian session or after midnight?")
    print(f"  5. Did you revenge-trade after a loss?")
    print(f"  6. Did you wait for the FVG/OB retest or did you chase breakouts?")

    tg_lines = [
        f"📋 WEEKLY REVIEW",
        f"Trades: {len(week_trades)} | "
        + (f"W/L/BE: {sum(1 for t in week_trades if t['result']=='WIN')}/"
           f"{sum(1 for t in week_trades if t['result']=='LOSS')}/"
           f"{sum(1 for t in week_trades if t['result']=='BE')}"),
    ]
    s = compute_stats(week_trades)
    if s:
        tg_lines.append(f"Win Rate: {s['win_rate']:.1f}% | Expectancy: {s['expectancy']:+.2f}R")
        tg_lines.append(f"Compliance: {s['compliance']:.1f}% | Violations: {s['violations']}")
    if violations:
        tg_lines.append(f"⚠️ {len(violations)} rule violation(s) this week")
    send_telegram("\n".join(tg_lines))


def cmd_list(trades: list, n: int = 10):
    """Print last N trades."""
    recent = trades[-n:]
    print(f"\n  {'#':<5} {'Date':<18} {'Symbol':<12} {'Dir':<6} {'Grade':<6} {'Score':<7} {'RR':>6} {'Result':<12} {'Note'}")
    print(f"  {'─'*90}")
    for t in reversed(recent):
        r_emoji = "🟢" if t["result"] == "WIN" else ("🔴" if t["result"] == "LOSS" else "🟡")
        comp = "" if t["compliant"] else " ⚠️"
        note = t.get("note", "")[:25]
        print(f"  {t['id']:<5} {t['timestamp']:<18} {t['symbol']:<12} {t['direction']:<6} "
              f"{t['grade']:<6} {t['score']}/10  {t['rr_achieved']:>+6.2f}R "
              f"{r_emoji} {t['result']:<8}{comp}  {note}")


def cmd_delete(trades: list, trade_id: int) -> list:
    original_len = len(trades)
    trades = [t for t in trades if t.get("id") != trade_id]
    if len(trades) < original_len:
        print(f"  ✅ Trade #{trade_id} removed.")
    else:
        print(f"  ⚠️  Trade #{trade_id} not found.")
    return trades


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    args    = sys.argv[1:]
    command = args[0].lower() if args else "help"

    trades = load_journal()

    if command == "log":
        cmd_log(args[1:])

    elif command == "review":
        cmd_review(trades)

    elif command == "stats":
        cmd_stats(trades)

    elif command == "list":
        n = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
        print(f"\n  LAST {n} TRADES")
        cmd_list(trades, n)

    elif command == "delete":
        if len(args) < 2 or not args[1].isdigit():
            print("Usage: journal delete ID")
            sys.exit(1)
        trades = cmd_delete(trades, int(args[1]))
        save_journal(trades)

    else:
        print("""
skill_journal.py — Trade Logger & Review Tool

Commands:
  log SYMBOL DIR ENTRY SL TP1 TP2 GRADE SCORE OUTCOME [NOTE]
      → Log a completed trade
      Outcomes: win_tp1 win_tp2 win_tp3 win_early loss_sl loss_early be

  list [N]    → Show last N trades (default 10)
  review      → Weekly review (last 7 days) with compliance check
  stats       → All-time stats and expectancy
  delete ID   → Remove a trade by ID

Examples:
  python skill_journal.py log SOLUSDT LONG 145.5 140 156 165 B 7 win_tp1
  python skill_journal.py log BTCUSDT SHORT 65000 66000 63000 61500 A 9 loss_sl "news spike"
  python skill_journal.py list 20
  python skill_journal.py review
  python skill_journal.py stats
""")


if __name__ == "__main__":
    main()
