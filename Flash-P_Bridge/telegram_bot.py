"""FLASH-P Telegram bridge — the easy front door.

Run it on the machine that has your authenticated Claude Code CLI:

    python telegram_bot.py

In Telegram, open your bot and either type a command or use the `/` menu:

    /gxe Stomatal_Conductance      gene x environment
    /epistasis Water_Use_Efficiency gene x gene
    /gxe                            (no name) -> pick a network from buttons
    /networks                       list available networks
    /help                           how to use it

It long-polls Telegram (outbound only — no tunnel, no public port), checks the sender
against the allowlist, runs the analysis sandboxed on your subscription, and replies with
a FLASH-P-branded image card + the full HTML report. Same core as the Teams adapter.
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
NET_NAMES = sorted({d.name for d in networks.values()})
TOKEN = cfg.telegram_bot_token

_MENU = [
    {"command": "gxe", "description": "Gene x environment interactions on a network"},
    {"command": "epistasis", "description": "Gene x gene epistasis on a network"},
    {"command": "networks", "description": "List available networks"},
    {"command": "help", "description": "How to use this bot"},
]

_HELP = (
    "FLASH-P bot — run analyses on existing networks.\n\n"
    "/gxe <network>        gene x environment interactions\n"
    "/epistasis <network>  gene x gene epistasis\n"
    "/networks             list available networks\n"
    "/help                 this message\n\n"
    "Tip: send /gxe or /epistasis with no name to pick a network from a list."
)


def _handle_job(job: Job) -> None:
    """Worker callback: run FLASH-P, then send a branded image + HTML back to the chat."""
    res = run_job(job.command, cfg)
    head = "✅" if res.ok else "⚠️"
    title = f"{head} FLASH-P · {job.command.verb} · {job.command.network_name}"
    if res.ok and res.png_path:
        telegram.send_photo(TOKEN, job.reply_to, res.png_path, caption=title)
        if res.html_path:
            telegram.send_document(TOKEN, job.reply_to, res.html_path, caption="📄 Full report")
    else:
        telegram.send_message(TOKEN, job.reply_to, f"{title}\n\n{res.summary[:3500]}")


queue = JobQueue(worker=_handle_job)


def _verb_and_arg(text: str) -> tuple[str, str]:
    parts = text.strip().split()
    if not parts:
        return "", ""
    verb = parts[0].lstrip("/").split("@", 1)[0].lower()
    return verb, " ".join(parts[1:]).strip()


def _handle(m: telegram.IncomingMessage) -> None:
    print(f"[msg] id={m.sender_id} @{m.sender_username} {m.sender_name!r}: {m.text!r}", flush=True)

    # Inline-keyboard tap: acknowledge it and turn "gxe|Net" into "gxe Net".
    text = m.text
    if m.callback_id:
        telegram.answer_callback_query(TOKEN, m.callback_id)
        text = text.replace("|", " ", 1)

    # Authorize.
    if not cfg.is_allowed_telegram(m.sender_id, m.sender_username):
        telegram.send_message(
            TOKEN, m.chat_id,
            f"Sorry {m.sender_name}, you're not on the FLASH-P allowlist.\n"
            f"Your Telegram id is {m.sender_id} — ask the owner to add it.",
        )
        return

    verb, arg = _verb_and_arg(text)

    if verb in ("help", "start", ""):
        telegram.send_message(TOKEN, m.chat_id, _HELP)
        return
    if verb == "networks":
        listing = "\n".join(f"• {n}" for n in NET_NAMES) or "(none found)"
        telegram.send_message(TOKEN, m.chat_id, f"Available networks:\n{listing}")
        return
    # Verb with no network -> show a tappable network picker.
    if verb in cfg.commands and not arg:
        buttons = [(n, f"{verb}|{n}") for n in NET_NAMES]
        telegram.send_message(
            TOKEN, m.chat_id, f"Pick a network for {verb}:",
            reply_markup=telegram.inline_keyboard(buttons, columns=2),
        )
        return

    # Full command.
    try:
        command = command_map.parse(text, cfg, networks)
    except command_map.ParseError as e:
        telegram.send_message(TOKEN, m.chat_id, str(e))
        return
    ahead = queue.submit(Job(command=command, requester=m.sender_name, reply_to=m.chat_id))
    when = "now" if ahead == 0 else f"after {ahead} job(s) ahead"
    telegram.send_message(
        TOKEN, m.chat_id,
        f"▶️ Running {command.verb} on {command.network_name} ({when}). I'll send the results here when it's done.",
    )


def main() -> int:
    if not TOKEN or TOKEN.startswith("PASTE"):
        print("✗ Set telegram.bot_token in config.json (get one from @BotFather).")
        return 1
    me = telegram.get_me(TOKEN)
    if not me.get("ok"):
        print("✗ Bad bot token:", me)
        return 1

    telegram.set_my_commands(TOKEN, _MENU)
    print(f"✓ Bot @{me['result']['username']} polling. {len(NET_NAMES)} network(s): {', '.join(NET_NAMES)}")
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
            if m:
                _handle(m)


if __name__ == "__main__":
    raise SystemExit(main())
