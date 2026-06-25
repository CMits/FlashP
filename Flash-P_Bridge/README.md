# FLASH-P Chat Bridge

Trigger a FLASH-P analysis from a chat app → it runs on your machine (on your
authenticated Claude Code subscription) → the result is sent back to the chat.

v1 scope: **quick analyses on existing networks only** — `gxe` (gene × environment)
and `epistasis` (gene × gene) — triggered by an **allowlist of specific people**.

## How it works (and what "pushing the branch" does)

The bot is **not a website or a server**. `telegram_bot.py` runs on **your** machine and *calls out*
to Telegram (long-polling) — outbound only, **no public port, no tunnel**. When an allow-listed person
messages it, the analysis runs **locally, on your authenticated Claude Code subscription** (or the free
`python` engine), and the branded result is sent back. Consequences:

- It only works **while your machine is on and the script is running** — close the laptop, the bot goes quiet.
- Everything runs on **your** subscription and **your** files. Colleagues need no Claude account; they just message your bot.
- Nothing is exposed — that's why it's safe.

**Pushing this branch to GitHub shares the _code_, not a running bot.** Nobody can use FLASH-P-over-chat
just because the code is public. To get a working bot, someone **self-hosts** (see below).

## Self-host (run your own bot)

1. Clone the repo and `cd Flash-P_Bridge`.
2. `pip install -r requirements.txt`, then `cp config.example.json config.json`.
3. Be logged in to Claude Code on that machine (`claude` on PATH, active subscription).
4. Create your own bot with **@BotFather** → paste the token into `config.json` → `telegram.bot_token`.
5. `python telegram_bot.py`, DM the bot to learn your id, add it to `telegram.allowlist`, restart.

No cost or compute lands on anyone else — each host uses their own token and their own subscription.

Three transports share one platform-agnostic core:
- **Telegram bot (easiest, your private team trigger)** — long-polls Telegram; **no tunnel,
  no public port, no HMAC**. Setup = one @BotFather token. → `telegram_bot.py`
- **Discord bot (the community front door)** — slash commands + a network dropdown in a
  Discord server; outbound gateway websocket, **no tunnel, no public port**. → `discord_bot.py`
- **Microsoft Teams** — `@flash-p` in a channel; needs a public tunnel + Power Automate
  + a 5s reply window. → `listener.py` (see "Teams setup" below)

Adding a platform = a new `adapters/<name>.py` + an entry point against the same core; the
security model (allowlist + command-lock + sandbox + single-worker queue) is shared.

---

## Quickstart — Telegram (do this first)

1. **Install deps + config** (once):
   ```bash
   cd Flash-P_Bridge
   pip install -r requirements.txt
   cp config.example.json config.json
   ```
   You must already be logged in to Claude Code on this machine (`claude` on PATH).

2. **Create a bot:** in Telegram, message **@BotFather** → `/newbot` → pick a name →
   it gives you a **token** like `8123456789:AAH...`. Paste it into
   `config.json` → `telegram.bot_token`.

3. **Allowlist yourself:** run `python telegram_bot.py`, DM your bot anything. It replies
   with *"you're not on the allowlist — your Telegram id is `NNN`"*. Put that id (or your
   `@username`) into `config.json` → `telegram.allowlist`, then restart the bot.

4. **Use it:** DM the bot
   ```
   gxe Stomatal_Conductance
   epistasis Water_Use_Efficiency
   ```
   You'll get "▶️ Running…", then the result.

> Tip: keep `claude.engine` = `"python"` in `config.json` for your first test (runs the
> analysis deterministically, **zero subscription cost**). Flip to `"claude"` to have the
> real agent run it on your subscription. Keep the machine awake while the bot runs.

---

## Quickstart — Discord (the community bot)

Use Discord when you want a **public server** people can join and trigger analyses from,
with slash commands and a **network dropdown**. Same safe core as Telegram.

1. **Install deps** (once): `pip install -r requirements.txt` (adds `discord.py`).

2. **Create the bot:** go to the **Discord Developer Portal** → *New Application* → **Bot**
   → *Reset Token* → copy the token into `config.json` → `discord.bot_token`.

3. **Invite it to your server:** Developer Portal → *OAuth2 → URL Generator* → scopes
   **`bot`** + **`applications.commands`** → open the generated URL → add it to your server.
   Put your server's ID in `config.json` → `discord.guild_id` (right-click the server with
   Developer Mode on → *Copy Server ID*) so slash commands appear **instantly**; leave it
   blank for global commands (can take up to ~1h to propagate).

4. **Allowlist yourself:** run `python discord_bot.py`, type `/gxe` in the server. If you're
   not listed it replies *"your Discord id is `NNN`"* (ephemerally). Put that id into
   `config.json` → `discord.allowlist`, then restart.

5. **Use it:**
   ```
   /gxe network:Stomatal_Conductance
   /epistasis network:Water_Use_Efficiency
   /gxe                 ← no network: pick one from the dropdown
   /networks            ← list available networks
   /help
   ```
   You'll get an ephemeral "▶️ Running…", then the **branded card + HTML report** posted in
   the channel for everyone to see.

> Same `claude.engine` tip applies — keep it `"python"` for a free first test.

---

```
@flash-p gxe Flowering_Time        (Teams channel)
   │  Outgoing Webhook (HMAC-signed POST)
   ▼  public HTTPS tunnel
listener.py  →  verify HMAC → allowlist → parse → ack <5s → enqueue
   ▼
claude -p "/run-flashp-gxe <NET>"   (your subscription, sandboxed to the pipeline)
   ▼  on completion
result posted back via a Power Automate Workflow
```

