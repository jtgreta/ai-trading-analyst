"""Trading toolkit — shared runtime for the ai-trading-analyst script suite.

Public API mirrors the former ``trading_utils.py`` module so calling scripts can
import everything from a single namespace root::

    from trading import fetch_klines, get_session_info, calc_position, ...
"""

from __future__ import annotations

# ── Config / environment ──────────────────────────────────────────────────────
from .config import (
    BINANCE_FUTURES,
    CAPITAL,
    EXCLUDE_EXACT,
    EXCLUDE_SUBS,
    MAJOR_SYMBOLS,
    MAX_RISK,
    MIN_RR,
    SCALP_RULES,
    SWING_RULES,
    TG_CHAT,
    TG_TOKEN,
    repo_root,
)

# ── Binance API ───────────────────────────────────────────────────────────────
from .api import (
    fetch_all_funding_rates,
    fetch_all_tickers,
    fetch_depth,
    fetch_funding_rate,
    fetch_klines,
    fetch_ls_ratio,
    fetch_open_interest,
    fetch_ticker,
)

# ── Indicators ────────────────────────────────────────────────────────────────
from .indicators import (
    atr,
    calc_trail_callback_pct,
    detect_divergence,
    distance_pct,
    ema,
    ma_stack_label,
    macd,
    pct_from,
    rsi,
    sma,
)

# ── Smart Money Concepts ──────────────────────────────────────────────────────
from .smc import (
    calc_atr_stop,
    calc_atr_stop_swing,
    calculate_ote_zone,
    correlation_warning,
    detect_bos_choch,
    detect_fvg,
    detect_liquidity,
    detect_market_structure,
    detect_order_blocks,
    find_fvg,
    identify_inducement,
)

# ── Sizing ────────────────────────────────────────────────────────────────────
from .sizing import calc_position, classify_token

# ── Session timing ────────────────────────────────────────────────────────────
from .session import PHT, get_next_session_window, get_session_info

# ── Output / Telegram ─────────────────────────────────────────────────────────
from .output import (
    ensure_utf8,
    fmt,
    format_telegram_trade,
    format_telegram_waiting,
    grade_label,
    print_market_structure,
    print_session_check,
    print_trade_plan,
    print_waiting_room,
)
from .telegram import send_telegram

# ── Filters ───────────────────────────────────────────────────────────────────
from .filters import hunter_candidates, scanner_candidates

# ── Journal storage ───────────────────────────────────────────────────────────
from .store import JOURNAL_FILE, load_journal, next_id, save_journal

__all__ = [
    # config
    "BINANCE_FUTURES", "CAPITAL", "EXCLUDE_EXACT", "EXCLUDE_SUBS",
    "MAJOR_SYMBOLS", "MAX_RISK", "MIN_RR", "SCALP_RULES", "SWING_RULES",
    "TG_CHAT", "TG_TOKEN", "repo_root",
    # api
    "fetch_all_funding_rates", "fetch_all_tickers", "fetch_depth",
    "fetch_funding_rate", "fetch_klines", "fetch_ls_ratio",
    "fetch_open_interest", "fetch_ticker",
    # indicators
    "atr", "calc_trail_callback_pct", "detect_divergence", "distance_pct",
    "ema", "ma_stack_label", "macd", "pct_from", "rsi", "sma",
    # smc
    "calc_atr_stop", "calc_atr_stop_swing", "calculate_ote_zone",
    "correlation_warning", "detect_bos_choch", "detect_fvg",
    "detect_liquidity", "detect_market_structure", "detect_order_blocks",
    "find_fvg", "identify_inducement",
    # sizing
    "calc_position", "classify_token",
    # session
    "PHT", "get_next_session_window", "get_session_info",
    # output / telegram
    "ensure_utf8", "fmt", "format_telegram_trade", "format_telegram_waiting",
    "grade_label", "print_market_structure", "print_session_check",
    "print_trade_plan", "print_waiting_room", "send_telegram",
    # filters
    "hunter_candidates", "scanner_candidates",
    # store
    "JOURNAL_FILE", "load_journal", "next_id", "save_journal",
]