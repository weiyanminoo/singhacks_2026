# Phase 1 — XRPL foundation + app skeleton

**Status:** partial — M1 met; the one remaining item (an RLUSD-denominated
payment) is blocked on the faucet claim, not on code
**Time:** T+1
**Owner:** Claude Code (both workstreams; solo build)

## What we built

| File | What it does |
|---|---|
| `app/xrpl_ops.py` | Connect, sign, submit, wait for validation. Per-account locks, tickets, memos, `SourceTag`, live fee/reserve reads, epoch helpers. |
| `app/main.py` | FastAPI: `/` UI, `/health` live network values, `/stream` SSE, `/demo` scripted run. |
| `app/static/index.html` | Split layout — trace panel left, envelope right. Tailwind CDN + vanilla JS over SSE. No build step. |
| `app/x402_client.py` | Stub returning fake hashes so the loop and UI could be built before Phase 2. |

## How it works

**Concurrency.** Two independent problems, two fixes:

1. *Sequence collisions* — solved with **per-account** `asyncio.Lock`s, not one
   global lock. Collisions are per-account, so serialising independent wallets
   costs time and buys nothing (D-006a).
2. *Serialisation of the discovery leg* — solved with **Tickets**. `TicketCreate`
   pre-allocates sequence numbers; each payment then carries `TicketSequence`
   with `Sequence: 0` and can be submitted concurrently. `submit()` deliberately
   **skips the lock** when a transaction is ticketed — that is the whole point.

**Transport.** Measuring exposed that the bottleneck was not the ledger. See
D-014 and the numbers below.

**Memos.** `booking_memo()` writes
`MemoType = alternate/booking`, `MemoData = BK-7741|decision:d_014|rule:hotel_cap_6_25`,
both hex-encoded, alongside `SourceTag: 4021`. Decode with
`bytes.fromhex(memo_data).decode()`.

**Fees and reserves** come from `server_info` on our own node every time
(`network_costs()`), never from the mainnet JSON snapshots (D-007).

**Epoch helper.** Kept, but the useful direction is `ripple_to_unix`, not the
`unix_to_ripple` the plan named. `unix_to_ripple` existed for escrow's
`FinishAfter`/`CancelAfter`, and escrow was cut (D-011). What we still need is
the reverse: ledger `close_time` and transaction `date` fields are Ripple-epoch,
so displaying when a transaction landed requires converting *out* of it.

## Decisions made

- **D-014** — WebSocket transport instead of JSON-RPC, on measured evidence.

## What broke, and how we fixed it

**The 90-second story was quietly at risk, and only measurement showed it.**
The plan assumed a ~3–5s ledger close was the floor. Reality: a single
`submit_and_wait` over JSON-RPC took **13.6s**, so 7 sequential discovery
payments (~95s) would have consumed the entire budget before a single LLM token.
Tickets brought 7 concurrent payments to 21.8s; switching to WebSocket brought
the same work to **9.2s**. The ledger closes every ~2.5s, so the residual was
client-side polling, not consensus.

The lesson worth carrying: we would have "verified tickets work" at 21.8s and
moved on satisfied. Comparing against the actual ledger close time is what
exposed that most of the remaining time was ours, not the network's.

**Port 8000 was occupied** by Docker on the dev machine. `.claude/launch.json`
uses 8010 locally; the documented default in the README stays 8000.

## Deviations from PLAN.md

- Phase 0's "CLI-verified RLUSD payment via `xrpl-up`" was folded into this
  phase's payment work rather than run separately. The de-risking it existed for
  — proving connect/sign/submit/wait before app code — was already satisfied by
  the 9 `TrustSet` transactions in Phase 0, which take the identical path.
- The RLUSD-denominated payment is still outstanding. Everything around it is
  built and verified in XRP; only the amount type is unexercised.
- Roles A/B collapsed into one sequence (solo build).

## Verification

- 7/7 concurrent ticketed payments `tesSUCCESS`.
- Payments with `SourceTag` + `Memos` landed and verified; hashes in
  `TRANSACTIONS.md`.
- `/health` returns live testnet values in the browser header.
- **M1 met:** transaction hashes on testnet.xrpl.org **and** trace text streaming
  into a browser page. The demo run drives the envelope from $10.00 to $2.82 —
  matching the documented figures exactly ($0.14 discovery + $7.04 purchases).

| Measurement | Value |
|---|---|
| Ledger close | ~2.5s |
| Single payment, JSON-RPC → WebSocket | 13.6s → 4.6s |
| 7 concurrent ticketed, JSON-RPC → WebSocket | 21.8s → **9.2s** |
| Sequential JSON-RPC baseline (extrapolated) | ~95s |

## Feeds README sections

*XRPL integration* table, *Memo format*, and the performance half of
*Beyond the prototype*.