Why two hops: a Teams outgoing webhook must reply within **~5 seconds**, but a FLASH-P
run takes minutes — so the webhook only *acknowledges*, and the real result is posted
**asynchronously** through a Power Automate "Workflow" (Office 365 incoming-webhook
connectors were retired in May 2026).

---

## Architecture (platform-agnostic core + thin adapters)

| File | Role |
|------|------|
| `telegram_bot.py` | **Telegram** front door: long-poll → authorize → parse → ack → enqueue |
| `discord_bot.py` | **Discord** front door: slash commands + dropdown → authorize → parse → ack → enqueue |
| `listener.py` | **Teams** front door (FastAPI): verify HMAC → authorize → parse → ack → enqueue |
| `command_map.py` | **Primary security layer** — only `gxe`/`epistasis` on a discovered network can become a command |
| `runner.py` | Runs the headless, sandboxed `claude -p` (or the Python driver directly for testing) |
| `render.py` | Turns driver outputs into a FLASH-P-branded PNG card + styled HTML report |
| `job_queue.py` | Single-worker queue — runs one job at a time, never overlapping |
| `adapters/telegram.py` | Telegram glue: long-poll, parse update, send message/photo/document |
| `adapters/discord.py` | Discord glue: client, network dropdown (`PickerView`), send result files |
| `adapters/teams.py` | Teams glue: HMAC verify, payload parse, ack, async post-back |
| `config.json` | **Your secrets** + settings — **gitignored, never committed**; copy from `config.example.json` |
| `settings.headless.json` | Permission allow/deny profile for the unattended runs |

### Contributing a new platform or network
- **New platform** = a new `adapters/<name>.py` + a `<name>_bot.py` entry point that calls
  the same `command_map.parse` → `job_queue` → `runner.run` → `render` path. Don't touch the
  core; keep the allowlist + command-lock. `discord.py` is the reference example to copy.
- **New network** = a Light-format `<NET>/network/network.json` (edges use short keys `s`/`t`);
  drop it under a configured `network_roots` path and it's auto-discovered. (A community
  networks gallery for sharing/bulk download is on the roadmap.)

## Secrets

**All secrets live in `config.json` only** (bot token, Teams HMAC token, workflow URL,
allowlist). `config.json` is gitignored — it is **never pushed**. The committed
`config.example.json` contains **placeholders only**. When you (or a colleague) clone the
repo, you `cp config.example.json config.json` and paste your own tokens locally. No key
is ever in git history.

---

## One-time setup

### 0. Install
```bash
cd Flash-P_Bridge
pip install -r requirements.txt
cp config.example.json config.json     # then edit config.json
```
You must already be logged in to Claude Code on this machine (`claude` on PATH, an
active subscription). The bridge never handles API keys — it shells out to your CLI.

### 1. Create the Teams **Outgoing Webhook**
Teams channel → ••• → **Manage team** → **Apps** → *Create an outgoing webhook*.
- **Name:** `flash-p` (this is what people @mention)
- **Callback URL:** your tunnel URL + `/teams/webhook` (see step 3)
- **Save the HMAC security token** it shows you → put it in `config.json` → `teams.hmac_token`.

> Creating an outgoing webhook needs no Azure app and usually no admin rights (unless
> your tenant has disabled member-created connectors).

### 2. Create the Power Automate **Workflow** (async result post-back)
Teams channel → ••• → **Workflows** → *"Post to a channel when a webhook request is
received"*. Copy the generated POST URL → `config.json` → `teams.workflow_url`.

### 3. Expose your listener with a tunnel
The callback URL must be public HTTPS. Easiest free option — **VS Code Dev Tunnels**
(or Cloudflare Tunnel):
```bash
# forwards a public https URL to your local listener on :8787
devtunnel host -p 8787 --allow-anonymous
```
Use that public URL (+ `/teams/webhook`) as the outgoing-webhook callback in step 1.

### 4. Fill in the allowlist
`config.json` → `allowlist` → add the one person who may trigger runs, by their Teams
**`aadObjectId`**. Easiest way to capture it: start the listener, @mention from that
person, and read the `sender_aad` the listener logs for the rejected attempt.

### 5. Run it
```bash
python listener.py            # or: uvicorn listener:app --host 127.0.0.1 --port 8787
```
Keep the machine awake (disable sleep) while you want `@flash-p` to work.

---

## Where it runs / always-on

For the one-person demo, your **PC** is fine — just keep it awake with the listener +
tunnel running. To make it always-on later, lift this same folder onto a small **cloud
VM or mini-PC**: install Claude Code, `claude` login once with your subscription, clone
the repo, and run `listener.py` as a service. No code changes.

---

## Safety model (defense in depth)

1. **HMAC** — only your Teams outgoing webhook can call the listener.
2. **Sender allowlist** — only listed `aadObjectId`s can trigger runs.
3. **Command allowlist** — free text never reaches the agent; only
   `/run-flashp-gxe|epistasis <known-network>` is ever sent.
4. **Sandboxed runs** — `--permission-mode dontAsk` + `settings.headless.json` deny
   destructive / exfiltration / repo-mutating shell verbs.
5. **Single-worker queue** — runs never overlap or collide on a network dir.

---

## Local test (no Teams needed)

`selftest.py` posts synthetic, correctly-HMAC-signed payloads to a running listener and
checks the four paths (valid trigger / bad HMAC / non-allowlisted / bad command). Set
`claude.engine` to `"python"` in `config.json` first to exercise the deterministic
driver without spending subscription tokens.
```bash
python listener.py            # terminal 1
python selftest.py            # terminal 2
```
