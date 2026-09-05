"""The trigger loop.

An always-on watcher over a pluggable event source. Today the source is a YAML
file; swapping it for a webhook, a queue or a real operational feed means
replacing `poll()` and nothing else — the engine never learns where events come
from.

`fire()` marks an event pending so the demo can trigger a run on cue while the
loop remains the real mechanism.
"""
from __future__ import annotations

import asyncio
import pathlib

import yaml

from app import templates

ROOT = pathlib.Path(__file__).resolve().parent.parent
VERTICALS = ROOT / "verticals"

POLL_SECONDS = 2.0
_seen: set[str] = set()


def _path(vertical: str) -> pathlib.Path:
    return VERTICALS / vertical / "events.yaml"


def load_events(vertical: str) -> list[dict]:
    return yaml.safe_load(_path(vertical).read_text(encoding="utf-8"))["events"]


def fire(vertical: str, event_id: str) -> dict:
    """Mark an event pending — the loop picks it up on its next poll."""
    doc = yaml.safe_load(_path(vertical).read_text(encoding="utf-8"))
    for e in doc["events"]:
        if e["id"] == event_id:
            e["pending"] = True
            _seen.discard(event_id)
            _path(vertical).write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
            return e
    raise KeyError(f"no event {event_id}")


def _clear_pending(vertical: str, event_id: str) -> None:
    """Consume the event in the source.

    Without this a leftover `pending: true` survives a restart and replays the
    whole recovery the moment the server boots — which during a demo looks like
    the agent firing on its own.
    """
    doc = yaml.safe_load(_path(vertical).read_text(encoding="utf-8"))
    for e in doc["events"]:
        if e["id"] == event_id:
            e["pending"] = False
    _path(vertical).write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def poll(vertical: str) -> list[dict]:
    """Pending events this vertical's playbook actually cares about.

    Two filters, deliberately separate: `pending` is source state, `matches` is
    the playbook deciding whether the event is one it handles. An event can be
    pending and still correctly ignored.
    """
    tpl = templates.load(vertical)
    out = []
    for e in load_events(vertical):
        if not e.get("pending") or e["id"] in _seen:
            continue
        if templates.matches(tpl, e):
            out.append(e)
    return out


async def watch(vertical: str, on_event, *, interval: float = POLL_SECONDS) -> None:
    """Run forever. One event at a time — a contingency run is not reentrant."""
    while True:
        try:
            for event in poll(vertical):
                _seen.add(event["id"])
                _clear_pending(vertical, event["id"])   # one-shot: never replay
                await on_event(event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:                      # never let the loop die silently
            print(f"[triggers] poll error: {exc!r}")
        await asyncio.sleep(interval)


def reset() -> None:
    _seen.clear()
