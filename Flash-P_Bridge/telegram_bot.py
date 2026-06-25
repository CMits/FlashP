"""FLASH-P Telegram bridge — the easy front door.

Run it on the machine that has your authenticated Claude Code CLI:

    python telegram_bot.py

Then DM your bot (created via @BotFather):  `gxe Stomatal_Conductance`

It long-polls Telegram (outbound only — no tunnel, no public port), checks the sender
against the allowlist, runs the FLASH-P command sandboxed on your subscription, and
sends the result back to the chat. Same core as the Teams adapter; nothing else changes.
"""
from __future__ import annotations

import sys
import time

try:  # Windows consoles default to cp1252; our status lines + echoed messages use emoji.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import command_map
from adapters import telegram
from config_loader import load_config
from job_queue import Job, JobQueue
from runner import run as run_job

cfg = load_config()
networks = command_map.discover_networks(cfg.network_roots)
TOKEN = cfg.telegram_bot_token


def _handle_job(job: Job) -> None:
    """Worker callback: run FLASH-P, then send the result back to the Telegram chat."""
    result = run_job(job.command, cfg)
    head = "✅ FLASH-P" if result.ok else "⚠️ FLASH-P"
    msg = (
        f"{head} {job.command.verb} — {job.command.network_name}\n\n"
        f"{result.summary}\n\n"
        f"📂 Full outputs: {result.artifacts_dir}"
    )
    telegram.send_message(TOKEN, job.reply_to, msg)


queue = JobQueue(worker=_handle_job)


def main() -> int:
    if not TOKEN or TOKEN.startswith("PASTE"):
        print("✗ Set telegram.bot_token in config.json (get one from @BotFather).")
        return 1
    me = telegram.get_me(TOKEN)
    if not me.get("ok"):
        print("✗ Bad bot token:", me)
        return 1

    n_nets = len({v.name for v in networks.values()})
    print(f"✓ Bot @{me['result']['username']} polling. {n_nets} analyzable network(s) loaded.")
    if not cfg.telegram_allowlist:
        print("  (allowlist empty — everyone is denied; DM the bot once to learn your id, then add it.)")

    queue.start()
    offset: int | None = None
    while True:
        try:
            updates = telegram.get_updates(TOKEN, offset=offset, timeout=30)
        except Exception as e:  # transient network error — back off and retry
            print("poll error:", e)
            time.sleep(3)
            continue

        for u in updates:
            offset = u["update_id"] + 1
            m = telegram.parse_update(u)
            if not m:
                continue
            print(f"[msg] id={m.sender_id} @{m.sender_username} {m.sender_name!r}: {m.text!r}", flush=True)

            # Authorize.
            if not cfg.is_allowed_telegram(m.sender_id, m.sender_username):
                telegram.send_message(
                    TOKEN, m.chat_id,
                    f"Sorry {m.sender_name}, you're not on the FLASH-P allowlist.\n"
                    f"Your Telegram id is {m.sender_id} — ask the owner to add it.",
                )
                continue

            # Parse to a safe command.
            try:
                command = command_map.parse(m.text, cfg, networks)
            except command_map.ParseError as e:
                telegram.send_message(TOKEN, m.chat_id, str(e))
                continue

            # Ack + enqueue.
            ahead = queue.submit(Job(command=command, requester=m.sender_name, reply_to=m.chat_id))
            when = "now" if ahead == 0 else f"after {ahead} job(s) ahead"
            telegram.send_message(
                TOKEN, m.chat_id,
                f"▶️ Running {command.verb} on {command.network_name} ({when}). I'll send the results here when it's done.",
            )


if __name__ == "__main__":
    raise SystemExit(main())
