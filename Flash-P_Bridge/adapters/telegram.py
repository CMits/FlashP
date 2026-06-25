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
    callback_id: str | None = None   # set when this came from an inline-keyboard tap


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


def send_message(token: str, chat_id, text: str, reply_markup: dict | None = None) -> bool:
    payload = {"chat_id": chat_id, "text": text[:4096]}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        r = requests.post(_API.format(token=token, method="sendMessage"), json=payload, timeout=30)
        return r.status_code < 300
    except requests.RequestException:
        return False


def send_photo(token: str, chat_id, path: str, caption: str = "") -> bool:
    try:
        with open(path, "rb") as fh:
            r = requests.post(
                _API.format(token=token, method="sendPhoto"),
                data={"chat_id": chat_id, "caption": caption[:1024]},
                files={"photo": fh}, timeout=60,
            )
        return r.status_code < 300
    except (requests.RequestException, OSError):
        return False


def send_document(token: str, chat_id, path: str, caption: str = "") -> bool:
    try:
        with open(path, "rb") as fh:
            r = requests.post(
                _API.format(token=token, method="sendDocument"),
                data={"chat_id": chat_id, "caption": caption[:1024]},
                files={"document": fh}, timeout=60,
            )
        return r.status_code < 300
    except (requests.RequestException, OSError):
        return False


def set_my_commands(token: str, commands: list[dict]) -> bool:
    """commands = [{'command': 'gxe', 'description': '...'}, ...] — populates the / menu."""
    try:
        r = requests.post(_API.format(token=token, method="setMyCommands"),
                          json={"commands": commands}, timeout=15)
        return r.status_code < 300
    except requests.RequestException:
        return False


def answer_callback_query(token: str, callback_id: str, text: str = "") -> bool:
    try:
        r = requests.post(_API.format(token=token, method="answerCallbackQuery"),
                          json={"callback_query_id": callback_id, "text": text}, timeout=15)
        return r.status_code < 300
    except requests.RequestException:
        return False


def inline_keyboard(buttons: list[tuple[str, str]], columns: int = 2) -> dict:
    """buttons = [(label, callback_data), ...] -> a reply_markup with `columns` per row."""
    rows, row = [], []
    for label, data in buttons:
        row.append({"text": label, "callback_data": data[:64]})
        if len(row) == columns:
            rows.append(row); row = []
    if row:
        rows.append(row)
    return {"inline_keyboard": rows}


def _name(frm: dict) -> str:
    return " ".join(filter(None, [frm.get("first_name"), frm.get("last_name")])) or frm.get("username") or "someone"


def parse_update(update: dict) -> IncomingMessage | None:
    """Normalize a text message OR an inline-keyboard tap into one IncomingMessage."""
    cq = update.get("callback_query")
    if cq:
        msg = cq.get("message") or {}
        frm = cq.get("from") or {}
        return IncomingMessage(
            text=cq.get("data", ""), chat_id=(msg.get("chat") or {}).get("id"),
            sender_id=frm.get("id"), sender_username=(frm.get("username") or ""),
            sender_name=_name(frm), callback_id=cq.get("id"),
        )
    msg = update.get("message") or update.get("edited_message")
    if not msg or not msg.get("text"):
        return None
    frm = msg.get("from") or {}
    return IncomingMessage(
        text=msg["text"], chat_id=(msg.get("chat") or {}).get("id"),
        sender_id=frm.get("id"), sender_username=(frm.get("username") or ""),
        sender_name=_name(frm),
    )
