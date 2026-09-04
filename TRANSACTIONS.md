# TRANSACTIONS.md

Every successful XRPL transaction, appended **immediately** as it lands. Do not
batch this — reconstructing hashes at hour 23 is miserable, and the submission
explicitly requires transaction hashes or explorer references.

Network: **XRPL Testnet**
Explorer: `https://testnet.xrpl.org/transactions/{hash}`

---

## Accounts

| Role | Address | Purpose |
|---|---|---|
| Treasury | `rXXXX...` | Holds the float. Never touched by the agent. |
| Session wallet | `rXXXX...` | Funded with exactly the envelope. **The spending ceiling is this balance.** |
| Vendor: Skyline Air | `rXXXX...` | Flight inventory + booking |
| Vendor: AeroConnect | `rXXXX...` | Flight inventory + booking |
| Vendor: Aurora Grand | `rXXXX...` | Hotel inventory + booking |
| Vendor: Transit Inn | `rXXXX...` | Hotel inventory + booking |
| Vendor: SwiftCar | `rXXXX...` | Ground transport |
| Vendor: Status Feed | `rXXXX...` | Flight status + waiver data |

Account explorer: `https://testnet.xrpl.org/accounts/{address}`

---

## Headline transactions for the submission

The three or four a reviewer should look at first. Fill these in last, chosen
from the demo run below.

| # | What it demonstrates | Type | Hash | Link |
|---|---|---|---|---|
| 1 | Envelope funding — the spending ceiling | Payment (RLUSD) | | |
| 2 | Discovery micro-payment via x402 | Payment (XRP) | | |
| 3 | Autonomous purchase with decision memo | Payment (RLUSD) | | |
| 4 | Refundable hold created | EscrowCreate | | |
| 5 | Failure recovery — hold cancelled, funds returned | EscrowCancel | | |
| 6 | Agent key delegation | SetRegularKey | | |

---

## Demo run — [timestamp]

Full transaction sequence from one clean end-to-end run. This is what we cite
in the README.

### Setup

| Time | Action | Type | Amount | Hash |
|---|---|---|---|---|
| | Fund session wallet | Payment | $400.00 RLUSD | |
| | Delegate signing to agent | SetRegularKey | — | |

### Discovery payments (x402)

| # | Provider | Endpoint | Price | Hash |
|---|---|---|---|---|
| 1 | Skyline Air | `/flights/skyline/availability` | 0.02 XRP | |
| 2 | AeroConnect | `/flights/aeroconnect/availability` | 0.02 XRP | |
| 3 | Status Feed | `/data/status/waivers` | 0.02 XRP | |
| 4 | Aurora Grand | `/hotels/aurora/availability` | 0.02 XRP | |
| 5 | Transit Inn | `/hotels/transit-inn/availability` | 0.02 XRP | |
| 6 | Bay Lodge | `/hotels/bay-lodge/availability` | 0.02 XRP | |
| 7 | SwiftCar | `/ground/swiftcar/eta` | 0.02 XRP | |
| 8 | GoRide | `/ground/goride/eta` | 0.02 XRP | |

**Discovery total:** _____ XRP across 8 transactions

> Note the 4th hotel provider the agent *chose not to query* — the search-vs-commit
> decision. Record which one and the stated reason here: _____

### Purchases

| Item | Vendor | Amount | Decision ID | Policy rule | Hash |
|---|---|---|---|---|---|
| Seat SQ0842 06:40 | Skyline Air | $184.00 | `d_007` | `flight_arrival_before_0800` | |
| Room, 1 night | Transit Inn | $78.00 | `d_012` | `hotel_cap_250` | |
| Airport transfer | SwiftCar | $19.60 | `d_015` | `ground_cap_40` | |

**Envelope:** $400.00 → $118.40

### Escrow

| Action | Type | Amount | Hash |
|---|---|---|---|
| Hotel hold created | EscrowCreate | | |
| Released on check-in | EscrowFinish | | |

### Failure path

| Step | Type | Hash | Notes |
|---|---|---|---|
| Payment to sold-out vendor | Payment | | Vendor reported no inventory after settlement |
| Hold cancelled, funds returned | EscrowCancel | | Automatic, no human involved |
| Reroute purchase | Payment | | Second-best option booked |

---

## Memo format

Every agent transaction carries `SourceTag` and `Memos` so any payment on the
explorer traces back to the decision and the rule that permitted it.

```
SourceTag: 4021
MemoType:  alternate/booking
MemoData:  BK-7741|decision:d_012|rule:hotel_cap_250
```

Decode with: `bytes.fromhex(memo_data).decode()`

---

## Append log

Raw running log. Newest at the bottom. Copy each hash here the moment it lands.

```
[HH:MM] <type> <amount> <purpose> <hash>
```

