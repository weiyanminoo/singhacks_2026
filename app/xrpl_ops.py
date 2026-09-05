"""XRPL operations for alternate.ai. Testnet only.

Two things here are deliberate and worth knowing before you change them:

1. **Per-account locks, not one global lock** (D-006a). Sequence collisions are
   per-account, so serialising independent wallets buys nothing and costs time.
2. **Ticketed transactions skip the lock entirely.** That is the whole point of
   pre-allocating tickets: each carries its own sequence number, so the discovery
   leg can fire concurrently instead of one ledger close at a time.
3. **WebSocket, not JSON-RPC** (D-014). Measured on the real 7-payment discovery
   leg: JSON-RPC 21.8s, WebSocket 9.2s. The ledger closes every ~2.5s, so most of
   the JSON-RPC time was client-side polling, not consensus.

Errors are never swallowed. A non-tesSUCCESS result raises.
"""
import asyncio
import json
import os
import pathlib

from dotenv import load_dotenv
from xrpl.asyncio.clients import AsyncWebsocketClient
from xrpl.asyncio.transaction import submit_and_wait
from xrpl.models.amounts import IssuedCurrencyAmount
from xrpl.models.requests import AccountObjects, ServerInfo
from xrpl.models.transactions import Memo, Payment, TicketCreate
from xrpl.wallet import Wallet

load_dotenv()

ROOT = pathlib.Path(__file__).resolve().parent.parent
WSS = os.getenv("XRPL_WSS", "wss://s.altnet.rippletest.net:51233")
RLUSD_CURRENCY = os.getenv("RLUSD_CURRENCY", "524C555344000000000000000000000000000000")
RLUSD_ISSUER = os.getenv("RLUSD_ISSUER", "")
SOURCE_TAG = int(os.getenv("AGENT_SOURCE_TAG", "4021"))

# Seconds between the Unix epoch and the Ripple epoch (2000-01-01).
# Ledger `close_time` and transaction `date` fields are Ripple-epoch, so the
# direction we actually need is ripple -> unix when displaying when a tx landed.
RIPPLE_EPOCH = 946_684_800

client = AsyncWebsocketClient(WSS)

_locks: dict[str, asyncio.Lock] = {}


class XRPLError(RuntimeError):
    """A transaction was submitted and the ledger rejected it."""


async def ensure_open() -> None:
    """Open the shared WebSocket if it is not already. Cheap to call repeatedly."""
    if not client.is_open():
        await client.open()


def unix_to_ripple(ts: float) -> int:
    return int(ts) - RIPPLE_EPOCH


def ripple_to_unix(ts: float) -> int:
    return int(ts) + RIPPLE_EPOCH


def to_hex(s: str) -> str:
    return s.encode().hex().upper()


def wallet(role: str) -> Wallet:
    """Load a wallet by role from wallets.json (gitignored)."""
    store = json.loads((ROOT / "wallets.json").read_text())
    return Wallet.from_seed(store[role]["seed"])


def address(role: str) -> str:
    return json.loads((ROOT / "wallets.json").read_text())[role]["address"]


def booking_memo(booking_ref: str, decision_id: str, rule: str) -> Memo:
    """`BK-7741|decision:d_014|rule:hotel_cap_6_25` — decode with bytes.fromhex()."""
    return Memo(
        memo_type=to_hex("alternate/booking"),
        memo_data=to_hex(f"{booking_ref}|decision:{decision_id}|rule:{rule}"),
    )


def rlusd(value) -> IssuedCurrencyAmount:
    if not RLUSD_ISSUER:
        raise XRPLError("RLUSD_ISSUER is not set in .env")
    return IssuedCurrencyAmount(currency=RLUSD_CURRENCY, issuer=RLUSD_ISSUER, value=str(value))


async def network_costs() -> dict:
    """Live fee and reserve values from OUR node (D-007).

    Never read these from the mainnet JSON snapshots — those are for README
    Feasibility claims only.
    """
    await ensure_open()
    info = (await client.request(ServerInfo())).result["info"]
    led = info["validated_ledger"]
    return {
        "base_fee_xrp": led["base_fee_xrp"],
        "reserve_base_xrp": led["reserve_base_xrp"],
        "reserve_inc_xrp": led["reserve_inc_xrp"],
        "network_id": info.get("network_id"),
        "ledger_index": led["seq"],
    }


async def submit(tx, w: Wallet) -> dict:
    """Sign, submit, wait for validation. Raises XRPLError on ledger rejection.

    Ticketed transactions bypass the per-account lock, because their sequence is
    already reserved and cannot collide.
    """
    await ensure_open()
    ticketed = getattr(tx, "ticket_sequence", None) is not None
    if ticketed:
        res = await submit_and_wait(tx, client, w)
    else:
        lock = _locks.setdefault(w.address, asyncio.Lock())
        async with lock:
            res = await submit_and_wait(tx, client, w)

    code = res.result["meta"]["TransactionResult"]
    if code != "tesSUCCESS":
        raise XRPLError(f"{type(tx).__name__} failed: {code} (hash {res.result.get('hash')})")
    return {
        "ok": True,
        "tx_hash": res.result["hash"],
        "ledger_index": res.result.get("ledger_index"),
        "code": code,
    }


async def create_tickets(role: str, count: int) -> list[int]:
    """Pre-allocate `count` tickets so payments can be submitted concurrently.

    Each ticket is a ledger object costing one owner reserve (0.2 XRP today).
    """
    await ensure_open()
    w = wallet(role)
    await submit(TicketCreate(account=w.address, ticket_count=count), w)
    objs = (await client.request(
        AccountObjects(account=w.address, type="ticket")
    )).result["account_objects"]
    return sorted(o["TicketSequence"] for o in objs)


async def pay(
    from_role: str,
    to_address: str,
    value,
    *,
    asset: str = "RLUSD",
    booking_ref: str = "",
    decision_id: str = "",
    rule: str = "",
    ticket: int | None = None,
) -> dict:
    """One payment, tagged and memoed so the explorer traces back to a decision.

    `asset="XRP"` takes a value in drops (string of integer drops).
    """
    w = wallet(from_role)
    amount = rlusd(value) if asset == "RLUSD" else str(value)
    memos = [booking_memo(booking_ref, decision_id, rule)] if booking_ref else None
    tx = Payment(
        account=w.address,
        destination=to_address,
        amount=amount,
        source_tag=SOURCE_TAG,
        memos=memos,
        sequence=0 if ticket else None,
        ticket_sequence=ticket,
    )
    return await submit(tx, w)
