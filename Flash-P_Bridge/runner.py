"""Run a parsed FLASH-P command and return a short, Teams-ready summary.

Two engines (set in config `claude.engine`):

* "claude"  — the real thing: spawn the authenticated Claude Code CLI to run the
              slash command (`/run-flashp-gxe <NET>`) in the project dir, sandboxed
              by `--permission-mode dontAsk` + settings.headless.json. The agent's
              own relayed findings ARE the summary. Uses the operator's subscription.
* "python"  — run the deterministic driver directly (no LLM, no tokens). Handy for
              local verification of the plumbing without spending subscription.

Nothing here calls any API or holds any key — the "claude" engine just shells out
to the already-logged-in CLI.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from command_map import ParsedCommand
from config_loader import Config

# Where each verb's full outputs land, relative to <NET> (for the "see full results" pointer).
_ARTIFACT_DIR = {"gxe": "gxe", "epistasis": "epistasis"}


@dataclass
class RunResult:
    ok: bool
    summary: str
    artifacts_dir: str          # human-readable path to full outputs (may not exist on failure)


def _artifacts_pointer(cmd: ParsedCommand) -> str:
    return (cmd.network_dir / _ARTIFACT_DIR.get(cmd.verb, "")).as_posix()


def run(cmd: ParsedCommand, cfg: Config) -> RunResult:
    if cfg.claude.engine == "python":
        return _run_python(cmd, cfg)
    return _run_claude(cmd, cfg)


def _run_claude(cmd: ParsedCommand, cfg: Config) -> RunResult:
    args = [
        cfg.claude.bin,
        "-p", cmd.prompt(),
        "--output-format", "json",
        "--permission-mode", cfg.claude.permission_mode,
        "--model", cfg.claude.model,
        # The network lives outside the project dir, so grant tool access to it.
        "--add-dir", cmd.network_dir.as_posix(),
    ]
    if cfg.claude.settings_file:
        args += ["--settings", str(cfg.claude.settings_file)]
    args += list(cfg.claude.extra_args)

    try:
        proc = subprocess.run(
            args,
            cwd=str(cfg.project_dir),
            capture_output=True,
            text=True,
            timeout=cfg.claude.timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return RunResult(False, f"⏱️ Timed out after {cfg.claude.timeout_seconds}s running {cmd.verb} on {cmd.network_name}.", _artifacts_pointer(cmd))

    summary = _extract_claude_result(proc.stdout) or (proc.stderr.strip()[-1500:] if proc.stderr else "")
    ok = proc.returncode == 0 and bool(summary)
    if not summary:
        summary = f"(no output; exit code {proc.returncode})"
    return RunResult(ok, summary.strip(), _artifacts_pointer(cmd))


def _extract_claude_result(stdout: str) -> str:
    """`--output-format json` prints one result object; pull its `result` text."""
    stdout = (stdout or "").strip()
    if not stdout:
        return ""
    # Try whole-string JSON first, then last non-empty line (stream-json fallback).
    for candidate in (stdout, stdout.splitlines()[-1]):
        try:
            obj = json.loads(candidate)
        except (json.JSONDecodeError, IndexError):
            continue
        if isinstance(obj, dict):
            return str(obj.get("result") or obj.get("text") or "").strip()
    return stdout  # not JSON — return raw text as a last resort


def _run_python(cmd: ParsedCommand, cfg: Config) -> RunResult:
    net = cmd.network_dir.as_posix()
    if cmd.verb == "gxe":
        args = ["python", "Agent/shared/gxe_report.py", net, "--modes", "KO,OE", "--doses", "0.25,0.5,1,2"]
    elif cmd.verb == "epistasis":
        out = (cmd.network_dir / "epistasis" / "epistasis_doubles.tsv").as_posix()
        args = ["python", "Agent/shared/scan_epistasis.py", net, "--epistasis", "--classify", "--out", out]
    else:
        return RunResult(False, f"Unsupported verb {cmd.verb}", _artifacts_pointer(cmd))

    try:
        proc = subprocess.run(
            args, cwd=str(cfg.project_dir), capture_output=True, text=True,
            timeout=cfg.claude.timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return RunResult(False, f"⏱️ Timed out after {cfg.claude.timeout_seconds}s.", _artifacts_pointer(cmd))

    tail = "\n".join((proc.stdout or "").strip().splitlines()[-40:])
    ok = proc.returncode == 0
    if not ok and proc.stderr:
        tail = (tail + "\n" + proc.stderr.strip()[-800:]).strip()
    # gxe writes a markdown report — prefer its content as the summary if present.
    if cmd.verb == "gxe":
        report = cmd.network_dir / "gxe" / "GXE_REPORT.md"
        if report.exists():
            tail = report.read_text(encoding="utf-8")[:3000]
    return RunResult(ok, tail or f"(exit {proc.returncode})", _artifacts_pointer(cmd))
