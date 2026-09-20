"""Token classification and dynamic position sizing.

Grade A setups trade at the token's full margin; Grade B trades at half margin.
Computed risk is never allowed to exceed the configured ``MAX_RISK`` cap — when
it would, margin is shrunk to fit.
"""

from __future__ import annotations

from typing import Any

from .config import MAJOR_SYMBOLS, MAX_RISK, SCALP_RULES, SWING_RULES

_MIDCAP_VOLUME_FLOOR = 500_000_000  # 24H quote volume separating midcap from new


def classify_token(symbol: str, quote_vol: float) -> str:
    """Return ``major`` / ``midcap`` / ``new`` for a symbol."""
    if symbol in MAJOR_SYMBOLS:
        return "major"
    if quote_vol > _MIDCAP_VOLUME_FLOOR:
        return "midcap"
    return "new"


def calc_position(
    tok_type: str,
    sl_pct: float,
    mode: str = "scalp",
    setup_grade: str = "B",
) -> dict[str, Any]:
    """Position sizing for a trade.

    Args:
        tok_type: token class from :func:`classify_token`.
        sl_pct: stop distance as a fraction of entry price.
        mode: ``scalp`` or ``swing`` (selects the rule table).
        setup_grade: ``A`` (full), ``B`` (half), ``C`` (blocked -> handled as
            WAITING ROOM by the calling skill).

    Returns:
        A dict with leverage, margin, position notional, dollar risk and label.
    """
    rules = SCALP_RULES if mode == "scalp" else SWING_RULES
    base = rules[tok_type]

    # A = 100%, B = 50%, C = 0% (C never reaches here in practice).
    grade_mult = {"A": 1.0, "B": 0.50, "C": 0.0}.get(setup_grade, 0.50)

    margin = round(base["margin"] * grade_mult, 2)
    lev = base["lev"]
    position = round(margin * lev, 2)
    risk = round(position * sl_pct, 2)

    # Hard risk cap: shrink margin so risk never exceeds MAX_RISK.
    if risk > MAX_RISK:
        margin = round(MAX_RISK / (lev * sl_pct), 2)
        position = round(margin * lev, 2)
        risk = round(position * sl_pct, 2)

    return {
        "lev": lev,
        "margin": margin,
        "position": position,
        "risk": risk,
        "label": base["label"],
        "grade": setup_grade,
    }