# TRANSACTIONS.md

Every successful XRPL transaction, appended **immediately** as it lands. Do not
batch this — reconstructing hashes at hour 23 is miserable, and the submission
explicitly requires transaction hashes or explorer references.

Network: **XRPL Testnet**
Explorer: `https://testnet.xrpl.org/transactions/{hash}`

**Scale note (D-009, D-012, D-016):** the demo runs a **10 XRP envelope**, not
$400. Purchases scale 1/40; discovery stays unscaled at 0.02 per query.
**Settlement is XRP, not RLUSD** — the testnet RLUSD faucet never dispensed
(D-016), so every account holds 0.00 RLUSD. The RLUSD trust lines below are real
and remain in place as evidence of the attempt. The UI renders amounts with a $
sign for legibility; the ledger moves XRP. Do not present these as dollars.

---

## Accounts

Real testnet accounts, created and funded T+0 by `scripts/setup_wallets.py`.
All hold 100 XRP and an RLUSD trust line (set successfully, never funded).

| Role | Address | Purpose |
|---|---|---|
| Treasury | `rQwmdaTDK2MkgjMmkcAXCAuRx3o4BpJL3j` | Holds the float. Never touched by the agent. |
| Session wallet | `r9Pwpy1iBRXFEeZdn8ix51tUJfoj2PCwD8` | **The spending ceiling is this XRP balance.** |
| Vendor: Skyline Air | `rwqggQdGuh8iPGJiBZLsTGP4GhytVukGeR` | Flight inventory + booking |
| Vendor: AeroConnect | `rn5D1RfpZine6vuSwT6VnQkT9mmjffW6ET` | Flight inventory + booking |
| Vendor: Aurora Grand | `r4tdKneC9ebjXYrdfpwiL9qLXZ9P9eWuqK` | Hotel inventory + booking |
| Vendor: Transit Inn | `rBNwjhcoy68gs9c7JckA4mF71W4KoYAmKn` | Hotel inventory + booking |
| Vendor: Meridian | `rrnffhbGZPu7wfvjXjThwxUPH6fCEcE9tu` | Hotel inventory + booking |
| Vendor: SwiftCar | `rJd6N2JLeQtYaaSkFU6Fpx8vAhh6CvnGLE` | Ground transport |
| Vendor: MetroLink | `rMeWHgWnsqxWjztYvwxCEH3kZKfbZWfYk9` | Ground transport |
| Vendor: Status Feed | `rwtGAc2QzvMkhcE1kZpiicegd1yfQj6Cky` | Flight status + waiver data |

RLUSD issuer (testnet): `rQhWct2fv4Vc4KRjRgMrxa8xPN9Zx9iLKV` ·
currency `524C555344000000000000000000000000000000`

Account explorer: `https://testnet.xrpl.org/accounts/{address}`

---

## Headline transactions for the submission

The three or four a reviewer should look at first. Fill these in last, chosen
from the demo run below.

| # | What it demonstrates | Type | Hash | Link |
|---|---|---|---|---|
| 1 | Envelope funding — the spending ceiling | Payment (XRP) | | |
| 2 | Discovery micro-payment via x402 | Payment (XRP) | | |
| 3 | Autonomous purchase with decision memo | Payment (XRP) | | |
| 4 | Concurrent discovery leg via pre-allocated tickets | TicketCreate | | |
| 5 | Failure recovery — vendor refund, agent reroutes | Payment (XRP) | | |
| 6 | Agent key delegation | SetRegularKey | | |

---

## Demo run — [timestamp]

Full transaction sequence from one clean end-to-end run. This is what we cite
in the README.

### Setup

| Time | Action | Type | Amount | Hash |
|---|---|---|---|---|
| | Fund session wallet | Payment | 10 XRP | |
| | Pre-allocate discovery tickets | TicketCreate | — | |
| | Delegate signing to agent | SetRegularKey | — | |

### Discovery payments (x402) — 7 queried, 1 declined

| # | Provider | Endpoint | Price | Hash |
|---|---|---|---|---|
| 1 | Skyline Air | `/flights/skyline/availability` | 0.02 XRP | |
| 2 | AeroConnect | `/flights/aeroconnect/availability` | 0.02 XRP | |
| 3 | Status Feed | `/data/status/waivers` | 0.02 XRP | |
| 4 | Aurora Grand | `/hotels/aurora/availability` | 0.02 XRP | |
| 5 | Transit Inn | `/hotels/transit-inn/availability` | 0.02 XRP | |
| 6 | Meridian | `/hotels/meridian/availability` | 0.02 XRP | |
| 7 | SwiftCar | `/ground/swiftcar/eta` | 0.02 XRP | |
| — | **MetroLink — DECLINED** | `/ground/metrolink/eta` | not paid | — |

**Discovery total:** _____ XRP across 7 transactions

> The 8th provider the agent *chose not to query* is the search-vs-commit
> decision. Record which one and the stated reason here: _____

### Purchases

| Item | Vendor | Amount | Decision ID | Policy rule | Hash |
|---|---|---|---|---|---|
| Seat SQ0842 06:40 | Skyline Air | $4.60 | `d_007` | `flight_arrival_before_0800` | |
| Room, 1 night | Transit Inn | $1.95 | `d_012` | `hotel_cap_6_25` | |
| Airport transfer | SwiftCar | $0.49 | `d_015` | `ground_cap_1_00` | |

**Envelope:** $10.00 → $2.82

### Refundable hold

Token escrow is **unavailable** for RLUSD on testnet — the issuer
`rQhWct2fv4Vc4KRjRgMrxa8xPN9Zx9iLKV` does not have `lsfAllowTrustLineLocking`
set (verified T+0, Flags `0x819a0000`). Cut-list item 1 applies: the hold is a
vendor-initiated refund `Payment`. See the failure path below and D-011.

