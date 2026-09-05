# ContingencyOS

> **Event-triggered programmable payment workflow for event organizers.**
> When a venue becomes unusable hours before an event, an AI agent decides
> whether to relocate, postpone or refund — then executes that decision with
> real money, inside a budget the organizer pre-authorised.

**SingHacks 2026 — Build an AI-Native Business on XRPL**
Network: **XRPL Testnet only.** No EVM sidechain, no other chain.

---

## What is real, what is simulated

Stated up front, because everything below depends on it.

| | |
|---|---|
| **Real** | Every XRPL transaction. x402 payments settle on Testnet against the t54 facilitator. Escrow uses genuine crypto-conditions. The agent's decisions, the policy engine, the spending controls and the failure recovery all run for real. |
| **Simulated** | The eight suppliers. Real venue, AV and catering APIs require commercial onboarding measured in weeks. Integration path is in [Beyond the prototype](#beyond-the-prototype). |
| **Two-layer money** | S$ figures are the organizer's **business layer**. They appear in the UI and ride inside transaction memos. On-ledger amounts are **nominal testnet XRP** — 0.02 XRP per verification, 0.1 XRP per settlement. **The XRP amount is not the S$ amount and we never claim it is.** |

**What the ledger genuinely proves:** the commitment, its ordering, and its
linkage to the decision and the policy rule that produced it. That is a stronger
claim than a number that happens to match a fiat figure, and it is the one we
make.

---

## The problem

At 9:00 a.m., two hours before a 1,000-person conference, the venue floods.

The organizer must now decide whether to cancel, postpone or relocate — and
simultaneously handle venue deposits, attendee refunds, exhibitors, catering, AV,
transport and supplier payments.

**The problem is not that the organizer lacks a contingency plan. It is that the
plan cannot execute fast enough.** A human can recommend a replacement venue in
ten minutes. But by the time finance approves the spend, the venue, the AV crew
and the transport capacity are gone — taken by whoever moved first.

Recovery is a race, and the binding constraint is authorisation latency, not
judgement.

---

## The product

The organizer sets a contingency policy in advance: budget, capacity floor, hard
constraints, and how much the agent may spend without asking. A trigger loop
watches for disruption events. When one fires:

1. **Screening** classifies the disruption and derives new operating constraints
2. **Planning** compares every recovery plan on total expected cost and rejects
   the infeasible ones
3. **Verification** pays providers, per query, to confirm what is *actually*
   available right now
4. **Settlement** escrows the venue, pays suppliers, releases on verified
   milestones, and refunds what it did not use

**Target customer:** conference and exhibition organizers, and the PCOs and
venues that carry disruption risk on their balance sheet. The buyer is the
organization; the beneficiaries are its attendees.

---

## Why this needs autonomous payments

The product test, applied honestly:

- **Remove the AI agent** → nothing evaluates competing recovery plans against
  capacity, deadline, accessibility and budget simultaneously. You are back to a
  human with a spreadsheet at 9 a.m.
- **Remove autonomous payments** → the agent can recommend but not reserve.
  Scarce replacement capacity is gone before approval returns. Same agent, same
  data, worse outcome.
- **Remove XRPL** → no independently verifiable record of which decision spent
  which money under which rule. The audit trail becomes a log file the vendor
  controls.

And specifically on **paid verification**: comparing plans is free — indicative
pricing is a rate card. Confirming that a venue is genuinely free tonight costs
two cents, because *that* is the information which expires. In our recorded run
the agent picks the cheaper AV supplier, pays to verify, discovers the crew is
committed elsewhere, and reroutes to the backup. A free lookup would have booked
an unavailable supplier.

---

## Architecture

```
   Event sources                Organizer policy            Recovery playbooks
   poll · webhook · manual      profiles/*.json             verticals/*/template.yaml
            \                          |                          /
             +------------> Trigger evaluator <------------------+
                                    |
        +---------------------------+----------------------------+
        |            THE ENGINE — no domain logic inside          |
        |                                                         |
        |   Screening  ->  Planning  ->  Verification  ->  Settlement
        |   classify       compare        pay to confirm    escrow, pay,
        |   severity       plans,         live availability  release, refund
        |   constraints    reject                                 |
        +--------|------------------|-------------------|---------+
                 |                  |                   |
            registry.yaml      policy.py            executor
            (providers)     (caps, approval)     mock | xrpl
                                                         |
                            +----------------------------+
                            |                            |
                      x402 facilitator             XRPL Testnet
                 xrpl-facilitator-testnet.t54.ai  Payment · Escrow
                                                  Memos · SourceTag
                                                         |
                                        SSE  ->  organizer dashboard
```

**The engine contains no event-industry logic.** A vertical is three data files
(`template.yaml`, `registry.yaml`, `events.yaml`) plus an organizer profile. The
repository ships a second, unused vertical (`flight-disruption`) as evidence that
this is architectural rather than asserted — diff the two and you will find no
engine changes between them.

Verify it yourself:

```bash
grep -rniE "venue|conference|attendee" app/*.py    # docstrings only
```

---

## How the AI agent creates value

A real trace excerpt from the recorded run:

```
[SCREENING]
 * Disruption classified — venue.unusable, severity critical
     Marina Hall · flooding · 48h to event
 * Operating constraint added: public transport around the original site
   is unavailable

[PLANNING]                                     (free indicative pricing)
 OK  Relocate to a replacement venue    S$ 82,250   cash S$75,000
 OK  Cancel and refund attendees        S$245,000   cash S$25,000
 REJ Postpone to a later date           S$ 65,000   cash S$20,000
      -> organizer requires the event to stay within 48h; this plan moves the date
 * Selected: Relocate — avoids S$164,930 versus cancel

 X Rejected City Ballroom — S$28,000   capacity 900 is below the required 1000
 X Rejected Expo Venue C  — S$35,000   public transport not available

[VERIFICATION]                                 (paid, x402)
 X HTTP 402 from Suntec Backup Hall — payment required
     0.02 XRP to rn5D1Rfp… · invoice 9F41717116…
 * Confirmed Suntec Backup Hall — hold HOLD-598729, expires in 20 min
 X AV Supplier B failed verification
     crew committed elsewhere — falling back to the next supplier
 * Confirmed AV Supplier A — hold HOLD-869124

[SETTLEMENT]
 ! Approval escalated — Hall 402, full day (S$42,000 over the S$10,000 limit)
 # EscrowCreate   Suntec Backup Hall — funds locked
 # EscrowFinish   Setup milestone verified — funds released
 # Payment        AV Supplier A · Catering Supplier A
 # Refund         Unused contingency returned to organizer

 OUTCOME  S$66,000 committed | S$14,000 unused | S$164,930 avoided
```

Three decisions worth pausing on:

1. **Postpone was the cheapest plan and lost.** S$65,000 against relocate's
   S$82,250 — rejected because the organizer's deadline is fixed. That is
   constraint reasoning, not cost minimisation.
2. **Two venues rejected for different reasons.** One on capacity, one on
   transport accessibility. The cheaper venue is not the answer when nobody can
   reach it.
3. **A supplier failed after being selected.** The agent had already chosen the
   cheaper AV supplier and paid to verify. Verification is what caught it.

**Deterministic scoring, LLM narration.** Every cost, constraint check and cap is
Python. The model writes the human-readable reason and the final report. It never
does arithmetic and never overrides a constraint, which is why the run is
reproducible.

---

## Agentic transaction flow

```
agent selects provider from the registry
    │
    ├─ GET /venue/suntec-backup            → 200, free indicative pricing
    │                                        (enough to compare plans)
    │
    ├─ GET /venue/suntec-backup/verify     → 402 Payment Required
    │      { x402Version: 2, scheme: "exact", network: "xrpl:1",
    │        amount: "20000", asset: "XRP", payTo: "rn5D1Rfp…",
    │        extra: { invoiceId: "9F41717116…", sourceTag: 4021 } }
    │
    ├─ sign + submit XRPL Payment 0.02 XRP → facilitator verifies
    ├─ retry with PAYMENT-SIGNATURE        → 200 + live availability + hold ref
    │      the response carries a payment-response header with the settling hash
    │
    └─ settlement
         EscrowCreate  crypto-condition = SHA-256 of the milestone evidence
         EscrowFinish  fulfillment presented once setup is verified
         Payment       remaining suppliers, memo-linked to the decision
         Payment       unused contingency returned to the organizer
```

**Escrow releases against evidence, not a clock.** The condition is a
PREIMAGE-SHA-256 derived from `suntec|HOLD-598729|milestone:setup_verified`. The
funds can only move when that evidence is presented as the fulfillment.

**Interoperability, stated accurately.** `x402-xrpl` uses `PAYMENT-SIGNATURE` /
`PAYMENT-REQUIRED` / `PAYMENT-RESPONSE` where upstream x402 uses `X-PAYMENT`. So
a stock x402 or MPP client will **not** consume our endpoints unchanged — we
verified this and reported it upstream. What is true: the challenge body is
spec-shaped, so interoperability is a header-mapping shim, not a protocol gap.

---

## XRPL integration

| What | XRPL feature | Why |
|---|---|---|
| Paid verification | `Payment` (XRP) via x402 | Micropayments card rails cannot process |
| Venue commitment | `EscrowCreate` + crypto-condition | Funds lock until the milestone is proven |
| Milestone release | `EscrowFinish` + fulfillment | Release on evidence, not on a timer |
| Timeout protection | `EscrowCancel` + `CancelAfter` | Funds return if the milestone never lands |
| Supplier settlement | `Payment` (XRP) | Instant final settlement |
| Audit trail | `Memos` + `SourceTag 4021` | Every payment names its decision and its rule |
| Concurrency | `TicketCreate` / `TicketSequence` | Concurrent submission without sequence collisions |
| Live network values | `server_info` | Fees and reserves read live, never hardcoded |

### Memo format

Every agent transaction is self-describing on the public ledger:

```
SourceTag: 4021
MemoType:  alternate/booking
MemoData:  HOLD-369668|decision:d_relocate_av|rule:approval_threshold
```

```python
bytes.fromhex(memo_data).decode()
```

Open any hash below on the explorer and you can read which decision caused the
payment and which policy rule permitted it. That is the traceability claim, and
it is verifiable without trusting us.

---

## Transaction hashes

Network **XRPL Testnet** · Explorer `https://testnet.xrpl.org/transactions/{hash}`
Session wallet: [`r9Pwpy1iBRXFEeZdn8ix51tUJfoj2PCwD8`](https://testnet.xrpl.org/accounts/r9Pwpy1iBRXFEeZdn8ix51tUJfoj2PCwD8)

| # | What it demonstrates | Type | Hash |
|---|---|---|---|
| 1 | **x402 paid verification** — invoice `AC16967C…` | Payment 0.02 XRP | [`CB258C4B…24D17`](https://testnet.xrpl.org/transactions/CB258C4B1D65ED17DD5984ACE90C26429A6D541EF1BE60D1BE74052750024D17) |
| 2 | **x402 paid verification** — second provider | Payment 0.02 XRP | [`4C7356F0…C48118`](https://testnet.xrpl.org/transactions/4C7356F05D34C5DACA6594CB65D1792755F0B314823F808D2404168FCFC48118) |
| 3 | **Venue funds locked** under a crypto-condition | EscrowCreate | [`5B350888…C20BD`](https://testnet.xrpl.org/transactions/5B350888DCE7DC2A2168BF01FA7740304E66857BFA591AECD96A128B500C20BD) |
| 4 | **Milestone verified, funds released** | EscrowFinish | [`9944ADC8…E2308`](https://testnet.xrpl.org/transactions/9944ADC8B0ADB7DC6200081774233338FD1133D20ACAB0A548E0188CA52E2308) |
| 5 | **AV supplier paid** — memo `decision:d_relocate_av` | Payment | [`8F6017BF…E040AB`](https://testnet.xrpl.org/transactions/8F6017BFB51C02EE12ACAF3F416111D6070082DA3465F142B32C5E3C07E040AB) |
| 6 | **Catering supplier paid** — memo `HOLD-594011\|decision:d_relocate_catering` | Payment | [`0CFF93B2…B6B350`](https://testnet.xrpl.org/transactions/0CFF93B2609C7A9ED6DB3249771A976F1D1E4BB696F224A1A35661FD5BB6B350) |
| 7 | **Unused contingency refunded** — memo `rule:unused_contingency` | Payment | [`FCD42A94…1E631`](https://testnet.xrpl.org/transactions/FCD42A94648BDD7BB01F59878F88475FAB5902AA081485B5F33D149DC761E631) |

Full running log, including trust-line setup and the concurrency benchmarks:
[TRANSACTIONS.md](TRANSACTIONS.md).

---

## Trust, governance and agent controls

| Criterion | How we handle it |
|---|---|
| **Transparency** | Streaming decision trace: every plan compared, every option rejected with its reason, every payment with its price and hash |
| **Authorisation** | In-policy and under S$10,000: autonomous. Above it: escalated with the reason stated. Never autonomous: changing the budget or adding a provider |
| **Spending controls** | Per-transaction, per-category and per-incident caps. Category caps are reported before the envelope cap, because "more than we spend on AV" explains a policy where "running low" only describes a balance |
| **Security** | Treasury separate from the session wallet; suppliers allowlisted in the registry; the agent can only pay registry destinations |
| **Traceability** | Every transaction memo names the decision and the rule; the run emits a SHA-256 `decision_hash` over the full trace |
| **Failure handling** | Supplier verification failure falls through to the next candidate; escrow `CancelAfter` returns funds if a milestone never lands; unused budget is refunded |
| **Safeguards** | Provider allowlist, duplicate-purchase guard, plan-level feasibility gates, simulation mode for failure testing |

**Stated honestly:** `SetRegularKey` gives the agent a key that can be rotated or
disabled without moving funds. Offline master-key custody is **intended
production design and is not demonstrated here** — the seed is in `.env` on the
demo machine.

---

## Reachability

The engine applies wherever four things are true:

1. Something breaks unexpectedly
2. There is a short window before the fix gets worse or impossible
3. The fix means buying from several unrelated parties
4. Hard constraints must hold throughout

Event disruption is the vertical we built. The same engine, with a different
`template.yaml` and `registry.yaml`, addresses **logistics reroutes** (blocked
lane, new carrier and warehousing under a customs deadline) and
**disaster-relief procurement** (field supply under capacity and access
constraints). We have **not** built those and do not claim them. What we claim is
that the engine contains no event-industry logic — checkable in one grep.

**Developer accessibility:** a new vertical is three YAML files. **Compliance
position:** we are not merchant of record; the agent acts under delegated
authority against a preauthorised budget, and bookings are made with the supplier
of record.

---

## Commercial model

Per-organizer subscription sold to conference and exhibition organizers and PCOs,
priced against the risk carried rather than per transaction. A single mid-size
organizer runs dozens of events a year, each with six-figure exposure.

**We take no margin on what the agent buys.** The moment we profit from its
choices, nobody trusts it to spend their money. Revenue comes from the
subscription and, later, from the supply side — verified-availability endpoints
are a product suppliers would pay to expose.

---

## Beyond the prototype

### Cost

Measured live, not estimated. Testnet `server_info` at the time of the run: base
fee **10 drops**, account reserve **1 XRP**, owner reserve **0.2 XRP** per object.
Mainnet values from the bundled `xrpl-fee-settings.json` snapshot **agree today**,
so these carry over. A full recovery is ~13 transactions ≈ **0.00013 XRP** in
network fees — negligible against six-figure exposure. The real per-incident cost
is verification and inference, not settlement.

### Performance

| Path | Time |
|---|---|
| Sequential payments, JSON-RPC | ~95s (13.6s each) |
| Concurrent via Tickets, JSON-RPC | 21.8s |
| Concurrent via Tickets, **WebSocket** | **9.2s** |

The ledger closes every ~2.5s, so the gap between 21.8s and 9.2s was client-side
polling, not consensus. Two independent fixes: `TicketCreate` pre-allocates
sequence numbers so payments need not be serialised, and a persistent WebSocket
removes the HTTP poll loop.

**The current bottleneck is x402, not XRPL.** The Python x402 client is
synchronous with no batched path, so five verification calls take ~50s where
seven concurrent ticketed payments take 9.2s. Reported upstream; the fix is an
async client that accepts a pre-allocated `TicketSequence`.

### Known hard problems

Named unprompted, because they are the real ones:

- **Partial-itinerary rollback.** A four-supplier recovery that fails on the
  fourth leaves three paid. Escrow helps for the venue; it does not solve the
  general case.
- **Duplicate booking under retry.** Stateful bookings punish naive retries — a
  repeated call is a repeated booking. Our duplicate-purchase guard is a partial
  answer.
- **Facilitator dependency.** The testnet x402 facilitator is best-effort with no
  SLA. Production needs a contracted facilitator or our own.
- **Availability is only as good as the registry.** "The agent found the best
  option" is true only relative to the suppliers it can reach.

### Integration path

Real inventory connects through venue management systems, PCO platforms and
direct supplier APIs. **The x402 wrapper is the only genuinely new component** —
roughly 30 lines of middleware per endpoint, which is what `vendors/`
demonstrates.

---

## Running it

Reviewed on Windows with Python 3.13; Linux and macOS work identically.

**Prerequisites:** Python 3.11+, git, internet access. XRPL Testnet and the t54
facilitator are both public — **no API keys or accounts are required** to
reproduce the run.

```bash
git clone <this-repo> && cd singhacks_2026
pip install -r requirements.txt
cp .env.example .env
```

`.env` works as-is for everything XRPL. `OPENAI_API_KEY` is optional — the run is
fully deterministic without it; the model only writes narration.

**1 · Create and fund the testnet wallets** (~1 minute, public faucet):

```bash
python scripts/setup_wallets.py accounts
```

Creates 10 Testnet accounts (treasury, organizer session, 8 suppliers), funds each
with 100 XRP, and writes `wallets.json` — gitignored, never committed.

**2 · Start the supplier app**, with x402 gating enabled.

`X402=1` is what turns on payment gating — without it the `/verify` endpoints
answer for free and there is no 402 challenge and no payment.

```bash
X402=1 python -m uvicorn vendors.main:app --port 8011
```

```powershell
# PowerShell has no inline env-var prefix
$env:X402="1"; python -m uvicorn vendors.main:app --port 8011
```

**3 · Start ContingencyOS** with real XRPL settlement, **in a second terminal**.

Both servers run in the foreground and must stay running — the first will block
the second if you try to run them in one terminal.

```bash
EXECUTOR=xrpl python -m uvicorn app.main:app --port 8010
```

```powershell
$env:EXECUTOR="xrpl"; python -m uvicorn app.main:app --port 8010
```

`EXECUTOR=xrpl` settles for real on Testnet. Use `EXECUTOR=mock` for an instant
run with fake hashes and no ledger activity — useful for reading the decision
logic without waiting ~2.5 minutes for settlement.

Each server is up when it prints `Uvicorn running on http://127.0.0.1:80xx`.

**4 · Open** http://localhost:8010 and click **Run full demo**.

A full run takes roughly two and a half minutes, most of it real settlement. Every
row in the ledger panel links to `testnet.xrpl.org`.

### Verify the claims yourself

```bash
# see a real 402 challenge, before any payment is made
curl -i http://127.0.0.1:8011/venue/suntec-backup/verify

# the engine contains no event-industry logic (docstring hits only)
grep -rniE "venue|conference|attendee" app/*.py

# policy caps and constraint scoring
python -m pytest tests/ -q
```

**Reset between runs:** the Reset button, or `POST /reset`.

### Repository layout

```
app/            engine, plan comparison, scoring, policy, escrow, x402 client, UI
verticals/      recovery playbooks + provider registries (the domain, as data)
profiles/       organizer contingency policies
vendors/        eight mock suppliers: free tier + x402-gated verification tier
scripts/        wallet setup and funding
docs/           build record: decision log and per-phase notes
tests/          policy and scoring tests
```

---

## Builder feedback

Nine items reported through the hackathon feedback hook during the build, each
with reproduction detail. The substantial ones:

- The testnet RLUSD faucet is wallet-connect only with no address field, which
  breaks scripted setup and forces a seed export into a browser extension. It then
  failed at three separate points and never reached the ledger.
- An enabled amendment is not a usable feature: `TokenEscrow` reports
  `enabled: true`, but issued-token locking also requires the *issuer* to set
  `lsfAllowTrustLineLocking`.
- `xrpl-py` transport choice carries a ~3× latency penalty documented nowhere
  (13.6s vs 4.6s per payment).
- `xrpl-py` ships no crypto-condition helper despite `EscrowCreate` accepting a
  `condition`, and `EscrowFinish` needs an `OfferSequence` the create result does
  not return.
- `x402-xrpl` diverges from upstream x402 header names, which breaks the MPP
  interoperability claim — we removed that claim from this README as a result.
- The x402 Python client is synchronous with no concurrent path, which is the
  wrong shape for the agentic workloads x402 is promoted for.

Full detail in [FEEDBACK.md](FEEDBACK.md), including draft answers for the
builder feedback form.

## Build record

Every non-obvious decision, including the ones we reversed and why:
[docs/00-decisions.md](docs/00-decisions.md).

## Team

**alternate.ai** — Wei Yan Min Oo
