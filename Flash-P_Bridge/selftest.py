"""Local smoke test for the FLASH-P Teams bridge — no Teams required.

Posts synthetic, correctly-HMAC-signed Bot Framework payloads to a running listener
and checks the four code paths. Run `python listener.py` first.

It reads config.json to use the same HMAC token + an allowlisted sender, and picks a
real discovered network so the "valid trigger" path actually enqueues a job.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sys

import requests

import command_map
from config_loader import load_config

cfg = load_config()
URL = f"http://{cfg.host}:{cfg.port}/teams/webhook"


def _sign(body: bytes, b64_token: str) -> str:
    key = base64.b64decode(b64_token)
    return "HMAC " + base64.b64encode(hmac.new(key, body, hashlib.sha256).digest()).decode()


def _post(payload: dict, token: str) -> tuple[int, str]:
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "Authorization": _sign(body, token)}
    r = requests.post(URL, data=body, headers=headers, timeout=10)
    text = ""
    try:
        text = r.json().get("text", "")
    except Exception:
        text = r.text
    return r.status_code, text


def _payload(text: str, aad: str, name: str = "Tester") -> dict:
    return {"type": "message", "text": text, "from": {"id": "29:abc", "name": name, "aadObjectId": aad}}


def main() -> int:
    try:  # Windows consoles default to cp1252; the listener's replies contain emoji.
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if not cfg.hmac_token or cfg.hmac_token.startswith("PASTE"):
        print("✗ Set teams.hmac_token in config.json first.")
        return 1

    allowed = next(iter(cfg.allowed_aad_ids()), None)
    if not allowed:
        print("✗ Add at least one allowlist entry with an aadObjectId in config.json.")
        return 1

    nets = command_map.discover_networks(cfg.network_roots)
    if not nets:
        print("✗ No networks discovered under network_roots — check config paths.")
        return 1
    a_network = command_map.parse(f"gxe {sorted(nets)[0]}", cfg, nets).network_name
    print(f"Using network: {a_network}\n")

    checks = []

    # 1. Valid trigger from an allowlisted user → 200 + "Running"
    code, txt = _post(_payload(f"<at>flash-p</at> gxe {a_network}", allowed), cfg.hmac_token)
    checks.append(("valid trigger enqueues", code == 200 and "Running" in txt, f"{code}: {txt[:80]}"))

    # 2. Bad HMAC → 401
    body = json.dumps(_payload(f"gxe {a_network}", allowed)).encode()
    r = requests.post(URL, data=body, headers={"Authorization": "HMAC deadbeef"}, timeout=10)
    checks.append(("bad HMAC rejected", r.status_code == 401, str(r.status_code)))

    # 3. Non-allowlisted sender → 200 + "allowlist"
    code, txt = _post(_payload(f"gxe {a_network}", "11111111-2222-3333-4444-555555555555"), cfg.hmac_token)
    checks.append(("non-allowlisted blocked", "allowlist" in txt.lower(), f"{code}: {txt[:80]}"))

    # 4. Unknown command → 200 + usage
    code, txt = _post(_payload("frobnicate everything", allowed), cfg.hmac_token)
    checks.append(("bad command → usage", "usage" in txt.lower() or "unknown" in txt.lower(), f"{code}: {txt[:80]}"))

    print("Results:")
    ok = True
    for name, passed, detail in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}  --  {detail}")
        ok = ok and passed
    print("\n" + ("ALL PASSED" if ok else "SOME FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
