# alternate.ai

> A recovery agent that fixes broken plans by buying the fix, inside a spending
> envelope you approved in advance.

**SingHacks 2026 — Build an AI-Native Business on XRPL**

<!--
  ⚠️ THIS FILE IS A GRADED DELIVERABLE, NOT DOCUMENTATION.
  ~70% of the score is read out of this repo, and this file carries most of it.

  FILL SECTIONS IN AS THE WORK LANDS — do not wait for Phase 5. Each heading is
  tagged with the phase that should complete it. See the phase→section map in
  CLAUDE.md.

  Delete every HTML comment before submitting.
-->

*In aviation, the **alternate** is the backup airport you are required to nominate
before you take off. A fallback designated in advance, funded in advance.*

---

## What is real and what is simulated  `[Phase 0]`

<!-- Keep this near the top. Honesty reads as confidence. -->

**Real:** every XRPL transaction, on Testnet. The money is **genuine RLUSD** —
Ripple's testnet stablecoin, issuer `rQhWct2fv4Vc4KRjRgMrxa8xPN9Zx9iLKV`, held on
real trust lines. Also real: the x402 payment flow, the agent's decisions, the
policy engine, the spending controls, the failure recovery.

**Simulated:** the vendors. Eight mock providers with genuinely different pricing,
inventory and latency. Travel API sandbox approval takes days and we had 24 hours.
Integration path in [Beyond the prototype](#beyond-the-prototype).

**Scaled:** the demo runs a **$10 envelope, not $400**. The public testnet RLUSD
faucet dispenses 10 RLUSD per 24 hours, so a larger envelope cannot be funded with
real RLUSD — and we chose authentic RLUSD at small scale over a self-issued token
at large scale. Every amount on the explorer is real.

**Purchases** are scaled 1/40 ($4.60 flight, $1.95 hotel, $0.49 transfer).
**Discovery is not scaled** — it stays at its real price of **$0.02 per query**,
$0.14 across 7 providers, because the cost of a data query does not shrink because
the trip is smaller. So the discovery figure you see in the trace is the same one
used in the unit economics under [Beyond the prototype](#beyond-the-prototype).
See `docs/00-decisions.md` D-009 and D-012.

**Not built:** conditional escrow. `TokenEscrow` is an enabled amendment, but
locking an issued token also requires the *issuer* to set
`lsfAllowTrustLineLocking`, and Ripple's testnet RLUSD issuer does not
(`Flags = 0x819a0000`, verified T+0). The refundable hold is therefore a
vendor-initiated refund `Payment`. Why escrow is the better production design is
in [Failure handling](#failure-handling). See D-011.

---

## The problem  `[Phase 5]`

<!-- Three paragraphs, no jargon.
     1. The 9pm cancellation, told as a scene. 400 people, 30 rooms, 15 minutes.
     2. Why humans lose: a multi-constraint decision under time pressure at the
        worst hour, across vendors that don't talk to each other, while inventory
        is consumed by others.
     3. Scale + proof of willingness to pay: ~1 in 5 flights runs late against
        4bn+ journeys a year; claim firms take 25–35% for handling only the
        paperwork afterwards. -->

## The product  `[Phase 5]`

<!-- Five sentences. Envelope set in advance → trigger → agent discovers, decides,
     buys → ~90 seconds → confirmations and receipts.
     Then separate the user (the stranded traveller) from the buyer (the company
     or TMC). Keeping those apart makes the commercial model legible. -->

## Why autonomous payments make this possible  `[Phase 5]`

<!-- The thesis. Three concrete points:
     1. The envelope is a physical ceiling, not a policy check.
     2. Broad search needs sub-cent payments; breadth is where the value is.
     3. A recommendation is worthless inside a 15-minute window.
     Be honest about cards: they handle the hotel room fine. They cannot handle
     twenty two-cent queries, and they don't give a vendor instant final money
     for inventory that expires tonight. -->

---

## How the AI agent creates value  `[Phase 3]`

<!-- The three decisions, each with a REAL trace excerpt from a run:
     1. Search-vs-commit under decaying inventory
     2. Constraint conflict — show the REJECTED option and the reason
     3. Cost-of-being-wrong — optimising the objective, not the price
     Then one line: deterministic constraint scoring with LLM-driven planning
     and selection. Detail in docs/phase-3-agent-decisions.md. -->

```
<!-- paste a real trace excerpt here -->
```

## Customer journey  `[Phase 3]`

<!-- Screenshots: envelope setup → trigger → discovery → decision → purchases →
     approval prompt → confirmations → receipt bundle. -->

## Agentic transaction flow  `[Phase 2]`

<!-- The actual mechanics, step by step:
     agent selects provider from registry → GET endpoint → 402 with price →
     signs XRPL Payment → facilitator verifies → 200 with live data → ... →
     purchase via RLUSD Payment with SourceTag + Memos → confirmation delivered.
     Escrow was cut (D-011); on the failure path the refundable hold is a
     vendor-initiated refund Payment. -->

## Architecture  `[Phase 3]`

<!-- Diagram. One screen. -->

---

## XRPL integration  `[Phase 1]`

| What | XRPL feature | Why |
|---|---|---|
| Spending ceiling | Session wallet's RLUSD trust line balance | The limit is the balance, not a code check |
| Discovery queries | `Payment` (RLUSD) ×7 | Sub-cent purchases card rails cannot process |
| Purchases | `Payment` (RLUSD) ×3 | Dollar-denominated, instant final settlement |
| Concurrent settlement | `TicketCreate` + `TicketSequence` | 7 discovery payments in one ledger close, not seven |
| Audit trail | `Memos` + `SourceTag` | Every tx maps to a decision and a policy rule |
| Refund on failure | `Payment` (RLUSD, vendor → session) | Money returns when the hotel sells out |
| Key delegation | `SetRegularKey` | Agent key rotatable or revocable without moving funds |

<!-- Explain the SINGLE-asset choice as a design decision (docs/00-decisions.md
     D-002a, which supersedes D-002). Points to make:
     - The envelope IS the RLUSD trust line balance. One number, one ceiling.
     - XRP in the account is operational only — reserves and ~10 drops per tx in
       fees. Not agent-spendable: the policy engine issues RLUSD payments to
       allowlisted registry destinations and nothing else.
     - The sub-cent argument is about RAILS, not denomination. A $0.02 payment is
       impossible on card networks whatever the asset settles it.
     - D-002 (the earlier two-asset design) is kept in the decision log on
       purpose — showing the reasoning that was revised is worth more than
       pretending we got it right first time.
     - Tickets: TicketBatch is a live amendment; we used it to solve a real
       latency constraint rather than working around it with a mutex. Cross-ref
       D-006a and the Performance section below. -->

<!-- RESOLVED: escrow was cut at T+0 (D-011) because the testnet RLUSD issuer does
     not set lsfAllowTrustLineLocking. The table row above now reads "Refund on
     failure / Payment", which is what we actually built. Failure handling must
     describe conditional escrow as the production design and say why it is
     better: funds return automatically on a time bound, without depending on the
     vendor's cooperation or solvency. -->

### Memo format

```
SourceTag: 4021
MemoType:  alternate/booking
MemoData:  BK-7741|decision:d_012|rule:hotel_cap_6_25
```

Decode: `bytes.fromhex(memo_data).decode()`

<!-- Any payment on the explorer traces back to the decision that caused it and
     the rule that permitted it. -->

## x402 usage  `[Phase 2]`

<!-- Facilitator: https://xrpl-facilitator-testnet.t54.ai (network xrpl:1).
     SDK: x402-xrpl (PyPI), version pinned - NOT x402-secure, see D-010.
     Which endpoints are gated and at what price — priced in RLUSD (~$0.02/call),
     not XRP drops, per D-002a. The free-tier pattern: free call returns schema +
     stale sample, paid call returns live data.
     Interoperability: MPP is backwards-compatible with x402, so an MPP client
     could consume our endpoints unchanged. -->

## XRPL AI Starter Kit / agent skill integration  `[Phase 2]`

<!-- Required by the submission checklist. Name which components and where:
     the xrpl-agentic-resources skill, xrpl-amendments.json for feature checks,
     xrpl-fee-settings.json for cost figures, the vendored docs indexes.
     Be specific — vague answers score nothing. -->

---

## Transaction hashes  `[Phase 3, verified Phase 5]`

Network: XRPL Testnet · Explorer: `https://testnet.xrpl.org`

| # | What it demonstrates | Type | Hash |
|---|---|---|---|
| | | | |

Full log: [TRANSACTIONS.md](TRANSACTIONS.md)

<!-- Most reviewers look for this table. Never bury hashes in a log file. -->

---

## Trust, governance and agent controls  `[Phase 4]`

| Criterion | How we handle it |
|---|---|
| **Transparency** | Streaming decision trace: every query, price, option considered, option rejected and why, running budget |
| **Authorisation** | In-policy and under cap: autonomous. Over cap or out of policy: single-tap approval with the reason stated. Never autonomous: changing the envelope, adding a provider |
| **Spending controls** | The session wallet holds exactly the envelope in RLUSD, and every purchase is an RLUSD payment to an allowlisted vendor — so the ceiling is the balance, not a code check. The account's small XRP balance covers fees and reserves and is not agent-spendable. Per-transaction, per-category and per-session caps sit inside that hard ceiling |
| **Security** | Treasury separate from session wallet; agent signs with a regular key that can be rotated or disabled without moving funds; providers allowlisted in the registry |
| **Traceability** | Every tx memo carries a decision reference; the receipt ledger maps tx ↔ decision ↔ policy rule ↔ booking reference |
| **Failure handling** | See below — demonstrated live in the video |
| **Safeguards** | Provider allowlist, duplicate-purchase guard (cannot book two hotels for one night), max actions per incident, kill switch |

<!-- Add a paragraph mapping this onto the OpenWallet Standard: delegated agent
     access and policy-gated signing are precisely this control layer, and
     production would use it rather than a bespoke key setup. -->

<!-- STATE HONESTLY (docs/00-decisions.md D-008): SetRegularKey demonstrates key
     delegation on ledger, and the regular key can be rotated or disabled without
     moving funds. Offline master-key custody is INTENDED PRODUCTION DESIGN and is
     NOT demonstrated here — the master seed is in .env on the demo machine.
     Do not write "the master key stays offline." Saying what we did not do is
     what makes the rest of this table credible. -->

## Failure handling  `[Phase 4]`

<!-- The live path: vendor reports sold out AFTER settlement → escrow cancels →
     funds return → agent reroutes → only the second option is paid.
     Also: approval timeout, provider timeout, envelope exhausted.
     For envelope exhausted, note that agent credit infrastructure (claw.credit)
     is the natural production answer — settle against the traveller's
     reimbursement or the airline compensation. -->

---

## Reachability  `[Phase 5]`

<!-- 20% of the grade. Not an afterthought. -->

### The pattern

alternate.ai applies wherever four things are true:

1. Something breaks unexpectedly
2. There is a short window before the fix gets worse or impossible
3. The fix means buying from several unrelated parties
4. Real constraints must hold while you do it

### Other verticals

<!-- One paragraph each: delivery van breakdown mid-route; production line down
     waiting on a part; venue cancels days before an event. Same engine — swap the
     provider registry and the constraint set. -->

### Interoperability, accessibility, compliance

<!-- MPP compatibility. The engine takes a constraint set + a provider registry,
     so a third party can point it at another vertical. Compliance position: not
     merchant of record, acting under delegated authority with a preauthorised
     envelope; bookings made with the vendor of record. -->

## Commercial model  `[Phase 5]`

<!-- Per-traveller subscription sold to TMCs and companies (~$10/traveller/month;
     one TMC contract reaches thousands of travellers and they already hold
     inventory access). 15–20% of recovered airline compensation, undercutting
     the 25–35% incumbents. Supply-side revenue later.
     The positioning point worth stating loudly: we take NO margin on what the
     agent buys, because the moment we profit from its choices nobody trusts it
     to spend their money.
     Unit economics: ~$0.14 discovery (7 × $0.02) + ~$0.10 inference +
     settlement fees. -->

---

## Beyond the prototype  `[Phase 5]`

<!-- 20% of the grade. Specific, with real numbers. -->

### Cost

<!-- Per recovery, broken down. Present BOTH, per docs/00-decisions.md D-007:
     - Testnet actuals: what this run actually cost, read live from our own node
       (server_info / server_state).
     - Mainnet projection: what it would cost on mainnet today, cited from
       resources/xrpl-fee-settings.json (live mainnet state via xrpscan).
     Presenting both is stronger than either alone, and it is exactly what the
     Feasibility criterion asks for. Do not hardcode or guess either set. -->

### Performance

<!-- Latency budget for the 90-second target: discovery round trips, x402
     settlement time, LLM inference. Where the time actually goes.

     LEAD WITH THE TICKETS RESULT (docs/00-decisions.md D-006a). The story:
     the happy path is ~13 transactions; at a ~3-5s ledger close, fully
     serialised settlement burns 40-65s before a single LLM token is generated,
     against a 90s target. We pre-allocate tickets with TicketCreate and fire the
     discovery leg concurrently with TicketSequence set and Sequence: 0, which
     collapses that leg from ~35s to about one ledger close. Per-account locks,
     not one global lock, because sequence collisions are per-account.
     Give the measured before/after numbers from a real run.
     If we fell back to per-account locks, say so plainly and describe tickets as
     the intended design. -->

### Scalability and reliability

<!-- What breaks at 10,000 concurrent disruptions. Sequence handling per wallet
     (see docs/00-decisions.md D-006a, which supersedes D-006). The testnet
     facilitator is best-effort with no committed SLA; we pinned a version.
     What production would need: ticket pools sized per wallet, and one session
     wallet per active incident rather than a shared account. -->

### Known hard problems

<!-- Name these unprompted — it signals domain understanding:
     - Stateful bookings punish naive retries; a duplicate call is a duplicate
       booking. Our duplicate-purchase guard is a partial answer.
     - Partial itinerary failure needs rollback of the legs that succeeded.
     - Inventory fragmentation: "the agent found the best option" is only ever
       true relative to the inventory it can reach. -->

### Integration path

<!-- How real inventory connects: NDC, GDS, direct hotel APIs. The x402 wrapper
     is the only genuinely new component (~30 lines of middleware). -->

### Compliance

<!-- Not merchant of record. Delegated authority via preauthorised envelope.
     Compensation recovery follows an assignment-of-claim model that existing
     firms already operate under. -->

---

## Running it  `[Phase 0]`

```bash
git clone <repo> && cd singhacks_2026
pip install -r requirements.txt
cp .env.example .env                          # add OPENAI_API_KEY
python scripts/setup_wallets.py accounts      # 10 testnet accounts, faucet-funded
python scripts/setup_wallets.py trustlines    # 9 RLUSD trust lines
#  → claim 10 RLUSD at https://tryrlusd.com/ to the `session` address printed above
uvicorn vendors.main:app --port 8001 &
uvicorn app.main:app --port 8000
# open http://localhost:8000
```

The RLUSD claim is manual: the faucet requires GitHub sign-in and there is no API.
It must happen **after** `trustlines`, because XRPL rejects an incoming IOU with
`tecNO_LINE` if the receiving account has no trust line.

Between demo runs, `python scripts/setup_wallets.py recycle` sweeps RLUSD from the
vendor accounts back to the session wallet — the vendors are our own accounts, so
the envelope is recycled rather than consumed. Without this you get roughly one
run per 24 hours.

Tests: `pytest tests/`

## Repository layout

```
app/         agent, policy engine, registry, scoring, wallet, x402 client, UI
vendors/     eight mock providers, x402-gated, one FastAPI app
docs/        build record: one file per phase + decision log
tests/       policy and scoring tests
scripts/     wallet setup
```

## Build record

Phase-by-phase implementation detail, decisions and deviations: [docs/](docs/)

## Builder feedback

See [FEEDBACK.md](FEEDBACK.md). Feedback hook ran throughout the build; final form
submitted.

## Team

<!-- names -->
