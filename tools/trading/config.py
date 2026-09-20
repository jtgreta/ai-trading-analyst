"""Runtime configuration: account defaults, tool rules, and environment loading.

All values can be overridden at runtime through ``config/trading.json`` (capital,
max risk, minimum RR, per-token sizing rules) and ``.env`` (Telegram credentials).

The defaults below are loaded once at import time; engines import the resolved
``CAPITAL``, ``MAX_RISK``, ``MIN_RR``, ``SCALP_RULES`` and ``SWING_RULES`` from
this module instead of re-declaring their own copies.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# ── Binance Futures API ───────────────────────────────────────────────────────
BINANCE_FUTURES: str = "https://fapi.binance.com/fapi/v1"

# ── Exchange universe filters ─────────────────────────────────────────────────
# Stablecoin-collateral perpetuals are excluded to avoid stablecoin pairs.
EXCLUDE_SUBS: list[str] = ["USDC", "BUSD", "TUSD", "DAI", "FDUSD"]
EXCLUDE_EXACT: set[str] = {"BTCDOMUSDT", "DEFIUSDT", "ALTUSDT"}

# Tokens classed as "major" regardless of 24H quote volume.
MAJOR_SYMBOLS: set[str] = {"BTCUSDT", "ETHUSDT", "BNBUSDT"}

# ── Account defaults (overridden by config/trading.json) ──────────────────────
CAPITAL: float = 100.0
MAX_RISK: float = 4.0          # hard max dollar risk per trade
MIN_RR: float = 2.0            # minimum risk:reward (TP1 >= 2x SL distance)

# Token type -> (leverage, full margin, max stop % as a fraction).
# Labels are shared by both planning and output modules.
_SCALP_RULES: dict[str, dict[str, Any]] = {
    "major":  {"lev": 10, "margin": 10, "max_sl": 0.030, "label": "BTC/ETH/BNB"},
    "midcap": {"lev":  5, "margin":  7, "max_sl": 0.085, "label": "Mid-cap"},
    "new":    {"lev":  3, "margin":  5, "max_sl": 0.200, "label": "New/Meme/AI"},
}
_SWING_RULES: dict[str, dict[str, Any]] = {
    "major":  {"lev":  5, "margin": 10, "max_sl": 0.060, "label": "BTC/ETH/BNB"},
    "midcap": {"lev":  3, "margin":  7, "max_sl": 0.140, "label": "Mid-cap"},
    "new":    {"lev":  2, "margin":  5, "max_sl": 0.300, "label": "New/Meme/AI"},
}


def repo_root() -> Path:
    """Absolute path to the repository root (parent of the ``tools/`` dir)."""
    return Path(__file__).resolve().parent.parent.parent


def _load_json_overlay() -> dict[str, Any]:
    """Load the optional ``config/trading.json`` overlay (silently on failure)."""
    path = repo_root() / "config" / "trading.json"
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _load_env() -> None:
    """Import ``.env`` key/value pairs as environment defaults (no overwrite)."""
    path = repo_root() / ".env"
    if not path.exists():
        return
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'").strip('"'))


def _apply_rule_overrides(rules: dict[str, dict[str, Any]], overlay: Any) -> None:
    """Merge per-token sizing overrides from the JSON config into *rules*."""
    if not isinstance(overlay, dict):
        return
    for token_name, override in overlay.items():
        if token_name in rules and isinstance(override, dict):
            for key, value in override.items():
                if value is not None:
                    rules[token_name][key] = value


def load_env() -> None:
    """Public wrapper around :func:`_load_env` for modules that import late."""
    _load_env()


# ── Apply user overrides at import time ───────────────────────────────────────
_load_env()
_overlay = _load_json_overlay()

if _overlay.get("capital"):
    CAPITAL = float(_overlay["capital"])
if _overlay.get("max_risk"):
    MAX_RISK = float(_overlay["max_risk"])
if _overlay.get("min_rr"):
    MIN_RR = float(_overlay["min_rr"])

SCALP_RULES: dict[str, dict[str, Any]] = _SCALP_RULES
SWING_RULES: dict[str, dict[str, Any]] = _SWING_RULES
_apply_rule_overrides(SCALP_RULES, _overlay.get("scalp_rules"))
_apply_rule_overrides(SWING_RULES, _overlay.get("swing_rules"))

# Telegram credentials (empty -> dispatch is skipped by telegram.send_telegram).
TG_TOKEN: str = os.environ.get("TG_TOKEN", "")
TG_CHAT: str = os.environ.get("TG_CHAT", "")