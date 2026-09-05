"""User profiles — the personalisation layer.

A profile holds preferences, hard constraints, the spend envelope, and a history
of past decisions. History is read as context and nudges scoring in a visible,
explainable way (see scoring.preference_bonus in the template). It is not
machine learning, and it should not become machine learning: a judge asking
"why did it pick that?" must get a sentence, not a weight vector.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROFILES = ROOT / "profiles"


class ProfileError(ValueError):
    pass


def load(profile_id: str) -> dict:
    path = PROFILES / f"{profile_id}.json"
    if not path.exists():
        raise ProfileError(f"no profile at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save(profile: dict) -> None:
    (PROFILES / f"{profile['id']}.json").write_text(
        json.dumps(profile, indent=2), encoding="utf-8"
    )


def remember(profile: dict, *, event: str, chose: str, over: str, because: str) -> dict:
    """Append a decision to history so the next incident can learn from it."""
    profile.setdefault("history", []).insert(0, {
        "at": "just now", "event": event, "chose": chose, "over": over, "because": because,
    })
    profile["history"] = profile["history"][:10]
    save(profile)
    return profile


def personalisation_notes(profile: dict) -> list[str]:
    """Human-readable facts the agent is allowed to act on.

    These get streamed into the trace so personalisation is *visible*. A selling
    point the user cannot see is not a selling point.
    """
    notes = []
    prefs = profile.get("preferences", {})
    cons = profile.get("constraints", {})

    if cons.get("commitment"):
        notes.append(f"must make {cons['commitment']}")
    if cons.get("arrive_by"):
        notes.append(f"arrive by {cons['arrive_by']}")
    if cons.get("max_transfer_minutes"):
        notes.append(f"transfers under {cons['max_transfer_minutes']} min")
    if prefs.get("avoid_red_eye"):
        notes.append("avoids red-eye departures")
    for s in prefs.get("preferred_suppliers", []):
        notes.append(f"prefers {s}")
    for s in prefs.get("avoid_suppliers", []):
        notes.append(f"avoids {s}")
    for h in profile.get("history", [])[:2]:
        notes.append(f"previously chose {h['chose']} over {h['over']} — {h['because']}")
    return notes
