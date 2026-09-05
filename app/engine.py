"""The contingency engine.

Domain-neutral by construction (D-015). Nothing here knows what a flight, hotel
or airport is — it reads a playbook, gathers options for whatever categories the
playbook names, scores them deterministically, and executes the steps in order.

    event → match template → expand with profile → discover → score → act

What the LLM does (Phase 3): choose which providers are worth querying, and
write the human-readable reason line. What Python does: every constraint check,
every cap, every number. See D-003.
"""
from __future__ import annotations

import asyncio
from decimal import Decimal

from app import executor as executor_mod
from app import policy, profiles, registry, scoring, templates


async def run(
    *,
    event: dict,
    profile_id: str,
    vertical: str,
    emit,
    adapter_name: str = "mock",
) -> dict:
    """Execute one contingency recovery, streaming trace events as it goes.

    Two shapes of playbook, one entry point: a template with `plans` compares
    whole recovery strategies first (D-018), a template with bare `steps` goes
    straight to execution.
    """
    if templates.load(vertical).get("plans"):
        from app import engine_plans
        return await engine_plans.run(event=event, profile_id=profile_id,
                                      vertical=vertical, emit=emit,
                                      adapter_name=adapter_name)

    tpl = templates.load(vertical)
    profile = profiles.load(profile_id)
    providers = registry.load(vertical)
    adapter = executor_mod.get(adapter_name)

    ledger = policy.Ledger(tpl["caps"])
    ctx = {"profile": profile, "event": event}
    chosen: dict[str, dict] = {}

    async def envelope():
        await emit({"type": "envelope", **ledger.status()})

    # --- 1. the trigger ----------------------------------------------------
    await emit({"type": "trace", "id": "trigger", "status": "done",
                "text": f"Trigger fired — {event['type']}",
                "detail": _summarise(event), "cost": None})
    await envelope()

    # --- 2. personalisation, made visible ----------------------------------
    notes = profiles.personalisation_notes(profile)
    await emit({"type": "trace", "id": "profile", "status": "done",
                "text": f"Loaded contingency profile for {profile['name']}",
                "detail": " · ".join(notes[:4]), "cost": None})
    for i, note in enumerate(notes[4:]):
        await emit({"type": "trace", "id": f"profile-{i}", "status": "done",
                    "text": note, "detail": None, "cost": None})

    await emit({"type": "trace", "id": "template", "status": "done",
                "text": f"Matched playbook — {tpl['name']}",
                "detail": templates.resolve(tpl["objective"], ctx).strip(),
                "cost": None})

    # --- 3. decide which providers are worth paying for --------------------
    wanted = _select_providers(tpl, providers, profile)
    declined = [p for p in providers if p not in wanted]

    # --- 4. discovery ------------------------------------------------------
    price = Decimal(str(tpl["discovery"]["price_per_query"]))
    options_by_category: dict[str, list[dict]] = {}

    for p in wanted:
        await emit({"type": "trace", "id": f"q-{p['id']}", "status": "running",
                    "text": f"Querying {p['name']}", "detail": p["category"],
                    "cost": f"${price}"})
        res = await adapter.discover(p, {})
        for opt in res["options"]:
            opt.setdefault("reliability", p.get("reliability", 0.5))
            options_by_category.setdefault(p["category"], []).append(opt)
        ledger.spent += price
        await emit({"type": "trace", "id": f"q-{p['id']}", "status": "done",
                    "text": f"Queried {p['name']}",
                    "detail": f"{len(res['options'])} option(s)", "cost": f"${price}"})
        await envelope()

    for p in declined:
        await emit({"type": "trace", "id": f"skip-{p['id']}", "status": "rejected",
                    "text": f"Declined to query {p['name']}",
                    "detail": _decline_reason(p, profile), "cost": None})

    # --- 5. work the steps in order, honouring dependencies ----------------
    for step in tpl["steps"]:
        if not _step_needed(step, chosen):
            await emit({"type": "trace", "id": f"s-{step['id']}", "status": "done",
                        "text": f"Step '{step['id']}' not required",
                        "detail": "condition not met given earlier choices", "cost": None})
            continue

        cap = float(tpl["caps"].get("per_category", {}).get(step.get("cap_key", ""), ledger.envelope))
        resolved = {k: templates.resolve(str(v), {**ctx, **chosen})
                    for k, v in (step.get("constraints") or {}).items()}
        step_view = {**step, "constraints": resolved}

        candidates = options_by_category.get(step["category"], [])
        if not candidates:
            await emit({"type": "error", "text": f"No options for '{step['id']}'",
                        "recovery": "step skipped; recovery continues"})
            continue

        ranked = scoring.rank(candidates, step=step_view, template=tpl,
                              profile=profile, cap=cap)

        # Evaluate EVERY candidate before choosing. Stopping at the first
        # acceptable option would hide the rejections, and a rejected option
        # with a stated reason is the clearest evidence of real reasoning —
        # a selection on its own proves nothing.
        picked = None
        for cand in ranked:
            opt = cand["option"]
            if not cand["eligible"]:
                await emit({"type": "trace", "id": f"rej-{opt['id']}", "status": "rejected",
                            "text": f"Rejected {opt['supplier']} — ${opt['price']}",
                            "detail": "; ".join(cand["failures"]), "cost": None})
                continue

            verdict = ledger.check(amount=opt["price"], category=step["category"],
                                   item_id=opt["id"])
            if not verdict["allowed"]:
                await emit({"type": "trace", "id": f"rej-{opt['id']}", "status": "rejected",
                            "text": f"Rejected {opt['supplier']} — ${opt['price']}",
                            "detail": f"{verdict['reason']} [{verdict['rule']}]", "cost": None})
                continue

            if picked is None:
                picked = (cand, verdict)          # best allowed option wins
            else:
                await emit({"type": "trace", "id": f"alt-{opt['id']}", "status": "rejected",
                            "text": f"Considered {opt['supplier']} — ${opt['price']}",
                            "detail": f"scored {cand['score']} vs {picked[0]['score']}",
                            "cost": None})

        if picked and picked[1]["needs_approval"]:
            await emit({"type": "approval", "reason": picked[1]["reason"],
                        "amount": f"${picked[0]['option']['price']}",
                        "option": picked[0]["option"]["label"]})

        if not picked:
            await emit({"type": "error", "text": f"No eligible option for '{step['id']}'",
                        "recovery": "every candidate failed a constraint or a cap"})
            continue

        cand, verdict = picked
        opt = cand["option"]
        memo = {"booking_ref": "", "decision_id": f"d_{step['id']}", "rule": verdict["rule"]}
        result = await adapter.purchase(_provider_for(providers, opt), opt, memo)

        ledger.commit(amount=opt["price"], category=step["category"], item_id=opt["id"])
        chosen[step["id"]] = {**opt.get("attributes", {}), "supplier": opt["supplier"],
                              "label": opt["label"], "price": opt["price"]}

        await emit({"type": "trace", "id": f"buy-{step['id']}", "status": "done",
                    "text": f"Booked {opt['supplier']} — {opt['label']}",
                    "detail": _why(cand, verdict), "cost": f"${opt['price']}"})
        await emit({"type": "purchase", "label": opt["label"], "amount": f"${opt['price']}",
                    "tx_hash": result["tx_hash"],
                    "explorer_url": executor_mod.EXPLORER,
                    "simulated": result.get("simulated", False)})
        await envelope()
        await asyncio.sleep(0.15)

    await emit({"type": "trace", "id": "done", "status": "done",
                "text": "Recovery complete",
                "detail": f"{len(chosen)} step(s) · ${ledger.spent:.2f} of ${ledger.envelope:.2f}",
                "cost": None})
    return {"chosen": chosen, "ledger": ledger.status()}


