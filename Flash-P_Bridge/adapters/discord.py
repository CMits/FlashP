"""Discord adapter for the FLASH-P bridge.

Like the Telegram adapter, this is **outbound only**: discord.py opens a gateway
websocket *from* your machine to Discord — no public port, no tunnel, nothing to
expose. Pure Discord glue (client, the network dropdown, file sending); the
platform-agnostic core (command_map / runner / render / job_queue) is untouched.

Requires `discord.py` (see requirements.txt). Imported only by `discord_bot.py`,
so the Telegram path never needs the library installed.
"""
from __future__ import annotations

import discord
from discord import app_commands


def make_client() -> tuple[discord.Client, app_commands.CommandTree]:
    """A minimal-intent client (slash commands need no privileged/message intents)."""
    intents = discord.Intents.none()
    intents.guilds = True
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)
    return client, tree


def user_label(user) -> str:
    return getattr(user, "display_name", None) or getattr(user, "name", None) or str(getattr(user, "id", "someone"))


class PickerView(discord.ui.View):
    """A dropdown of network names; awaits `on_pick(interaction, value)` on selection."""

    def __init__(self, verb: str, net_names: list[str], on_pick, *, timeout: float = 120):
        super().__init__(timeout=timeout)
        self._on_pick = on_pick
        options = [discord.SelectOption(label=n) for n in net_names[:25]]  # Discord caps a select at 25
        select = discord.ui.Select(placeholder=f"Pick a network for {verb}…",
                                   options=options, min_values=1, max_values=1)
        select.callback = self._handle
        self.add_item(select)
        self._select = select

    async def _handle(self, interaction: discord.Interaction) -> None:
        await self._on_pick(interaction, self._select.values[0])


async def send_results(channel, png_path: str | None, html_path: str | None, title: str) -> None:
    """Post the branded card + HTML report to the channel (public, so the community sees it)."""
    files = []
    if png_path:
        files.append(discord.File(png_path))
    if html_path:
        files.append(discord.File(html_path))
    await channel.send(content=title, files=files) if files else await channel.send(content=title)
