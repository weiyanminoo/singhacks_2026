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

**Real:** every XRPL transaction, the x402 payment flow, the agent's decisions,
the policy engine, the spending controls, the failure recovery.

**Simulated:** the vendors. Six mock providers with genuinely different pricing,
inventory and latency. Travel API sandbox approval takes days and we had 24 hours.
Integration path in [Beyond the prototype](#beyond-the-prototype).

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
     purchase via RLUSD Payment with SourceTag + Memos → EscrowCreate for the
     refundable hold → confirmation delivered. -->

## Architecture  `[Phase 3]`

<!-- Diagram. One screen. -->

---

## XRPL integration  `[Phase 1]`

| What | XRPL feature | Why |
|---|---|---|
| Spending ceiling | Funded session account | The limit is the balance, not a code check |
| Discovery queries | `Payment` (XRP) ×8 | Sub-cent purchases card rails cannot process |
| Purchases | `Payment` (RLUSD) ×3 | Dollar-denominated, instant final settlement |
| Audit trail | `Memos` + `SourceTag` | Every tx maps to a decision and a policy rule |
| Refundable hold | `EscrowCreate` / `Finish` / `Cancel` | Money returns when the hotel sells out |
| Key delegation | `SetRegularKey` | Agent key rotatable, master offline |

<!-- Explain the two-asset choice as a design decision (see docs/00-decisions.md
     D-002): stablecoin for value transfer where price stability matters, native
     asset for high-frequency micropayments and conditional holds. -->

### Memo format

```
SourceTag: 4021
MemoType:  alternate/booking
MemoData:  BK-7741|decision:d_012|rule:hotel_cap_250
```

Decode: `bytes.fromhex(memo_data).decode()`

<!-- Any payment on the explorer traces back to the decision that caused it and
     the rule that permitted it. -->

## x402 usage  `[Phase 2]`

<!-- Facilitator: xrpl-x402.t54.ai. SDK: t54-labs/x402-secure, version pinned.
     Which endpoints are gated and at what price. The free-tier pattern: free call
     returns schema + stale sample, paid call returns live data.
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
| **Spending controls** | The session wallet holds exactly the envelope. Per-transaction, per-category and per-session caps. The ceiling is the balance, not a code check |
| **Security** | Treasury separate from session wallet; agent signs with a rotatable regular key; providers allowlisted in the registry |
| **Traceability** | Every tx memo carries a decision reference; the receipt ledger maps tx ↔ decision ↔ policy rule ↔ booking reference |
| **Failure handling** | See below — demonstrated live in the video |
| **Safeguards** | Provider allowlist, duplicate-purchase guard (cannot book two hotels for one night), max actions per incident, kill switch |

<!-- Add a paragraph mapping this onto the OpenWallet Standard: delegated agent
     access and policy-gated signing are precisely this control layer, and
     production would use it rather than a bespoke key setup. -->

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
     Unit economics: ~$0.16 discovery + ~$0.10 inference + settlement fees. -->

---

## Beyond the prototype  `[Phase 5]`

<!-- 20% of the grade. Specific, with real numbers. -->

### Cost

<!-- Per recovery, broken down. Cite fee and reserve values from
     xrpl-fee-settings.json — do not hardcode or guess. -->

### Performance

<!-- Latency budget for the 90-second target: discovery round trips, x402
     settlement time, LLM inference. Where the time actually goes. -->

### Scalability and reliability

<!-- What breaks at 10,000 concurrent disruptions. Sequence handling per wallet
     (see docs/00-decisions.md D-006). The testnet facilitator is best-effort with
     no committed SLA; we pinned a version. What production would need. -->

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
git clone <repo> && cd alternate-ai
cp .env.example .env               # add your testnet seeds
pip install -r requirements.txt
python scripts/setup_wallets.py    # fund + trust lines
uvicorn vendors.main:app --port 8001 &
uvicorn app.main:app --port 8000
# open http://localhost:8000
```

Tests: `pytest tests/`

## Repository layout

```
app/         agent, policy engine, registry, scoring, wallet, x402 client, UI
vendors/     six mock providers, x402-gated, one FastAPI app
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
