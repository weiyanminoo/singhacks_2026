"""Execution adapters.

The engine calls `discover()` and `purchase()` and cannot tell which adapter is
underneath. That boundary is what let the whole product be built and demoed
before the payment path was real, and it is what will let the XRPL adapter drop
in during Phase 3 without touching engine logic.

- `mock`  — instant, no ledger. Fake but well-formed hashes.
- `xrpl`  — real XRPL settlement via xrpl_ops (Phase 3).
"""
from __future__ import annotations

import os
import secrets

import httpx

VENDORS_BASE = os.getenv("VENDORS_BASE", "http://127.0.0.1:8011")
EXPLORER = "https://testnet.xrpl.org/transactions/"


class Adapter:
    name = "base"

    async def discover(self, provider: dict, context: dict) -> dict:
        raise NotImplementedError

    async def purchase(self, provider: dict, option: dict, memo: dict) -> dict:
        raise NotImplementedError


class MockAdapter(Adapter):
    """No ledger. Options come from the real vendor app; settlement is faked."""

    name = "mock"

    async def discover(self, provider: dict, context: dict) -> dict:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(VENDORS_BASE + provider["endpoint"], params=context)
            r.raise_for_status()
            data = r.json()
        return {
            "ok": True,
            "options": data.get("options", []),
            "price_paid": provider["price"],
            "tx_hash": secrets.token_hex(32).upper(),
            "simulated": True,
        }

    async def purchase(self, provider: dict, option: dict, memo: dict) -> dict:
        return {
            "ok": True,
            "tx_hash": secrets.token_hex(32).upper(),
            "confirmation_code": "BK-" + secrets.token_hex(3).upper(),
            "simulated": True,
        }


class XrplAdapter(Adapter):
    """Real settlement on XRPL Testnet. Wired in Phase 3."""

    name = "xrpl"

    def __init__(self, asset: str = "XRP"):
        self.asset = asset

    async def discover(self, provider: dict, context: dict) -> dict:
        raise NotImplementedError("Phase 3 — x402 402→pay→retry")

    async def purchase(self, provider: dict, option: dict, memo: dict) -> dict:
        raise NotImplementedError("Phase 3 — RLUSD/XRP Payment with memo")


def get(name: str = "mock") -> Adapter:
    return {"mock": MockAdapter, "xrpl": XrplAdapter}[name]()


def explorer_url(tx_hash: str) -> str:
    return EXPLORER + tx_hash
