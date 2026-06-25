"""Microsoft Teams adapter for the FLASH-P bridge.

Teams delivers an @mention via an **Outgoing Webhook**: an HMAC-signed POST that
expects a JSON reply within ~5 seconds. Long results are posted back later,
asynchronously, via a **Power Automate Workflow** URL (the 2026 replacement for
the retired Office 365 incoming-webhook connectors).

This module is pure Teams glue — verify, parse, format, post. The platform-agnostic
core (command_map / runner / job_queue) knows nothing about Teams.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
from dataclasses import dataclass

import requests


@dataclass
class IncomingMention:
    text: str                 # raw message text (may contain <at>flash-p</at> markup)
    sender_aad: str           # from.aadObjectId (lowercased) — the allowlist key
    sender_name: str          # from.name — for display


def verify_hmac(raw_body: bytes, auth_header: str, b64_token: str) -> bool:
    """Validate the Teams `Authorization: HMAC <sig>` header against the raw body.

    Teams signs with HMAC-SHA256 using the base64-decoded security token shown when
    the outgoing webhook is created.
    """
    if not auth_header or not b64_token:
        return False
    provided = auth_header.split(" ", 1)[1].strip() if " " in auth_header else auth_header.strip()
    try:
        key = base64.b64decode(b64_token)
    except (ValueError, TypeError):
        return False
    digest = hmac.new(key, raw_body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode()
    return hmac.compare_digest(expected, provided)


def parse_mention(payload: dict) -> IncomingMention:
    frm = payload.get("from") or {}
    return IncomingMention(
        text=payload.get("text", ""),
        sender_aad=str(frm.get("aadObjectId", "")).strip().lower(),
        sender_name=str(frm.get("name", "") or "someone"),
    )


def ack(text: str) -> dict:
    """Synchronous reply body Teams renders in-thread (must return within ~5s)."""
    return {"type": "message", "text": text}


def post_result(workflow_url: str, text: str) -> bool:
    """Post an async result card back to the channel via the Power Automate workflow."""
    if not workflow_url:
        return False
    card = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "type": "AdaptiveCard",
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "version": "1.4",
                    "body": [{"type": "TextBlock", "text": text, "wrap": True}],
                },
            }
        ],
    }
    try:
        resp = requests.post(workflow_url, json=card, timeout=30)
        return resp.status_code < 300
    except requests.RequestException:
        return False
