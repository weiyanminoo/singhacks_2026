"""x402 client — real 402 → pay → retry.

Wraps `X402RequestsSession`, which handles the challenge, signs an XRPL payment
and retries. Verified working end to end at T+5 (see TRANSACTIONS.md).

Two things worth knowing:

1. The session is **synchronous** (`requests`), so calls run in a thread so as
   not to block the event loop while settlement completes (~10s per call).
2. The transaction hash comes back in the `payment-response` header, base64 JSON,
   under both `transaction` and `extensions.t54Attestation.paymentTxHash`. That
   hash is what the decision trace records — it is the receipt.

Header naming diverges from upstream x402 (`PAYMENT-SIGNATURE` rather than
`X-PAYMENT`), so a stock x402 client will not interoperate unchanged. See D-017.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os

from xrpl.wallet import Wallet

RPC_URL = os.getenv("XRPL_JSON_RPC", "https://s.altnet.rippletest.net:51234/")
MAX_DROPS = os.getenv("X402_MAX_DROPS", "50000")

STUB = False
_session = None


def _get_session(wallet: Wallet):
    global _session
    if _session is None:
        from x402_xrpl import X402RequestsSession
        _session = X402RequestsSession(wallet, rpc_url=RPC_URL, max_value=MAX_DROPS)
    return _session


def _decode_receipt(headers) -> dict:
    raw = headers.get("payment-response")
    if not raw:
        return {}
    try:
        d = json.loads(base64.b64decode(raw + "=" * (-len(raw) % 4)))
    except Exception:
        return {}
    att = (d.get("extensions") or {}).get("t54Attestation") or {}
    return {
        "tx_hash": d.get("transaction") or att.get("paymentTxHash"),
        "payer": d.get("payer"),
        "network": d.get("network"),
        "attestor": att.get("attestor"),
        "status": att.get("status"),
    }


def _fetch_sync(wallet: Wallet, url: str, timeout: int) -> dict:
    s = _get_session(wallet)
    r = s.get(url, timeout=timeout)
    receipt = _decode_receipt(r.headers)
    return {
        "ok": r.status_code == 200,
        "status": r.status_code,
        "data": r.json() if r.headers.get("content-type", "").startswith("application/json") else {},
        "paid": bool(receipt.get("tx_hash")),
        **receipt,
    }


def _probe_sync(url: str, timeout: int) -> dict:
    import requests
    r = requests.get(url, timeout=timeout)
    if r.status_code != 402:
        return {"challenged": False, "status": r.status_code}
    try:
        body = r.json()
        accept = (body.get("accepts") or [{}])[0]
    except Exception:
        return {"challenged": True, "status": 402}
    return {
        "challenged": True,
        "status": 402,
        "x402_version": body.get("x402Version"),
        "scheme": accept.get("scheme"),
        "network": accept.get("network"),
        "asset": accept.get("asset"),
        "amount_drops": accept.get("amount"),
        "pay_to": accept.get("payTo"),
        "invoice_id": (accept.get("extra") or {}).get("invoiceId"),
        "resource": (body.get("resource") or {}).get("url"),
        "description": (body.get("resource") or {}).get("description"),
    }


async def probe(url: str, *, timeout: int = 15) -> dict:
    """Fetch the 402 challenge WITHOUT paying, so the terms can be shown.

    The SDK settles the challenge internally, so a viewer only ever sees the
    result. This unpaid request surfaces what the provider is actually asking
    for — price, asset, recipient address, invoice id — before any money moves.
    It costs nothing on ledger and makes the mechanic legible instead of magic.
    """
    try:
        return await asyncio.to_thread(_probe_sync, url, timeout)
    except Exception as exc:
        return {"challenged": False, "error": str(exc)[:120]}


async def pay_and_fetch(wallet: Wallet, url: str, *, timeout: int = 90) -> dict:
    """Fetch a paid resource, settling the 402 challenge on XRPL.

    Never raises on a provider problem — a supplier that fails verification is a
    normal outcome the engine must route around, not an exception.
    """
    try:
        return await asyncio.to_thread(_fetch_sync, wallet, url, timeout)
    except Exception as exc:
        return {"ok": False, "status": 0, "data": {}, "paid": False,
                "error": f"{type(exc).__name__}: {exc}"}
