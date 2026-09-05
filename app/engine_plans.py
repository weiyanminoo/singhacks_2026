"""Plan-based contingency recovery — the ContingencyOS flow (D-018).

Four stages, matching the four agents in the spec:

  1. Screening     classify the disruption, derive operating constraints
  2. Planning      compare cancel / postpone / relocate on the FREE tier, select
  3. Verification  pay x402 for LIVE confirmation of the selected plan only
  4. Settlement    escrow the venue, pay suppliers, release on evidence, refund

The split between stages 2 and 3 is the point: deliberation is free, and you
only spend money confirming the plan you actually intend to run.

Still domain-neutral — nothing here knows what a venue is.
"""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal

import httpx

from app import escrow as escrow_mod
from app import executor as executor_mod
from app import plans as plans_mod
from app import policy, profiles, registry, scoring, templates, x402_client, xrpl_ops

VENDORS = executor_mod.VENDORS_BASE


async def run(*, event: dict, profile_id: str, vertical: str, emit,
              adapter_name: str = "mock") -> dict:
    tpl = templates.load(vertical)
    profile = profiles.load(profile_id)
    providers = registry.load(vertical)
    live = adapter_name == "xrpl"

    trace: dict = {
        "event_id": event["id"], "event_type": event["type"],
        "severity": event.get("payload", {}).get("severity", "unknown"),
        "constraints": profile.get("constraints", {}),
        "plans_considered": [], "providers_considered": [], "payments": [],
        "selected_plan": None,
    }

    # ---------- 1. Screening ------------------------------------------------
    p = event.get("payload", {})
    await emit({"type": "agent", "agent": "screening", "status": "running"})
    await emit({"type": "trace", "id": "screen", "status": "done",
                "text": f"Disruption classified — {event['type']}, severity {p.get('severity')}",
                "detail": f"{p.get('venue')} · {p.get('cause')} · "
                          f"{p.get('hours_to_event')}h to event", "cost": None})
    if p.get("public_transport_disrupted"):
        await emit({"type": "trace", "id": "screen-2", "status": "done",
                    "text": "Operating constraint added: public transport around the "
                            "original site is unavailable", "detail": None, "cost": None})
    await emit({"type": "agent", "agent": "screening", "status": "done"})

    notes = profiles.personalisation_notes(profile)
    await emit({"type": "trace", "id": "profile", "status": "done",
                "text": f"Loaded contingency policy — {profile['org']}",
                "detail": " · ".join(notes[:3]), "cost": None})

    # ---------- 2. Planning (free tier) -------------------------------------
    await emit({"type": "agent", "agent": "planning", "status": "running"})
    catalogue = await _catalogue(providers, emit)
    relocate = next((pl for pl in tpl["plans"] if pl.get("steps")), None)
    estimates = _estimate(relocate, catalogue, tpl, profile)

    evaluated = plans_mod.evaluate(tpl, profile, {relocate["id"]: estimates})
    for pv in evaluated:
        c = pv["costs"]
        await emit({"type": "plan", "id": pv["id"], "label": pv["label"],
                    "feasible": pv["feasible"],
                    "total": f"{c['total_expected_cost']:,.0f}",
                    "cash": f"{c['direct_recovery']:,.0f}",
                    "components": {k: f"{v:,.0f}" for k, v in c.items()},
                    "rejected_because": pv["rejected_because"]})
        trace["plans_considered"].append({
            "plan": pv["id"],
            "status": "feasible" if pv["feasible"] else "rejected",
            "total_expected_cost": str(c["total_expected_cost"]),
            "reason": "; ".join(pv["rejected_because"]) or "within all constraints",
        })

    chosen, avoided = plans_mod.select(evaluated)
    if not chosen:
        await emit({"type": "error", "text": "No feasible recovery plan",
                    "recovery": "escalate to the organizer"})
        return {"trace": trace}

    trace["selected_plan"] = chosen["id"]
    await emit({"type": "trace", "id": "select", "status": "done",
                "text": f"Selected: {chosen['label']}",
                "detail": f"S${chosen['total']:,.0f} expected · avoids "
                          f"S${avoided['avoided_loss']:,.0f} versus {avoided['versus']}",
                "cost": None})
    await emit({"type": "agent", "agent": "planning", "status": "done"})

    if not chosen["plan"].get("steps"):
        return {"trace": trace}

    # ---------- 3. Verification (x402, paid) --------------------------------
    await emit({"type": "agent", "agent": "verification", "status": "running"})
    ledger = policy.Ledger(tpl["caps"])
    confirmed: dict[str, dict] = {}
    wallet = xrpl_ops.wallet("session")

    for step in chosen["plan"]["steps"]:
        picked = await _verify_step(step, tpl, profile, providers, catalogue,
                                    ledger, wallet, emit, trace, live)
        if picked:
            confirmed[step["id"]] = picked
        elif step.get("required"):
            await emit({"type": "error",
                        "text": f"No verifiable supplier for '{step['id']}'",
                        "recovery": "required step — escalating to the organizer"})
    await emit({"type": "agent", "agent": "verification", "status": "done"})

    # ---------- 4. Settlement ----------------------------------------------
    await emit({"type": "agent", "agent": "settlement", "status": "running"})
    result = await _settle(chosen, confirmed, tpl, providers, ledger, emit, trace, live)
    await emit({"type": "agent", "agent": "settlement", "status": "done"})

    trace["decision_hash"] = hashlib.sha256(
        json.dumps(trace, sort_keys=True, default=str).encode()).hexdigest()
    await emit({"type": "trace", "id": "done", "status": "done",
                "text": "Recovery complete",
                "detail": f"decision {trace['decision_hash'][:16]}… · "
                          f"S${ledger.spent:,.0f} committed of S${ledger.envelope:,.0f}",
                "cost": None})
    await emit({"type": "outcome",
                "committed": f"{ledger.spent:,.0f}",
                "unused": f"{ledger.remaining:,.0f}",
                "avoided_loss": f"{avoided['avoided_loss']:,.0f}",
                "decision_hash": trace["decision_hash"],
                **result})
    return {"trace": trace, "ledger": ledger.status()}


