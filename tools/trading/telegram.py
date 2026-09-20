"""Telegram dispatch (chat delivery of trade plans and WAITING ROOM summaries).

Credentials come from ``TG_TOKEN`` / ``TG_CHAT`` in ``.env``. If they are
unset, dispatch is skipped with a notice instead of silently failing.
"""

from __future__ import annotations

import requests

from .config import TG_CHAT, TG_TOKEN


def send_telegram(msg: str) -> None:
    """Send ``msg`` to the configured Telegram chat (max 4096 chars)."""
    if not TG_TOKEN or not TG_CHAT:
        print("  ⚠️  Telegram skipped: TG_TOKEN/TG_CHAT not configured")
        return
    try:
        if len(msg) > 4096:
            msg = msg[:4093] + "..."
        resp = requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            data={"chat_id": TG_CHAT, "text": msg},
            timeout=10,
        )
        resp.raise_for_status()
        print(f"  ✅ Telegram sent ({len(msg)} chars)")
    except Exception as exc:  # noqa: BLE001 - notification must never crash
        print(f"  ⚠️  Telegram failed: {exc}")