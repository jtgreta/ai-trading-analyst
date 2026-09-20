"""Session timing in PHT (UTC+8), driving volatility context and aggression.

The clock never blocks a trade — it only sets the minimum grade window context.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from typing import Any

PHT = timezone(timedelta(hours=8))

# Window lookup table: (start_min, end_min) -> (window name, volatility, advice)
_WINDOWS: list[tuple[int, int, dict[str, str]]] = [
    (900, 1020, {
        "window": "London Open",
        "volatility": "🟢 High",
        "aggression": "Maximum",
        "advice": "Prime Window. High probability of impulsive, trending moves.",
        "min_grade": "B",
    }),
    (1020, 1260, {
        "window": "London-NY Gap",
        "volatility": "🟡 Moderate",
        "aggression": "Moderate",
        "advice": "Secondary Window. Favor setups with clear structural alignment.",
        "min_grade": "B",
    }),
    (1260, 1380, {
        "window": "NY Overlap",
        "volatility": "🟢 High",
        "aggression": "Maximum",
        "advice": "Prime Window. Maximum liquidity and volume.",
        "min_grade": "B",
    }),
    (480, 720, {
        "window": "Asian Session",
        "volatility": "🟡 Low",
        "aggression": "Conservative",
        "advice": "Low-Vol Window. Favor Grade A setups. Higher risk of chop.",
        "min_grade": "A",
    }),
]
_OFF_HOURS = {
    "window": "Off-hours",
    "volatility": "🟡 Low",
    "aggression": "Conservative",
    "advice": "Low-Vol Window. High risk of fakeouts. Favor Grade A setups.",
    "min_grade": "A",
}


def get_session_info() -> dict[str, Any]:
    """Current PHT session context (window, volatility, aggression, advice)."""
    now = datetime.now(PHT)
    t = now.hour * 60 + now.minute
    time_str = now.strftime("%Y-%m-%d %H:%M PHT")
    info = _OFF_HOURS
    for start, end, window in _WINDOWS:
        if start <= t < end:
            info = window
            break
    return {
        "time_str": time_str,
        "window": info["window"],
        "volatility": info["volatility"],
        "aggression": info["aggression"],
        "advice": info["advice"],
        "can_enter": True,
        "min_grade": info["min_grade"],
    }


def get_next_session_window() -> str:
    """Human-readable next prime window to check back."""
    now = datetime.now(PHT)
    h = now.hour
    if h < 15:
        return "3:00 PM PHT — London open"
    if h < 21:
        return "9:30 PM PHT — London–NY overlap opens"
    return "3:00 PM PHT tomorrow — London open"