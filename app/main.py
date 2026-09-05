"""FastAPI app — SSE stream, trigger loop, UI.

The Phase 1 scripted demo has been removed: it hardcoded suppliers and prices,
which is exactly the domain leak D-015 forbids in `app/`. Runs now come from the
engine, driven by the trigger loop.

Run:  uvicorn app.main:app --port 8010 --reload
      uvicorn vendors.main:app --port 8011
"""
import asyncio
import json
import os
import pathlib

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse

from app import engine, profiles, registry, templates, triggers, xrpl_ops

STATIC = pathlib.Path(__file__).resolve().parent / "static"

VERTICAL = os.getenv("VERTICAL", "event-contingency")
PROFILE = os.getenv("PROFILE", "organizer-01")
ADAPTER = os.getenv("EXECUTOR", "mock")

app = FastAPI(title="alternate.ai")

_subscribers: list[asyncio.Queue] = []
_running = False


async def emit(event: dict) -> None:
    for q in list(_subscribers):
        await q.put(event)


@app.on_event("startup")
async def _start_watcher():
    asyncio.create_task(triggers.watch(VERTICAL, _on_event))


async def _on_event(event: dict) -> None:
    """A trigger fired. Run the recovery, once at a time."""
    global _running
    if _running:
        return
    _running = True
    try:
        await engine.run(event=event, profile_id=PROFILE, vertical=VERTICAL,
                         emit=emit, adapter_name=ADAPTER)
    except Exception as exc:
        await emit({"type": "error", "text": f"Recovery failed: {exc}",
                    "recovery": "see server logs"})
        raise
    finally:
        _running = False


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


@app.get("/health")
async def health():
    return await xrpl_ops.network_costs()


@app.get("/context")
async def context():
    """What the UI needs to describe the current setup, without domain knowledge."""
    tpl = templates.load(VERTICAL)
    prof = profiles.load(PROFILE)
    return {
        "vertical": VERTICAL,
        "template": tpl["name"],
        "verticals_available": templates.available(),
        "profile": {"id": prof["id"], "name": prof["name"], "org": prof.get("org")},
        "event": prof.get("event", {}),
        "constraints": prof.get("constraints", {}),
        "envelope": prof["envelope"],
        "notes": profiles.personalisation_notes(prof),
        "providers": [{"id": p["id"], "name": p["name"], "category": p["category"]}
                      for p in registry.load(VERTICAL)],
        "events": [{"id": e["id"], "type": e["type"],
                    "pending": e.get("pending", False),
                    "matches": templates.matches(tpl, e)}
                   for e in triggers.load_events(VERTICAL)],
        "executor": ADAPTER,
    }


@app.post("/fire/{event_id}")
async def fire(event_id: str):
    """Mark an event pending. The loop picks it up — it is still the mechanism."""
    triggers.fire(VERTICAL, event_id)
    return {"fired": event_id}


@app.post("/reset")
async def reset():
    triggers.reset()
    await emit({"type": "reset"})
    return {"ok": True}


@app.get("/stream")
async def stream():
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.append(q)

    async def gen():
        try:
            yield "retry: 2000\n\n"
            while True:
                yield f"data: {json.dumps(await q.get())}\n\n"
        finally:
            if q in _subscribers:
                _subscribers.remove(q)

    return StreamingResponse(
        gen(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