# --- stages ---------------------------------------------------------------

async def _catalogue(providers: list[dict], emit) -> dict[str, list[dict]]:
    """Free indicative tier. No payment — this is a rate card, not a booking."""
    out: dict[str, list[dict]] = {}
    async with httpx.AsyncClient(timeout=10) as c:
        for p in providers:
            try:
                r = await c.get(VENDORS + p["endpoint"])
                opts = r.json().get("options", [])
            except Exception as exc:
                await emit({"type": "trace", "id": f"cat-{p['id']}", "status": "rejected",
                            "text": f"{p['name']} catalogue unreachable",
                            "detail": str(exc)[:80], "cost": None})
                continue
            for o in opts:
                o.setdefault("reliability", p.get("reliability", 0.5))
                o["_provider"] = p["id"]
                out.setdefault(p["category"], []).append(o)
    await emit({"type": "trace", "id": "catalogue", "status": "done",
                "text": f"Indicative pricing gathered from {len(providers)} providers",
                "detail": "free tier — no payment required to compare plans",
                "cost": None})
    return out


def _estimate(plan: dict, catalogue: dict, tpl: dict, profile: dict) -> dict:
    """Cheapest option per step that passes the hard constraints."""
    est = {}
    for step in plan.get("steps", []):
        cap = float(tpl["caps"].get("per_category", {}).get(step.get("cap_key", ""), 1e12))
        cands = catalogue.get(step["category"], [])
        resolved = {k: templates.resolve(str(v), {"profile": profile})
                    for k, v in (step.get("constraints") or {}).items()}
        ranked = scoring.rank(cands, step={**step, "constraints": resolved},
                              template=tpl, profile=profile, cap=cap)
        best = next((r for r in ranked if r["eligible"]), None)
        if best:
            est[step["id"]] = {"price": best["option"]["price"],
                               "reliability": best["option"].get("reliability", 0.5)}
    return est


