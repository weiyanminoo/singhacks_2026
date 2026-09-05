"""FastAPI app — Phase 1: SSE stream + the UI shell.

The agent, registry, policy and scoring arrive in Phase 2/3. This exists so the
trace panel and envelope are alive and rendering real streamed events, which is
half of milestone M1.

Run:  uvicorn app.main:app --port 8000 --reload
"""
import asyncio
import json
import pathlib

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse

from app import xrpl_ops

STATIC = pathlib.Path(__file__).resolve().parent / "static"

app = FastAPI(title="alternate.ai")

# One queue per connected browser. A run broadcasts to all of them.
_subscribers: list[asyncio.Queue] = []


async def emit(event: dict) -> None:
    """Push one trace event to every connected browser."""
    for q in list(_subscribers):
        await q.put(event)


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


@app.get("/health")
async def health():
    """Live network values, so the UI can prove it is talking to a real ledger."""
    return await xrpl_ops.network_costs()


@app.get("/stream")
async def stream():
    """Server-Sent Events. One line of JSON per event."""
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.append(q)

    async def gen():
        try:
            yield "retry: 2000\n\n"
            while True:
                event = await q.get()
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            if q in _subscribers:
                _subscribers.remove(q)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/demo")
async def demo():
    """Phase 1 only: drive the panel with a scripted sequence.

    Proves events render and the envelope animates. Phase 3 replaces this with
    the real agent run.
    """
    asyncio.create_task(_demo_run())
    return {"started": True}


async def _demo_run() -> None:
    envelope = 10.00
    spent = 0.0

    async def envelope_event():
        await emit({"type": "envelope", "remaining": f"{envelope - spent:.2f}",
                    "spent": f"{spent:.2f}", "pct": (envelope - spent) / envelope})

    await emit({"type": "trace", "id": "t0", "text": "Disruption detected — SQ0842 SIN→CGK cancelled",
                "detail": "Meeting 09:00 Jakarta · envelope $10.00", "cost": None, "status": "done"})
    await envelope_event()
    await asyncio.sleep(0.4)

    providers = [
        ("Skyline Air", "flights"), ("AeroConnect", "flights"), ("Status Feed", "data"),
        ("Aurora Grand", "hotels"), ("Transit Inn", "hotels"), ("Meridian", "hotels"),
        ("SwiftCar", "ground"),
    ]
    for i, (name, cap) in enumerate(providers):
        await emit({"type": "trace", "id": f"q{i}", "text": f"Querying {name}",
                    "detail": cap, "cost": "$0.02", "status": "running"})
        await asyncio.sleep(0.25)
        spent += 0.02
        await emit({"type": "trace", "id": f"q{i}", "text": f"Queried {name}",
                    "detail": cap, "cost": "$0.02", "status": "done"})
        await envelope_event()

    await emit({"type": "trace", "id": "skip", "text": "Declined to query MetroLink",
                "detail": "best option has 2 rooms left · 8th query not worth the delay",
                "cost": None, "status": "rejected"})
    await asyncio.sleep(0.4)
    await emit({"type": "trace", "id": "rej", "text": "Rejected Aurora Grand — $7.75",
                "detail": "meets every criterion except the $6.25 hotel cap",
                "cost": None, "status": "rejected"})
    await asyncio.sleep(0.4)

    for label, amount in [("Seat SQ0842 06:40", 4.60), ("Room, 1 night", 1.95),
                          ("Airport transfer", 0.49)]:
        spent += amount
        await emit({"type": "purchase", "label": label, "amount": f"${amount:.2f}",
                    "tx_hash": "STUB" + "0" * 60,
                    "explorer_url": "https://testnet.xrpl.org/transactions/"})
        await envelope_event()
        await asyncio.sleep(0.3)

    await emit({"type": "trace", "id": "done", "text": "Recovery complete",
                "detail": f"3 purchases · ${spent:.2f} of ${envelope:.2f}",
                "cost": None, "status": "done"})
