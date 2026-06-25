"""Telegram adapter for the FLASH-P bridge.

The simplest, safest transport: the bot **long-polls** Telegram (outbound HTTPS only),
so the host needs no tunnel, no public endpoint, and no inbound port. There is no
reply-time limit, so the ack and the (minutes-later) result are both just `sendMessage`.

Pure Telegram glue — verify nothing inbound, parse updates, send messages. The
platform-agnostic core (command_map / runner / job_queue) is untouched.
"""
from __future__ import annotations

from dataclasses import dataclass

import requests

_API = "https://api.telegram.org/bot{token}/{method}"


@dataclass
class IncomingMessage:
    text: str
    chat_id: int
    sender_id: int
    sender_username: str       # without leading '@' (may be empty)
    sender_name: str           # display name for messages


def get_me(token: str) -> dict:
    """Validate the bot token; returns Telegram's getMe response."""
    r = requests.get(_API.format(token=token, method="getMe"), timeout=15)
    return r.json()


def get_updates(token: str, offset: int | None = None, timeout: int = 30) -> list[dict]:
    """Long-poll for new updates (blocks up to `timeout` seconds server-side)."""
    params: dict = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    r = requests.get(_API.format(token=token, method="getUpdates"), params=params, timeout=timeout + 15)
    r.raise_for_status()
    return r.json().get("result", [])


def send_message(token: str, chat_id, text: str) -> bool:
    try:
        r = requests.post(
            _API.format(token=token, method="sendMessage"),
            json={"chat_id": chat_id, "text": text[:4096]},
            timeout=30,
        )
        return r.status_code < 300
    except requests.RequestException:
        return False


def parse_update(update: dict) -> IncomingMessage | None:
    """Extract a text message from an update; returns None for non-text/non-message updates."""
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return None
    text = msg.get("text")
    if not text:
        return None
    frm = msg.get("from") or {}
    chat = msg.get("chat") or {}
    name = " ".join(filter(None, [frm.get("first_name"), frm.get("last_name")])) or frm.get("username") or "someone"
    return IncomingMessage(
        text=text,
        chat_id=chat.get("id"),
        sender_id=frm.get("id"),
        sender_username=(frm.get("username") or ""),
        sender_name=name,
    )
