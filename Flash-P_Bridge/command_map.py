"""Parse an `@flash-p ...` message into a safe, allowlisted FLASH-P command.

This is the PRIMARY security layer of the bridge: only two verbs (`gxe`,
`epistasis`) and only networks discovered under the configured roots can ever
become a command. Free-form text never reaches the agent — we hand Claude Code a
fixed slash command (`/run-flashp-gxe <network-dir>`), nothing else.

Platform-agnostic: adapters normalize their payload to a plain mention string and
call `parse()`. Telegram/Slack adapters reuse this unchanged.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from config_loader import Config


class ParseError(Exception):
    """Raised with a user-facing help message when a mention can't be parsed."""


@dataclass
class ParsedCommand:
    verb: str                 # "gxe" | "epistasis"
    slash_command: str        # "/run-flashp-gxe"
    network_name: str         # friendly label, e.g. "Flowering_Time"
    network_dir: Path         # absolute path to the <NET> dir

    def prompt(self) -> str:
        # The argument passed to the slash command is the absolute network dir.
        return f'{self.slash_command} "{self.network_dir.as_posix()}"'


# Path fragments that mark a non-canonical / snapshot network we should NOT expose.
_EXCLUDE_FRAGMENTS = ("worktrees", "iteration_", "_baseline_snapshot", "refinement", "runs", "kb_cleaned")


def _is_analyzable(net_json: Path) -> bool:
    """The Light gxe/epistasis drivers require the short-key schema (edges use `s`/`t`).

    Paper-format networks (`source`/`target`) would crash the drivers, so we only
    expose networks the drivers can actually run — no failed runs posted to Teams.
    """
    try:
        edges = json.loads(net_json.read_text(encoding="utf-8")).get("edges", [])
    except (OSError, ValueError):
        return False
    return bool(edges) and "s" in edges[0] and "t" in edges[0]


def discover_networks(roots: list[Path]) -> dict[str, Path]:
    """Return {alias_lower: net_dir} for every canonical, analyzable built network.

    A canonical network is a dir `<NET>` that directly contains `network/network.json`.
    We skip iteration/refinement/worktree snapshots, and (via `_is_analyzable`) only
    surface Light-format networks the analysis drivers can actually run.
    """
    found: dict[str, Path] = {}
    for root in roots:
        if not root.exists():
            continue
        for net_json in root.rglob("network/network.json"):
            # net_json = <NET>/network/network.json  ->  net_dir = <NET>
            if net_json.parent.name != "network":
                continue
            net_dir = net_json.parent.parent
            low = net_dir.as_posix().lower()
            if any(frag in low for frag in _EXCLUDE_FRAGMENTS):
                continue
            if not _is_analyzable(net_json):
                continue
            base = net_dir.name                       # e.g. "Flowering_Time_network"
            stem = re.sub(r"_network$", "", base)     # e.g. "Flowering_Time"
            for alias in {base, stem, stem.replace("_", " ")}:
                found.setdefault(alias.strip().lower(), net_dir)
    return found


def _clean_mention_text(text: str) -> str:
    """Strip HTML tags (Teams sends `<at>flash-p</at> ...`) and a leading bot name."""
    text = re.sub(r"<[^>]+>", " ", text or "")          # drop <at>..</at> etc.
    text = text.replace("&nbsp;", " ").strip()
    # Drop a leading "@flash-p" / "flash-p" / "flashp" token if present.
    text = re.sub(r"^@?\s*flash[\s_-]?p\b[:,]?", "", text, flags=re.IGNORECASE).strip()
    return text


def _usage(networks: dict[str, Path]) -> str:
    examples = sorted({d.name for d in networks.values()})[:6]
    ex = ", ".join(re.sub(r"_network$", "", e) for e in examples) or "(no built networks found)"
    return (
        "Usage: `@flash-p gxe <network>` or `@flash-p epistasis <network>`.\n"
        f"Available networks include: {ex}."
    )


def parse(text: str, cfg: Config, networks: dict[str, Path] | None = None) -> ParsedCommand:
    nets = networks if networks is not None else discover_networks(cfg.network_roots)
    body = _clean_mention_text(text)
    if not body:
        raise ParseError(_usage(nets))

    parts = body.split()
    # Normalize Telegram-style commands: "/gxe" and "/gxe@MyBot" -> "gxe".
    verb = parts[0].lstrip("/").split("@", 1)[0].lower()
    if verb not in cfg.commands:
        raise ParseError(f"Unknown action `{verb}`.\n{_usage(nets)}")
    if len(parts) < 2:
        raise ParseError(f"`{verb}` needs a network name.\n{_usage(nets)}")

    query = " ".join(parts[1:]).strip()
    key = query.lower()
    net_dir = nets.get(key) or nets.get(key.replace(" ", "_")) or nets.get(re.sub(r"_network$", "", key))
    if net_dir is None:
        raise ParseError(f"No network matching `{query}`.\n{_usage(nets)}")

    return ParsedCommand(
        verb=verb,
        slash_command=cfg.commands[verb],
        network_name=re.sub(r"_network$", "", net_dir.name),
        network_dir=net_dir,
    )
