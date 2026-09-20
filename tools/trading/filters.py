"""Market-wide candidate filters shared by the scanner and hunter pipelines.

Hand-rolled float parsing keeps malformed ticker rows from crashing the scan,
and both pipelines fall back to relaxed thresholds when fewer than 5 coins pass
the strict screen.
"""

from __future__ import annotations

from typing import Any

from .config import EXCLUDE_EXACT, EXCLUDE_SUBS

_VOL_FLOOR = 100_000_000  # $100M minimum 24H quote volume


def _clean(ip: Any) -> float:
    """Parse a ticker field defensively; raises ValueError on garbage."""
    value = float(ip)
    return value


# ── Scanner pipeline ──────────────────────────────────────────────────────────

def scanner_candidates(tickers: list[dict]) -> tuple[list[dict], int]:
    """Volume/range/change screen ranked by absolute 24H move.

    Strict: vol > $100M, range > 10%, |change| > 3%.
    Relaxed (if fewer than 5): range > 7%.

    Returns ``(candidates, total_matched)`` sorted by ``absChange`` desc.
    """
    def _pass(range_min: float) -> list[dict]:
        out = []
        for t in tickers:
            sym = t.get("symbol", "")
            if any(sub in sym for sub in EXCLUDE_SUBS):
                continue
            if sym in EXCLUDE_EXACT:
                continue
            try:
                lo = _clean(t["lowPrice"])
                if lo == 0:
                    continue
                rng = (_clean(t["highPrice"]) - lo) / lo * 100
                ac = abs(_clean(t["priceChangePercent"]))
                if (
                    _clean(t["quoteVolume"]) > _VOL_FLOOR
                    and rng > range_min
                    and ac > 3
                ):
                    out.append({
                        "symbol": sym,
                        "priceChangePercent": _clean(t["priceChangePercent"]),
                        "quoteVolume": _clean(t["quoteVolume"]),
                        "rangePercent": rng,
                        "absChange": ac,
                        "lastPrice": _clean(t["lastPrice"]),
                    })
            except (KeyError, TypeError, ValueError, ZeroDivisionError):
                continue
        return out

    filtered = _pass(10.0)
    if len(filtered) < 5:
        filtered = _pass(7.0)

    filtered.sort(key=lambda x: x["absChange"], reverse=True)
    return filtered, len(filtered)


# ── Hunter pipeline ───────────────────────────────────────────────────────────

def hunter_candidates(tickers: list[dict]) -> tuple[list[dict], bool]:
    """Pre-breakout screen ranked by 24H quote volume.

    Strict: vol > $100M, 3 < range < 25%, |change| < 15%.
    Relaxed (if fewer than 5): range ceiling lifted to 30%.

    Returns ``(candidates, relaxed)``.
    """
    def _pass(range_max: float) -> list[dict]:
        out = []
        for t in tickers:
            sym = t.get("symbol", "")
            if any(sub in sym for sub in EXCLUDE_SUBS):
                continue
            if sym in EXCLUDE_EXACT:
                continue
            try:
                lo = _clean(t["lowPrice"])
                lp = _clean(t["lastPrice"])
                if lo <= 0 or lp <= 0:
                    continue
                rng = (_clean(t["highPrice"]) - lo) / lo * 100
                ac = abs(_clean(t["priceChangePercent"]))
                if _clean(t["quoteVolume"]) > _VOL_FLOOR and 3 < rng < range_max and ac < 15:
                    out.append({
                        "symbol": sym,
                        "quoteVolume": _clean(t["quoteVolume"]),
                        "lastPrice": lp,
                        "pctChange": _clean(t["priceChangePercent"]),
                        "range24h": rng,
                        "absChange": ac,
                    })
            except (KeyError, TypeError, ValueError, ZeroDivisionError):
                continue
        return out

    candidates = _pass(25.0)
    relaxed = False
    if len(candidates) < 5:
        candidates = _pass(30.0)
        relaxed = True

    candidates.sort(key=lambda x: x["quoteVolume"], reverse=True)
    return candidates, relaxed