# --- helpers ---------------------------------------------------------------

def _summarise(event: dict) -> str:
    p = event.get("payload", {})
    bits = [str(v) for k, v in p.items() if k in ("supplier", "reference", "origin",
                                                  "destination", "reason")]
    return " · ".join(bits)


def _select_providers(tpl: dict, providers: list[dict], profile: dict) -> list[dict]:
    """Which providers are worth paying to query.

    Phase 2 heuristic: respect the playbook's max_queries and drop the provider
    the profile avoids with the weakest reliability. Phase 3 hands this to the
    LLM, which is where search-vs-commit reasoning belongs.
    """
    cats = tpl["discovery"]["categories"]
    ranked = [p for c in cats for p in providers if p["category"] == c]
    avoid = set(profile.get("preferences", {}).get("avoid_suppliers", []))
    ranked.sort(key=lambda p: (p["name"] in avoid, -p.get("reliability", 0)))
    return ranked[: tpl["discovery"]["max_queries"]]


def _decline_reason(p: dict, profile: dict) -> str:
    avoid = profile.get("preferences", {}).get("avoid_suppliers", [])
    if p["name"] in avoid:
        return (f"profile avoids {p['name']}; reliability {p.get('reliability')} — "
                "not worth the query cost or the delay")
    return f"reliability {p.get('reliability')} — one more query not worth the delay"


def _step_needed(step: dict, chosen: dict) -> bool:
    cond = step.get("needed_when")
    if not cond:
        return True
    ref, _, attr = cond.partition(".")
    return bool(chosen.get(ref, {}).get(attr))


def _provider_for(providers: list[dict], option: dict) -> dict:
    for p in providers:
        if p["name"] == option.get("supplier"):
            return p
    return providers[0]


def _why(cand: dict, verdict: dict) -> str:
    bits = [f"score {cand['score']}"]
    for label, delta in cand["breakdown"]["adjustments"]:
        bits.append(f"{label} ({delta:+})")
    bits.append(f"within {verdict['rule']}")
    return " · ".join(bits)