### Failure path

| Step | Type | Hash | Notes |
|---|---|---|---|
| Payment to sold-out vendor | Payment (XRP) | | Vendor reported no inventory after settlement |
| Refund returned to session wallet | Payment (XRP) | | Vendor-initiated; escrow is the production design |
| Reroute purchase | Payment (XRP) | | Second-best option booked |

---

## Memo format

Every agent transaction carries `SourceTag` and `Memos` so any payment on the
explorer traces back to the decision and the rule that permitted it.

```
SourceTag: 4021
MemoType:  alternate/booking
MemoData:  BK-7741|decision:d_012|rule:hotel_cap_6_25
```

Decode with: `bytes.fromhex(memo_data).decode()`

---

## Append log

Raw running log. Newest at the bottom. Copy each hash here the moment it lands.

```
[HH:MM] <type> <amount> <purpose> <hash>
```

### T+4 · Phase 3 — agent purchases settled on XRPL, end to end

Settled in **XRP** (D-016): the testnet RLUSD faucet never dispensed, so all
accounts hold 0.00 RLUSD. Trust lines remain in place as evidence of the attempt.

Every payment carries `SourceTag: 4021` and a memo tying it to the decision and
the policy rule that permitted it. Decoded from the first one:

```
MemoType  alternate/booking
MemoData  sky-0844|decision:d_rebook_transport|rule:approval_threshold
```

| Step | Amount | Hash |
|---|---|---|
| Rebook transport (Skyline SQ0844) | 4.6 XRP | `57231C3918A5228F330BAC23940CC94B048F9D1D300389248228237BCB0DF8CA` |
| Overnight stay (Transit Inn) | 1.95 XRP | `5C0A11EE86B4DF8096B7E3E2F6DE2590E18AC8FF816A591B4E713C3AE86F75CF` |
| Ground transfer (SwiftCar) | 0.49 XRP | `8A00233D27BF3AE88A1542BEC4B06515848BED6267A4880FB1E2EE8FE00F543C` |

Second full run, same playbook, independently settled:
`2F37CBDDB05D886511B0760C72AE25666A92F28FCDBF77762732B88191B1AF22` ·
`0D268053388B21C3EBBAF42A2C3FE8779BD2C42C60D243D21690D5B5DE55DC6A` ·
`ACE522A79138366D028EDF1CCD04297E23ADBAC922FD53988C37CB1F5FE89908`

**x402 gating verified** on all 8 supplier endpoints — an unpaid GET returns a
real 402 with `x402Version: 2`, `scheme: exact`, `network: xrpl:1`, amount in
drops, and each supplier's own `payTo` address. Each endpoint is gated to its own
wallet: there is no merchant of record in the middle.

### T+1 · Phase 1 verification — payments, memos, tickets, concurrency

All XRP (RLUSD amount type still pending the faucet claim). Every one carries
`SourceTag: 4021`; the two below also carry a decoded booking memo.

| What | Result | Hash |
|---|---|---|
| Payment + SourceTag + Memo (JSON-RPC, smoke test) | tesSUCCESS | `0987438281379084FC0E674EFF7A52D06DA88BB247B1E36FCD147B9506656E6A` |
| Payment + SourceTag + Memo (WebSocket, after D-014) | tesSUCCESS | `6A073C92E38007BC1820CF51DA7B55230DCCD8383A95FED1878865EFA5F808A8` |
| `TicketCreate` ×8 → sequences 20492414–20492421 | tesSUCCESS | see account explorer |
| 3 concurrent ticketed payments | 3/3 tesSUCCESS | `47FB55EC…`, `827D5F10…`, `AF01FE94…` |
| **7 concurrent ticketed payments (real discovery leg)** | **7/7 tesSUCCESS** | 21.8s JSON-RPC → **9.2s WebSocket** |

**Measured latency** (same work, 7 concurrent ticketed payments):

| Path | Time |
|---|---|
| Sequential, JSON-RPC (extrapolated 7 × 13.6s) | ~95s |
| Concurrent via tickets, JSON-RPC | 21.8s |
| Concurrent via tickets, WebSocket | **9.2s** |

Ledger close observed at ~2.5s, so the residual is transport, not consensus.
See D-006a (tickets) and D-014 (transport).

### T+0 · Phase 0 setup — RLUSD trust lines (9 × TrustSet, all tesSUCCESS)

| Account | Hash |
|---|---|
| session | `D15101C8519C38AD0F3941775BB9A8E1B5058204203C680F72C93F0753548BFF` |
| flights_skyline | `A95ADF7107C2F5DB249949142D555FDEF9F89CB2CA99ED5CD3C13E3898BB346D` |
| flights_aeroconnect | `A6E673C8305590AA7739B73ACCD5AF6C070E0A631AAF0580DD2EA8B41F14A32A` |
| hotels_aurora | `5ACC9F85EE4BEE2F9AF9C9BA700C665BFFACC2402FE68E8E7D1A2AAFA048B03A` |
| hotels_transit_inn | `CDEC69B0A7823F837D9BEBBB402AAA8B260BD60CDEFD6AE7A33117C0C2F8B425` |
| hotels_meridian | `999E4B83700A43F3D03906CA2AA96790FE89C3E283F2D34632C0514BE0B9BEC9` |
| ground_swiftcar | `A9C9E4A6CFD9EA59F79FE351135683BE5EC866E57D5E8C99475934053F466B49` |
| ground_metrolink | `B0839A773A797617D518D40614E8AC2B00C92270C7FA178AE76B41CEFA6389DB` |
| data_status | `B384791634DBA41B23C1D538E04068BF912A81C86662E04284A0B473F14231AA` |
