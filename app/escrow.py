"""XRPL escrow with crypto-conditions (D-019).

Funds are locked against a **PREIMAGE-SHA-256 condition derived from the
milestone evidence hash**, and released only when that evidence is presented as
the fulfillment. Release is driven by proof, not by a clock — which is what
makes escrow more than decoration here.

D-011 cut escrow because issued-token locking needs the issuer to set
`lsfAllowTrustLineLocking`. That constraint died with D-016: settlement is
native XRP, which has no issuer.

Condition encoding is the fiddly part. The XRPL wire format for a 32-byte
PREIMAGE-SHA-256 is:

    condition   = A0258020 <sha256(preimage)> 810120
    fulfillment = A0228020 <preimage>

`EscrowFinish` also costs more than a normal transaction — 330 drops plus 10 per
16 bytes of fulfillment — so the fee is set explicitly rather than autofilled.
"""
from __future__ import annotations

import hashlib
import os

from xrpl.models.requests import AccountObjects, Tx
from xrpl.models.transactions import EscrowCancel, EscrowCreate, EscrowFinish

from app import xrpl_ops


def make_condition(evidence: bytes | str | None = None) -> tuple[str, str]:
    """Return (condition, fulfillment) hex for a milestone.

    Passing the evidence makes the preimage *derived from the thing being
    proved*, so the fulfillment is not an arbitrary secret — it is the evidence.
    """
    if evidence is None:
        preimage = os.urandom(32)
    else:
        raw = evidence.encode() if isinstance(evidence, str) else evidence
        preimage = hashlib.sha256(raw).digest()
    digest = hashlib.sha256(preimage).digest()
    condition = "A0258020" + digest.hex().upper() + "810120"
    fulfillment = "A0228020" + preimage.hex().upper()
    return condition, fulfillment


def finish_fee(fulfillment: str) -> str:
    """330 drops base + 10 drops per 16 bytes of fulfillment, with headroom."""
    nbytes = len(fulfillment) // 2
    return str(330 + 10 * ((nbytes + 15) // 16) + 100)


async def create(*, from_role: str, to_role: str, drops: int, condition: str,
                 cancel_after_s: int = 3600, memo: dict | None = None) -> dict:
    """Lock funds. `cancel_after` is the escape hatch if the milestone never lands."""
    w = xrpl_ops.wallet(from_role)
    memos = None
    if memo:
        memos = [xrpl_ops.booking_memo(memo.get("booking_ref", ""),
                                       memo.get("decision_id", ""),
                                       memo.get("rule", ""))]
    import time
    tx = EscrowCreate(
        account=w.address,
        destination=xrpl_ops.address(to_role),
        amount=str(drops),
        condition=condition,
        cancel_after=xrpl_ops.unix_to_ripple(time.time() + cancel_after_s),
        source_tag=xrpl_ops.SOURCE_TAG,
        memos=memos,
    )
    res = await xrpl_ops.submit(tx, w)
    res["offer_sequence"] = await _sequence_of(res["tx_hash"])
    return res


async def finish(*, owner_role: str, submitter_role: str, offer_sequence: int,
                 condition: str, fulfillment: str) -> dict:
    """Release the funds by presenting the evidence."""
    w = xrpl_ops.wallet(submitter_role)
    tx = EscrowFinish(
        account=w.address,
        owner=xrpl_ops.address(owner_role),
        offer_sequence=offer_sequence,
        condition=condition,
        fulfillment=fulfillment,
        fee=finish_fee(fulfillment),
    )
    return await xrpl_ops.submit(tx, w)


async def cancel(*, owner_role: str, submitter_role: str, offer_sequence: int) -> dict:
    """Return locked funds to the owner once `cancel_after` has passed."""
    w = xrpl_ops.wallet(submitter_role)
    return await xrpl_ops.submit(
        EscrowCancel(account=w.address, owner=xrpl_ops.address(owner_role),
                     offer_sequence=offer_sequence), w)


async def _sequence_of(tx_hash: str) -> int:
    """EscrowFinish needs the CREATE's sequence, which is not in the result."""
    await xrpl_ops.ensure_open()
    r = (await xrpl_ops.client.request(Tx(transaction=tx_hash))).result
    tx = r.get("tx_json", r)
    return tx.get("Sequence") or tx.get("TicketSequence")


async def outstanding(role: str) -> list[dict]:
    await xrpl_ops.ensure_open()
    r = await xrpl_ops.client.request(
        AccountObjects(account=xrpl_ops.address(role), type="escrow"))
    return r.result.get("account_objects", [])
