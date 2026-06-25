"""FLASH-P Discord bot — the community front door.

Run it on the machine that has your authenticated Claude Code CLI:

    python discord_bot.py

In Discord, use the slash commands (they show up as you type `/`):

    /gxe network:Stomatal_Conductance       gene × environment
    /epistasis network:Water_Use_Efficiency gene × gene
    /gxe                                     (no network) -> pick from a dropdown
    /networks                                list available networks
    /help                                    how to use it

Outbound only — discord.py opens a gateway websocket *from* your machine, so there
is no public port and no tunnel. Same safe core as the Telegram bot: allowlist +
command-lock (only gxe/epistasis on a discovered network) + sandboxed runner +
single-worker queue. Results (branded card + HTML report) are posted in the channel.
"""
from __future__ import annotations

import asyncio
import sys
from typing import Optional

try:  # Windows consoles default to cp1252; our status lines use emoji.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

try:
    import discord
    from discord import app_commands
except ModuleNotFoundError:
    print("✗ discord.py is not installed. Run:  pip install -r requirements.txt   (or: pip install discord.py)")
    raise SystemExit(1)

import command_map
from adapters import discord as dadapter
from config_loader import load_config
from job_queue import Job, JobQueue
from runner import run as run_job

cfg = load_config()
networks = command_map.discover_networks(cfg.network_roots)
NET_NAMES = sorted({d.name for d in networks.values()})
TOKEN = cfg.discord_bot_token

client, tree = dadapter.make_client()

_HELP = (
    "**FLASH-P bot** — run analyses on existing networks.\n\n"
    "`/gxe <network>` — gene × environment interactions\n"
    "`/epistasis <network>` — gene × gene epistasis\n"
    "`/networks` — list available networks\n"
    "`/help` — this message\n\n"
    "Tip: run `/gxe` or `/epistasis` with no network to pick one from a dropdown."
)


def _handle_job(job: Job) -> None:
    """Worker callback (runs on the queue thread): run FLASH-P, then post results back.

    The analysis is blocking, so it runs here off the event loop; the reply is then
    scheduled onto the Discord loop with run_coroutine_threadsafe.
    """
    res = run_job(job.command, cfg)
    head = "✅" if res.ok else "⚠️"
    title = f"{head} FLASH-P · {job.command.verb} · {job.command.network_name}"
    channel_id = int(job.reply_to)

    async def _post() -> None:
        channel = client.get_channel(channel_id) or await client.fetch_channel(channel_id)
        if res.ok and res.png_path:
            await dadapter.send_results(channel, res.png_path, res.html_path, title)
        else:
            await channel.send(f"{title}\n\n{res.summary[:1800]}")

    asyncio.run_coroutine_threadsafe(_post(), client.loop)


queue = JobQueue(worker=_handle_job)
_queue_started = False


async def _reply(interaction: discord.Interaction, text: str) -> None:
    """Send an ephemeral note whether or not the interaction was already responded to."""
    if interaction.response.is_done():
        await interaction.followup.send(text, ephemeral=True)
    else:
        await interaction.response.send_message(text, ephemeral=True)


async def _do_run(interaction: discord.Interaction, verb: str, network: str) -> None:
    try:
        command = command_map.parse(f"{verb} {network}".strip(), cfg, networks)
    except command_map.ParseError as e:
        await _reply(interaction, str(e))
        return
    ahead = queue.submit(Job(command=command, requester=dadapter.user_label(interaction.user),
                             reply_to=str(interaction.channel_id)))
    when = "now" if ahead == 0 else f"after {ahead} job(s) ahead"
    await _reply(interaction, f"▶️ Running **{command.verb}** on **{command.network_name}** ({when}). "
                              "I'll post the results in this channel when it's done.")


async def _run_or_pick(interaction: discord.Interaction, verb: str, network: Optional[str]) -> None:
    if not cfg.is_allowed_discord(interaction.user.id, getattr(interaction.user, "name", "")):
        await _reply(interaction,
                     f"Sorry {dadapter.user_label(interaction.user)}, you're not on the FLASH-P allowlist.\n"
                     f"Your Discord id is `{interaction.user.id}` — ask the owner to add it.")
        return
    if network:
        await _do_run(interaction, verb, network)
        return
    if not NET_NAMES:
        await _reply(interaction, "No analyzable networks found. Check `network_roots` in config.json.")
        return

    async def on_pick(picker_interaction: discord.Interaction, value: str) -> None:
        await _do_run(picker_interaction, verb, value)

    view = dadapter.PickerView(verb, NET_NAMES, on_pick)
    await interaction.response.send_message(f"Pick a network for **{verb}**:", view=view, ephemeral=True)


@tree.command(name="gxe", description="Gene × environment interactions on a network")
@app_commands.describe(network="Network name (leave blank to pick from a dropdown)")
async def gxe_cmd(interaction: discord.Interaction, network: Optional[str] = None) -> None:
    await _run_or_pick(interaction, "gxe", network)


@tree.command(name="epistasis", description="Gene × gene epistasis on a network")
@app_commands.describe(network="Network name (leave blank to pick from a dropdown)")
async def epistasis_cmd(interaction: discord.Interaction, network: Optional[str] = None) -> None:
    await _run_or_pick(interaction, "epistasis", network)


@tree.command(name="networks", description="List available networks")
async def networks_cmd(interaction: discord.Interaction) -> None:
    listing = "\n".join(f"• {n}" for n in NET_NAMES) or "(none found)"
    await interaction.response.send_message(f"**Available networks:**\n{listing}", ephemeral=True)


@tree.command(name="help", description="How to use the FLASH-P bot")
async def help_cmd(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(_HELP, ephemeral=True)


@client.event
async def on_ready() -> None:
    global _queue_started
    if not _queue_started:
        queue.start()
        _queue_started = True
    try:
        if cfg.discord_guild_id:
            guild = discord.Object(id=int(cfg.discord_guild_id))
            tree.copy_global_to(guild=guild)
            await tree.sync(guild=guild)          # instant in that server
        else:
            await tree.sync()                     # global — can take up to ~1h to appear
    except Exception as e:  # never let a sync hiccup take the bot down
        print("command sync error:", e)
    print(f"✓ Bot {client.user} ready. {len(NET_NAMES)} network(s): {', '.join(NET_NAMES) or '(none)'}")
    if not cfg.discord_allowlist:
        print("  (allowlist empty — everyone is denied; add your Discord user id to config.json.)")


def main() -> int:
    if not TOKEN or TOKEN.startswith("PASTE"):
        print("✗ Set discord.bot_token in config.json (Discord Developer Portal → your app → Bot → Reset Token).")
        return 1
    client.run(TOKEN)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