async def _verify_step(step, tpl, profile, providers, catalogue, ledger, wallet,
                       emit, trace, live) -> dict | None:
    """Rank candidates, then PAY to confirm the best one is really available.

    A supplier that passes the catalogue but fails live verification is the
    normal case this exists to catch — we fall through to the next candidate.
    """
    cap = float(tpl["caps"].get("per_category", {}).get(step.get("cap_key", ""), 1e12))
    resolved = {k: templates.resolve(str(v), {"profile": profile})
                for k, v in (step.get("constraints") or {}).items()}
    ranked = scoring.rank(catalogue.get(step["category"], []),
                          step={**step, "constraints": resolved},
                          template=tpl, profile=profile, cap=cap)

    # Emit every constraint rejection FIRST, before anything is chosen.
    # Returning on the first success would hide them, and a rejected option with
    # a stated reason is the clearest evidence that a decision was made — the
    # venue turned down for inaccessible transport is the whole argument.
    for cand in ranked:
        if cand["eligible"]:
            continue
        opt = cand["option"]
        prov = registry.get(providers, opt["_provider"])
        await emit({"type": "trace", "id": f"rej-{opt['id']}", "status": "rejected",
                    "text": f"Rejected {opt['supplier']} — S${float(opt['price']):,.0f}",
                    "detail": "; ".join(cand["failures"]), "cost": None})
        trace["providers_considered"].append(
            {"provider": prov["id"], "status": "rejected",
             "reason": "; ".join(cand["failures"])})

    for cand in ranked:
        if not cand["eligible"]:
            continue
        opt = cand["option"]
        prov = registry.get(providers, opt["_provider"])

        verdict = ledger.check(amount=opt["price"], category=step["category"],
                               item_id=opt["id"])
        if not verdict["allowed"]:
            await emit({"type": "trace", "id": f"rej-{opt['id']}", "status": "rejected",
                        "text": f"Rejected {opt['supplier']} — S${float(opt['price']):,.0f}",
                        "detail": f"{verdict['reason']} [{verdict['rule']}]", "cost": None})
            continue

        # pay for live confirmation
        url = VENDORS + prov["endpoint"] + "/verify"
        await emit({"type": "trace", "id": f"v-{prov['id']}", "status": "running",
                    "text": f"Paying for live verification — {prov['name']}",
                    "detail": "x402", "cost": tpl["discovery"]["price_display"]})
        res = (await x402_client.pay_and_fetch(wallet, url)) if live else \
              {"ok": True, "data": {"verified": True}, "paid": False, "tx_hash": None}

        if res.get("tx_hash"):
            await emit({"type": "x402", "provider": prov["name"],
                        "amount_xrp": "0.02", "display": tpl["discovery"]["price_display"],
                        "tx_hash": res["tx_hash"],
                        "explorer_url": executor_mod.EXPLORER, "status": res.get("status")})
            trace["payments"].append({"kind": "x402", "provider": prov["id"],
                                      "tx_hash": res["tx_hash"]})

        body = res.get("data", {})
        if not res.get("ok") or body.get("verified") is False:
            reason = body.get("reason") or res.get("error") or "unavailable"
            await emit({"type": "trace", "id": f"v-{prov['id']}", "status": "rejected",
                        "text": f"{prov['name']} failed verification",
                        "detail": f"{reason} — falling back to the next supplier",
                        "cost": tpl["discovery"]["price_display"]})
            trace["providers_considered"].append(
                {"provider": prov["id"], "status": "failed_verification", "reason": reason})
            continue

        await emit({"type": "trace", "id": f"v-{prov['id']}", "status": "done",
                    "text": f"Confirmed {prov['name']}",
                    "detail": f"hold {body.get('hold_reference','—')} · "
                              f"expires in {body.get('hold_expires_minutes','—')} min",
                    "cost": tpl["discovery"]["price_display"]})
        trace["providers_considered"].append({"provider": prov["id"], "status": "confirmed"})
        return {"option": opt, "provider": prov, "verdict": verdict,
                "hold": body.get("hold_reference")}
    return None


