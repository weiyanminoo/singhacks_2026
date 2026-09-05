"""x402 client — STUB for Phase 1.

Returns plausible fake hashes so the agent loop and UI can be built and tested
before the real 402 -> pay -> retry path lands in Phase 2. The signature is the
one agreed in CLAUDE.md's interface contract and will not change when the real
implementation replaces the body.

Phase 2 replaces this with `x402-xrpl` (D-010) against the t54 testnet
facilitator. If that facilitator enforces a minimum price above $0.02, STOP AND
ASK rather than picking a fallback (D-012).
"""
import secrets

STUB = True


def _fake_hash() -> str:
    return secrets.token_hex(32).upper()


async def pay_and_fetch(provider_id: str, path: str, params: dict, max_price: str) -> dict:
    """Query a paid provider endpoint, settling the 402 challenge on XRPL.

    Phase 1: returns a fake hash and empty data. Phase 2: real.
    """
    return {
        "ok": True,
        "data": {},
        "price_paid": max_price,
        "tx_hash": _fake_hash(),
        "ledger_index": 0,
        "stub": True,
    }
