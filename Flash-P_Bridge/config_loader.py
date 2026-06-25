"""Load and validate the bridge operator config.

`config.json` lives next to this file and is gitignored (it holds the HMAC token,
the Power Automate URL, and the sender allowlist). `config.example.json` is the
committed template. All paths in the config are resolved relative to this folder
so the bridge can be launched from anywhere.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

BRIDGE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = BRIDGE_DIR / "config.json"


@dataclass
class ClaudeConfig:
    bin: str = "claude"
    engine: str = "claude"          # "claude" = run the real agent on the subscription; "python" = run the driver directly (no tokens, for testing)
    model: str = "sonnet"
    permission_mode: str = "dontAsk"
    settings_file: Path | None = None
    extra_args: list[str] = field(default_factory=list)
    timeout_seconds: int = 1800


@dataclass
class Config:
    host: str
    port: int
    project_dir: Path
    network_roots: list[Path]
    hmac_token: str
    workflow_url: str
    allowlist: list[dict[str, str]]
    telegram_bot_token: str
    telegram_allowlist: list[str]
    claude: ClaudeConfig
    commands: dict[str, str]
    raw: dict[str, Any]

    def allowed_aad_ids(self) -> set[str]:
        return {str(e.get("aadObjectId", "")).strip().lower() for e in self.allowlist if e.get("aadObjectId")}

    def allowed_names(self) -> set[str]:
        return {str(e.get("name", "")).strip().lower() for e in self.allowlist if e.get("name")}

    def is_allowed(self, aad: str, name: str) -> bool:
        """A sender is allowed if their Azure Object ID OR their display name is listed.

        aadObjectId is the robust key (stable, unique); display name is the easy one
        for onboarding a colleague ("just add their name").
        """
        return (aad or "").strip().lower() in self.allowed_aad_ids() or (name or "").strip().lower() in self.allowed_names()

    def is_allowed_telegram(self, user_id, username: str) -> bool:
        """Allowed if the Telegram numeric id OR @username is on the telegram allowlist.

        Entries may be written with or without a leading '@'. Empty allowlist => deny all.
        """
        allow = {str(a).strip().lstrip("@").lower() for a in self.telegram_allowlist if str(a).strip()}
        return str(user_id).strip().lower() in allow or (username or "").strip().lstrip("@").lower() in allow


def _resolve(base: Path, p: str) -> Path:
    candidate = Path(p)
    return candidate if candidate.is_absolute() else (base / candidate).resolve()


def load_config(path: Path | None = None) -> Config:
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not cfg_path.exists():
        raise FileNotFoundError(
            f"No config found at {cfg_path}. Copy config.example.json -> config.json and fill it in."
        )
    raw = json.loads(cfg_path.read_text(encoding="utf-8"))

    teams = raw.get("teams", {})
    tg = raw.get("telegram", {})
    c = raw.get("claude", {})
    settings_file = c.get("settings_file")
    claude = ClaudeConfig(
        bin=c.get("bin", "claude"),
        engine=c.get("engine", "claude"),
        model=c.get("model", "sonnet"),
        permission_mode=c.get("permission_mode", "dontAsk"),
        settings_file=_resolve(BRIDGE_DIR, settings_file) if settings_file else None,
        extra_args=list(c.get("extra_args", [])),
        timeout_seconds=int(c.get("timeout_seconds", 1800)),
    )

    return Config(
        host=raw.get("host", "127.0.0.1"),
        port=int(raw.get("port", 8787)),
        project_dir=_resolve(BRIDGE_DIR, raw["project_dir"]),
        network_roots=[_resolve(BRIDGE_DIR, r) for r in raw.get("network_roots", [])],
        hmac_token=teams.get("hmac_token", ""),
        workflow_url=teams.get("workflow_url", ""),
        allowlist=list(raw.get("allowlist", [])),
        telegram_bot_token=tg.get("bot_token", ""),
        telegram_allowlist=list(tg.get("allowlist", [])),
        claude=claude,
        commands=dict(raw.get("commands", {"gxe": "/run-flashp-gxe", "epistasis": "/run-flashp-epistasis"})),
        raw=raw,
    )