async def _settle(chosen, confirmed, tpl, providers, ledger, emit, trace, live) -> dict:
    """Escrow the largest commitment, pay the rest, release on evidence, refund."""
    nominal = int(float(tpl["settlement"]["nominal_xrp"]) * 1_000_000)
    esc_nominal = int(float(tpl["settlement"]["escrow_nominal_xrp"]) * 1_000_000)
    adapter = executor_mod.get("xrpl" if live else "mock")
    out = {"escrow": None, "milestone": None, "refund": None}

    for step_id, pick in confirmed.items():
        opt, prov, verdict = pick["option"], pick["provider"], pick["verdict"]
        sgd = float(opt["price"])
        memo = {"booking_ref": pick.get("hold") or opt["id"],
                "decision_id": f"d_{chosen['id']}_{step_id}", "rule": verdict["rule"]}

        if verdict["needs_approval"]:
            await emit({"type": "approval", "reason": verdict["reason"],
                        "amount": f"S${sgd:,.0f}", "option": opt["label"]})

        if step_id == "replacement_venue" and live:
            cond, ful = escrow_mod.make_condition(
                f"{opt['id']}|{pick.get('hold')}|milestone:setup_verified")
            c = await escrow_mod.create(from_role="session",
                                        to_role=prov["wallet_role"], drops=esc_nominal,
                                        condition=cond, memo=memo)
            await emit({"type": "xrpl", "kind": "EscrowCreate",
                        "label": f"{opt['supplier']} — funds locked",
                        "display": f"S${sgd:,.0f}", "nominal_xrp": tpl["settlement"]["escrow_nominal_xrp"],
                        "tx_hash": c["tx_hash"], "explorer_url": executor_mod.EXPLORER})
            trace["payments"].append({"kind": "escrow_create", "tx_hash": c["tx_hash"]})
            out["escrow"] = c["tx_hash"]

            f = await escrow_mod.finish(owner_role="session", submitter_role="session",
                                        offer_sequence=c["offer_sequence"],
                                        condition=cond, fulfillment=ful)
            await emit({"type": "xrpl", "kind": "EscrowFinish",
                        "label": "Setup milestone verified — funds released",
                        "display": f"S${sgd:,.0f}", "nominal_xrp": tpl["settlement"]["escrow_nominal_xrp"],
                        "tx_hash": f["tx_hash"], "explorer_url": executor_mod.EXPLORER})
            trace["payments"].append({"kind": "escrow_finish", "tx_hash": f["tx_hash"]})
            out["milestone"] = f["tx_hash"]
        else:
            r = await adapter.purchase(prov, {**opt, "price": nominal / 1_000_000}, memo)
            await emit({"type": "xrpl", "kind": "Payment",
                        "label": f"{opt['supplier']} — {opt['label']}",
                        "display": f"S${sgd:,.0f}", "nominal_xrp": tpl["settlement"]["nominal_xrp"],
                        "tx_hash": r["tx_hash"], "explorer_url": executor_mod.EXPLORER,
                        "simulated": r.get("simulated", False)})
            trace["payments"].append({"kind": "payment", "provider": prov["id"],
                                      "tx_hash": r["tx_hash"]})

        ledger.commit(amount=opt["price"], category=prov["category"], item_id=opt["id"])
        await emit({"type": "envelope", **ledger.status()})

    if live and ledger.remaining > 0:
        r = await xrpl_ops.pay("session", xrpl_ops.address("treasury"), nominal,
                               asset="XRP", booking_ref="REFUND",
                               decision_id=f"d_{chosen['id']}", rule="unused_contingency")
        await emit({"type": "xrpl", "kind": "Refund",
                    "label": "Unused contingency returned to organizer",
                    "display": f"S${ledger.remaining:,.0f}",
                    "nominal_xrp": tpl["settlement"]["nominal_xrp"],
                    "tx_hash": r["tx_hash"], "explorer_url": executor_mod.EXPLORER})
        trace["payments"].append({"kind": "refund", "tx_hash": r["tx_hash"]})
        out["refund"] = r["tx_hash"]
    return out
