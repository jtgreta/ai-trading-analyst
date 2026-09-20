"""Journal persistence (load/save of ``journal.json`` at the repo root)."""

from __future__ import annotations

import json
import os

from .config import repo_root

JOURNAL_FILE = os.path.join(repo_root(), "journal.json")


def load_journal() -> list:
    """Load the trade journal; returns ``[]`` when absent or corrupt."""
    if not os.path.exists(JOURNAL_FILE):
        return []
    try:
        with open(JOURNAL_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def save_journal(trades: list) -> None:
    """Persist the trade journal."""
    with open(JOURNAL_FILE, "w", encoding="utf-8") as f:
        json.dump(trades, f, indent=2, ensure_ascii=False)


def next_id(trades: list) -> int:
    """Next sequential trade id."""
    return max((t.get("id", 0) for t in trades), default=0) + 1