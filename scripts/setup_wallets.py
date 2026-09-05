"""Create and fund the XRPL Testnet accounts alternate.ai needs.

    python scripts/setup_wallets.py accounts    # generate + faucet-fund, idempotent
    python scripts/setup_wallets.py trustlines  # RLUSD trust lines (needs ISSUER in .env)
    python scripts/setup_wallets.py recycle     # sweep vendor RLUSD back to session
    python scripts/setup_wallets.py show        # print addresses + balances

Seeds are written to wallets.json, which is gitignored. Never commit it.
"""
import json
import os
import pathlib
import sys

from dotenv import load_dotenv
from xrpl.clients import JsonRpcClient
from xrpl.models.requests import AccountInfo, AccountLines
from xrpl.models.transactions import TrustSet
from xrpl.models.amounts import IssuedCurrencyAmount
from xrpl.transaction import submit_and_wait
from xrpl.wallet import Wallet, generate_faucet_wallet

load_dotenv()

ROOT = pathlib.Path(__file__).resolve().parent.parent
STORE = ROOT / "wallets.json"
JSON_RPC = os.getenv("XRPL_JSON_RPC", "https://s.altnet.rippletest.net:51234/")

# 8 providers: 2 flight, 3 hotel, 2 ground, 1 status/waiver (D-004a).
VENDORS = [
    "flights_skyline", "flights_aeroconnect",
    "hotels_aurora", "hotels_transit_inn", "hotels_meridian",
    "ground_swiftcar", "ground_metrolink",
    "data_status",
]
ROLES = ["treasury", "session"] + VENDORS

client = JsonRpcClient(JSON_RPC)


def load():
    return json.loads(STORE.read_text()) if STORE.exists() else {}


def save(d):
    STORE.write_text(json.dumps(d, indent=2))
    os.chmod(STORE, 0o600)


def accounts():
    """Generate and faucet-fund any role that does not exist yet. Safe to re-run."""
    store = load()
    for role in ROLES:
        if role in store:
            print(f"  {role:22} exists  {store[role]['address']}")
            continue
        w = generate_faucet_wallet(client, debug=False)
        store[role] = {"address": w.address, "seed": w.seed}
        save(store)  # save after each, so a faucet failure never loses work
        print(f"  {role:22} FUNDED  {w.address}")
    print(f"\n{len(store)}/{len(ROLES)} accounts ready -> {STORE.name}")


def trustlines():
    """Set an RLUSD trust line on the session wallet and every vendor."""
    issuer = os.getenv("RLUSD_ISSUER")
    currency = os.getenv("RLUSD_CURRENCY", "524C555344000000000000000000000000000000")
    limit = os.getenv("RLUSD_TRUST_LIMIT", "10000")
    if not issuer:
        sys.exit("RLUSD_ISSUER not set in .env — see docs/phase-0-setup.md")

    store = load()
    for role in ["session"] + VENDORS:
        w = Wallet.from_seed(store[role]["seed"])
        tx = TrustSet(
            account=w.address,
            limit_amount=IssuedCurrencyAmount(currency=currency, issuer=issuer, value=limit),
        )
        r = submit_and_wait(tx, client, w)
        code = r.result["meta"]["TransactionResult"]
        print(f"  {role:22} {code}  {r.result['hash']}")
        if code != "tesSUCCESS":
            sys.exit(f"trust line failed for {role}: {code}")


def recycle():
    """Sweep all vendor RLUSD back to the session wallet, so the demo re-runs.

    The public faucet caps at 10 RLUSD/24h (D-009), which would allow roughly one
    end-to-end run per day. The vendors are our own accounts, so the envelope is
    recycled rather than consumed — only XRP fees are actually spent.
    """
    issuer = os.getenv("RLUSD_ISSUER")
    currency = os.getenv("RLUSD_CURRENCY", "524C555344000000000000000000000000000000")
    store = load()
    session = store["session"]["address"]
    total = 0.0
    for role in VENDORS:
        w = Wallet.from_seed(store[role]["seed"])
        lines = client.request(AccountLines(account=w.address)).result.get("lines", [])
        bal = next((l["balance"] for l in lines if l["currency"] == currency), "0")
        if float(bal) <= 0:
            continue
        from xrpl.models.transactions import Payment
        r = submit_and_wait(
            Payment(
                account=w.address,
                destination=session,
                amount=IssuedCurrencyAmount(currency=currency, issuer=issuer, value=bal),
            ),
            client, w,
        )
        code = r.result["meta"]["TransactionResult"]
        print(f"  {role:22} {code}  returned {bal}")
        if code == "tesSUCCESS":
            total += float(bal)
    print(f"\nrecycled {total} RLUSD back to session {session}")


def show():
    store = load()
    for role, v in store.items():
        info = client.request(AccountInfo(account=v["address"], ledger_index="validated")).result
        xrp = int(info["account_data"]["Balance"]) / 1_000_000 if "account_data" in info else 0
        lines = client.request(AccountLines(account=v["address"])).result.get("lines", [])
        iou = ", ".join(f"{l['balance']} {l['currency'][:4]}" for l in lines) or "-"
        print(f"  {role:22} {v['address']}  {xrp:>10.2f} XRP  {iou}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"
    {"accounts": accounts, "trustlines": trustlines, "recycle": recycle, "show": show}[cmd]()
