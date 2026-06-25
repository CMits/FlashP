"""FLASH-P Teams bridge — the HTTP front door.

Flow per incoming `@flash-p ...` mention:
  1. verify the Teams HMAC signature        (adapters.teams.verify_hmac)
  2. check the sender is on the allowlist    (config.allowed_aad_ids)
  3. parse to a safe, allowlisted command    (command_map.parse)
  4. reply within ~5s ("running…")           (adapters.teams.ack)
  5. enqueue a single-worker job             (job_queue)
  6. when the job finishes, post the result  (adapters.teams.post_result)

Run it with:   uvicorn listener:app --host 127.0.0.1 --port 8787
(or:           python listener.py)
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import command_map
from adapters import teams
from config_loader import load_config
from job_queue import Job, JobQueue
from runner import run as run_job

cfg = load_config()
networks = command_map.discover_networks(cfg.network_roots)
app = FastAPI(title="FLASH-P Teams Bridge")


def _handle_job(job: Job) -> None:
    """Worker callback: run FLASH-P, then post the result back to Teams."""
    result = run_job(job.command, cfg)
    head = "✅ FLASH-P" if result.ok else "⚠️ FLASH-P"
    msg = (
        f"{head} {job.command.verb} — {job.command.network_name}  (requested by {job.requester})\n\n"
        f"{result.summary}\n\n"
        f"📂 Full outputs: {result.artifacts_dir}"
    )
    teams.post_result(job.reply_to or cfg.workflow_url, msg)


queue = JobQueue(worker=_handle_job)
queue.start()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "networks_loaded": len(networks)}


@app.post("/teams/webhook")
async def teams_webhook(request: Request):
    raw = await request.body()

    # 1. Authenticate the request actually came from our Teams outgoing webhook.
    if not teams.verify_hmac(raw, request.headers.get("authorization", ""), cfg.hmac_token):
        return JSONResponse(teams.ack("Unauthorized."), status_code=401)

    payload = await request.json()
    mention = teams.parse_mention(payload)

    # Log the sender so the operator can capture the aadObjectId for the allowlist.
    print(f"[mention] name={mention.sender_name!r}  aadObjectId={mention.sender_aad!r}  text={mention.text!r}", flush=True)

    # 2. Authorize the sender (by Azure Object ID or display name).
    if not cfg.is_allowed(mention.sender_aad, mention.sender_name):
        return JSONResponse(teams.ack(
            f"Sorry {mention.sender_name}, you're not on the FLASH-P allowlist. "
            f"Ask the owner to add you."
        ))

    # 3. Parse to a safe command.
    try:
        command = command_map.parse(mention.text, cfg, networks)
    except command_map.ParseError as e:
        return JSONResponse(teams.ack(str(e)))

    # 4. Ack within the 5s window + 5. enqueue.
    ahead = queue.submit(Job(command=command, requester=mention.sender_name, reply_to=cfg.workflow_url))
    when = "now" if ahead == 0 else f"after {ahead} job(s) ahead of it"
    return JSONResponse(
        teams.ack(f"▶️ Running {command.verb} on **{command.network_name}** ({when}). I'll post the results here when it's done.")
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=cfg.host, port=cfg.port)
