# PLAN.md — alternate.ai build roadmap

24 hours. 2 people. ~34 productive person-hours.

**Rule: do not start a phase until the previous phase's success criteria are met.**
If a milestone slips, execute the cut list at the bottom. No debate.

**Every phase ends with three things**, not one: working code, a
`docs/phase-N-*.md` entry, and the mapped README sections filled in. A phase is
not done until all three are done.

---

## Roles

The A/B split below describes **workstreams, not people**. It assumed two humans
building in parallel against stubs; with Claude Code as the implementer that is
the wrong shape. Keep the labels — they usefully mark dependency order within a
phase — but work like this:

- **Claude Code implements sequentially**, phase by phase, in dependency order.
  Within a phase, do Person A's items before Person B's where B depends on A;
  otherwise the order is Claude's call.
- **Human 1 drives.** Reviews each phase against its success criteria, makes the
  call whenever Claude flags an ambiguity, runs the demo dry runs.
- **Human 2 works in parallel on what Claude is not touching:** README prose, the
  architecture diagram, `DEMO.md` narration, screenshots, and the Reachability
  and Commercial sections — none of which need code.

**Stub-first still applies inside Claude's own work.** Build `x402_client` stubs
returning fake hashes so the agent logic and UI can be developed and tested before
the real payment path lands.

---

## Phase 0 — Setup (T+0 → T+1) · BOTH

Nothing else starts until this is done.

> ~~`bash skills/install.sh`~~ — **done, do not re-run.** Under MSYS on Windows
> `ln -s` deep-copies instead of linking, so re-running replaces the working
> junctions with copies that `refresh.sh` will never update.
> ~~Install the feedback hook~~ — **done**, verified with a live 201 submission.

- [ ] `bash skills/xrpl-agentic-resources/scripts/refresh.sh`
- [ ] Read https://xrpl-x402.t54.ai/#setup
- [ ] Confirm `xrpl-up` installs on Windows; if not, fall back to an `xrpl-py`
      script (this phase gates on the tool, so establish it early)
- [ ] Create 2 testnet accounts (treasury, session), fund generously from faucet
- [ ] Get testnet RLUSD from https://tryrlusd.com/
- [ ] **Set the RLUSD trust line on the session wallet** (envelope = this balance)
- [ ] **`scripts/setup_wallets.py`: 8 vendor accounts + 8 `TrustSet` transactions**
      — every vendor must hold an RLUSD trust line, since all spending is now
      RLUSD (D-002a). One-time, scripted.
- [x] **Escrow asset check** — DONE. Issuer `rQhWct2fv4Vc4KRjRgMrxa8xPN9Zx9iLKV`
      has `Flags = 0x819a0000`; `lsfAllowTrustLineLocking` is **NOT set**, so
      token escrow is unavailable. Cut-list item 1 executed → refund-`Payment`
      fallback. Recorded as D-011.
- [ ] Verify **one RLUSD payment** via `xrpl-up`, before any app code
- [x] `.env.example` (incl. `OPENAI_API_KEY`), `requirements.txt`, `.gitignore`
      covering `.env` / `__pycache__` / `wallets.json` / `.claude/skills/`
- [ ] Both read the interface contract in `CLAUDE.md` out loud and agree it
      (note: `create_hold()` is replaced by `refund()` — the one contract change,
      forced by D-011)

**Success:** wallets funded, RLUSD held on session + all 8 vendors, one
CLI-verified **RLUSD** payment on the explorer, escrow asset question answered,
hook running, both people agree the contract.

**Write:** `docs/phase-0-setup.md` — account addresses and roles, exact faucet and
trust line steps, anything that did not work first time.
**README:** *What is real vs simulated*, *Running it*.

---

## Phase 1 — Skeleton (T+1 → T+3)

**Person A**
- [ ] `xrpl_ops.py`: connect, sign, submit, wait for validation
- [ ] **Per-account locks (not one global lock) + `TicketCreate`** — pre-allocate 8
      tickets on the session wallet; discovery fires concurrently with
      `TicketSequence` set and `Sequence: 0` (D-006a). **Do this now, not later.**
      Verify `TicketBatch` on testnet first. If tickets are not working by the end
      of this phase, fall back to per-account locks, record it, and move on —
      Phase 2 is not to be spent on this.
- [ ] Ripple-epoch helper (`unix_to_ripple(ts) = ts - 946684800`)
- [ ] One RLUSD `Payment` with `SourceTag` + `Memos`, landed and verified
- [ ] Fee/reserve values read **live from our own node** (`server_info` /
      `server_state`), not hardcoded and **not** from the mainnet JSON snapshot
      (D-007)

**Person B**
- [ ] FastAPI app, `/stream` SSE endpoint
- [ ] `static/index.html`: split layout, trace panel left, envelope right
- [ ] Trace events render and animate in; envelope number updates
- [ ] Stub `x402_client` returning fake hashes so the UI can be built

### ✅ MILESTONE M1 (T+3)
**A transaction hash is on testnet.xrpl.org AND text is streaming into a browser
page.** Both halves alive independently.

*If M1 slips past T+4: stop, pair on whichever half is stuck.*

**Write:** `docs/phase-1-xrpl-foundation.md` — memo/SourceTag encoding, the
sequence-handling approach and why, the epoch helper, the fee values read and
their source.
**README:** *XRPL integration* table, *Memo format*.

---

## Phase 2 — The contingency engine (T+3 → T+8) · THE MVP

**This is the product.** Everything here is domain-neutral (D-015). No flight
logic in `app/`.

**Data first — the domain, as files**
- [ ] `verticals/flight-disruption/template.yaml`: trigger conditions, required
      resource categories, ordered recovery steps with slots, constraint schema,
      default caps
- [ ] `verticals/flight-disruption/registry.yaml`: the 8 providers
      (2 flight, 3 hotel, 2 ground, 1 status/waiver) — id, capability, endpoint,
      price, reliability
- [ ] `verticals/flight-disruption/events.yaml`: mock feed the trigger loop polls
- [ ] `profiles/traveller-01.json`: preferences, budget, hard constraints, history

**Engine — no domain knowledge**
- [ ] `templates.py`: load + validate playbooks; fail loudly on a bad schema
- [ ] `profiles.py`: load/save profile; append decisions to history
- [ ] `registry.py`: resources from the vertical's data file, never hardcoded URLs
- [ ] `scoring.py`: deterministic constraint scoring
- [ ] `policy.py`: per-tx cap, category cap, envelope cap, approval threshold,
      duplicate-purchase guard
- [ ] `engine.py`: match template → expand with profile → plan → score → act
- [ ] `executor.py`: adapter interface + `mock` adapter (instant, no ledger)
- [ ] `triggers.py`: polling loop over a pluggable source + manual fire endpoint
- [ ] `vendors/main.py`: 8 mock providers, plain HTTP for now (x402 in Phase 3)
- [ ] Personalisation is **visible in the trace** — say which profile fact drove
      which choice, or the selling point is invisible

### ✅ MILESTONE M2 (T+8) — THE ONE THAT MATTERS NOW
**An event fires from the loop, the engine matches a template, personalises it
from the profile, and executes a full recovery — streamed to the UI end to end.**
A working product, with payments still mocked.

*If M2 slips past T+9: cut the next cut-list item immediately.*

**Write:** `docs/phase-2-engine.md` — the template schema and why it is shaped
that way, how matching works, what the LLM decides vs what Python decides, how
personalisation enters the plan, an annotated trace.
**README:** *How the agent creates value*, *Architecture*, *Reachability* (the
engine shape IS the argument).

---

## Phase 3 — XRPL + x402, thin but real (T+8 → T+11)

The engine already works. This makes the money real without touching engine logic.

- [ ] `executor.py`: `xrpl` adapter alongside `mock` — same interface, so the
      engine cannot tell the difference
- [ ] x402-gate the vendor endpoints via **`x402-xrpl`** (D-010), **priced in
      RLUSD at $0.02/call** (D-012). **If the facilitator enforces a minimum
      above $0.02: STOP AND ASK.**
- [ ] `x402_client.py`: real 402 challenge → pay → retry, replacing the stub
- [ ] Free tier on data endpoints returns schema + stale sample; paid returns live
- [ ] Discovery leg uses pre-allocated tickets (D-006a) over WebSocket (D-014)
- [ ] `receipts.py`: tx_hash ↔ decision_id ↔ policy_rule ↔ booking_ref
- [ ] The outstanding **RLUSD-denominated payment** finally lands here
- [ ] Explorer links inline next to each purchase in the UI

### ✅ MILESTONE M3 (T+11)
**The same run as M2, settling on XRPL.** Hashes visible and clickable, envelope
drains for real, memos tie each payment to the decision that caused it.

*If M3 slips past T+12: keep the mock executor for the demo, show the XRPL
transactions we already have, and be explicit about it in the README.*

**Write:** `docs/phase-3-xrpl-x402.md` — the 402 challenge shape observed,
facilitator setup and pinned version, per-call latency measured, the adapter
boundary.
**README:** *x402 usage*, *Agentic transaction flow*, *Transaction hashes*.

---

## Phase 5 — ContingencyOS: the thin thread (T+5 → T+9)

**Pivot to event contingency (D-018).** Build the smallest complete path first,
exactly as specified: event trigger → plan selection → x402 payment → XRPL
escrow → milestone release → refund. Breadth comes in Phase 6.

**Data — the vertical**
- [ ] `verticals/event-contingency/template.yaml` — **new `plans:` layer** above
      the existing `steps:`: cancel / postpone / relocate, each with its cost
      components; relocate carries the step chain (venue → AV → catering → transport)
- [ ] `verticals/event-contingency/registry.yaml` — ≥6 providers: Marina Hall
      (flooded), Suntec Backup Hall, Expo Venue C (no transport), City Ballroom
      (capacity 900), AV A/B, Catering A, Transport A
- [ ] `verticals/event-contingency/events.yaml` — venue_failure, severity critical
- [ ] `profiles/organizer-01.json` — Asia Fintech Summit, 1,000 pax, S$80,000 cap,
      per-transaction S$10,000 approval threshold, all constraints

**Engine — the one structural addition**
- [ ] `plans.py`: expected-cost model —
      `direct_recovery + expected_refunds + supplier_failure_risk + delay_penalty`
- [ ] Plan-level rejection: capacity, deadline, transport access, budget
- [ ] `engine.py`: compare plans → select → execute the winner's steps via the
      machinery that already exists
- [ ] Decision trace object + `decision_hash` (sha256 over the canonical trace)

**Money — three layers, kept separate (D-018)**
- [ ] Business layer S$ — UI and memos only, never claimed as on-ledger value
- [ ] x402 layer — real XRP micropayments, own budget, **verified working T+5**
- [ ] Settlement layer — real XRPL at a nominal amount, true S$ in the memo

**Settlement**
- [ ] `x402_client.py`: wrap `X402RequestsSession` (proven T+5); record tx hash
      from the `payment-response` header into the trace
- [ ] `escrow.py`: `EscrowCreate` with PREIMAGE-SHA-256 condition on the milestone
      evidence hash; `EscrowFinish` with fulfillment; `EscrowCancel` (D-019).
      **Timebox the condition encoding — fall back to `FinishAfter` and record it.**
- [ ] Refund unused contingency balance to the organizer

### ✅ MILESTONE M5 (T+9)
**Flood event fires → three plans compared → relocate selected with reasons →
one real x402 verification payment → escrow created → milestone released →
unused balance refunded.** All hashes on testnet.xrpl.org.

---

## Phase 6 — Breadth: rejections, failure, full sequence (T+9 → T+13)

- [ ] All four verification calls x402-gated: venue, transport, AV, catering
- [ ] **Expo Venue C rejected** — public transport unavailable (required visual)
- [ ] **City Ballroom rejected** — capacity 900 < 1,000
- [ ] **AV Supplier B fails or times out → backup provider engaged** (required)
- [ ] Milestone payments: partial venue payment after booking verification
- [ ] Supplier failure → redirect or refund
- [ ] The full 12-transaction sequence from the spec, logged in `TRANSACTIONS.md`
- [ ] Human approval escalation above S$10,000 per transaction / S$80,000 total

### ✅ MILESTONE M6 (T+13) — the complete recovery, end to end

---

## Phase 7 — Dashboard (T+13 → T+16)

Five regions covering all nine required visuals:
- [ ] Header: event profile + organizer constraints + live disruption
- [ ] Agent activity timeline (Screening → Planning → Verification → Settlement)
- [ ] Plan comparison: three plans, costs, selected one, **rejection reasons**
- [ ] Money column: contingency balance, x402 activity, XRPL transactions with
      clickable explorer links, settlement status
- [ ] Final financial outcome: spend, avoided loss, unused balance refunded
- [ ] Run full demo · simulation mode · reset

### ✅ MILESTONE M7 (T+16) — HARD FEATURE FREEZE

---

## Phase 8 — Report, docs, submission (T+16 → T+22)

- [ ] Final decision report (the trace, rendered)
- [ ] `docs/phase-5-contingencyos.md`
- [ ] README: rewrite for the event line of business; keep the honesty sections
- [ ] `DEMO.md` rewritten to the flood scenario
- [ ] Record the demo

---

## Phase 4 — Sleep + failure + polish (T+11 → T+17)

**T+11 → T+14: sleep in staggered shifts.** Do not skip. Hour 19 spent debugging
what you broke at hour 18 is the classic way to lose.

**Person A (T+14 → T+17)**
- [ ] Failure path: vendor returns sold-out AFTER payment → vendor-initiated
      refund `Payment` (D-011, escrow cut) → agent reroutes → only the second
      option is paid
- [ ] `tests/test_policy.py`: cap enforcement, approval threshold, duplicate guard
- [ ] `tests/test_scoring.py`: constraint scoring picks the right option

**Person B (T+14 → T+17)**
- [ ] Visual polish: dark bg, one accent colour, monospace trace, fade-in on each
      new line, generous spacing. Restraint reads as intentional.
- [ ] Envelope counter animates down
- [ ] Approval prompt looks good on a phone screen
- [ ] Full dry run, timed. Must land under 2 minutes.

### ✅ MILESTONE M4 (T+17) — HARD FEATURE FREEZE
**Whatever state the code is in at T+17, stop building.** This single commitment
is worth more than any remaining feature, because ~70% of the grade is read out
of the repo.

**Write:** `docs/phase-4-failure-and-controls.md` — every failure mode handled and
how, the governance model (what is autonomous vs what requires approval and why),
what the tests cover, known unhandled cases stated honestly.
**README:** *Trust & governance* table, *Failure handling*.

---

## Phase 5 — Submission (T+17 → T+22) · BOTH

Most README sections should already be filled from earlier phases. This is
polish plus the two long-form sections.

**Person A finishes:**
- [ ] Architecture diagram, final
- [ ] Transaction hash table with explorer links, verified live
- [ ] **Feasibility / Beyond the prototype** (20% of grade): cost per recovery
      broken down (~$0.14 discovery (7 × $0.02) + ~$0.10 inference + settlement
      fees — testnet actuals read live from our node **and** the mainnet
      projection cited from `xrpl-fee-settings.json`, per D-007), latency budget
      (lead with the tickets result, D-006a), what breaks at 10k
      concurrent disruptions, real integration path (NDC/GDS/direct hotel APIs),
      reliability caveats incl. the testnet facilitator being best-effort, and
      the **duplicate-booking / partial-itinerary rollback problem** named
      explicitly
- [ ] Interoperability line — do NOT claim an MPP client works unchanged; the
      headers diverge from upstream x402 (PAYMENT-SIGNATURE vs X-PAYMENT,
      verified T+4). Claim what is true: the challenge body is spec-shaped, so
      interop is a header shim rather than a protocol gap

**Person B finishes:**
- [ ] Problem (3 paragraphs, no jargon)
- [ ] Product + target customer (companies/TMCs, not consumers)
- [ ] **Reachability** (20% of grade): the four-ingredient pattern; three named
      verticals (delivery van breakdown, stopped production line, cancelled
      venue); interoperability; developer accessibility; compliance position
      (not merchant of record, delegated authority, preauthorised envelope)
- [ ] OpenWallet mapping paragraph (delegated agent access, policy-gated signing)
- [ ] Claw Credit paragraph for envelope-exhausted (README only, do not build)
- [ ] Screenshots throughout
- [ ] Reproduce in 5 commands, verified from a clean clone

**T+20 → T+22: record the demo.** Screen recording with narration over the top.
Never live. Expect three takes. Follow `DEMO.md`.

**Write:** `docs/phase-5-submission.md` — what was cut and why, what is simulated,
known gaps. Honest.

---

## Phase 6 — Buffer (T+22 → T+24)

- [ ] Final `TRANSACTIONS.md` pass — every hash present with explorer links
- [ ] `FEEDBACK.md` cleaned into specific, constructive points
- [ ] **Submit the builder feedback Google form** (https://forms.gle/FZckiEAMU8oWXVbX7)
- [ ] Verify `.env.example` and setup instructions work from a clean clone
- [ ] No seeds committed. Check twice.
- [ ] `docs/` index up to date
- [ ] Final commit + push

---

## 🔪 CUT LIST — agreed in advance, executed without debate

When a milestone slips, cut the next item. No "give me one more hour."
**Record every cut in `docs/00-decisions.md`.**

1. ~~**Escrow**~~ — **ALREADY EXECUTED at T+0 (D-011)**, forced by the issuer flag
   rather than by time. → **vendor-initiated refund `Payment`** back to the session
   wallet.
   Visually this demonstrates the same thing: agent pays, vendor is sold out,
   money returns, agent reroutes. The README then states plainly that conditional
   escrow is the production design, and why — funds return automatically, without
   requiring the vendor's cooperation.
2. **The car booking leg** *(promoted above providers at T+0, D-013)* → keep
   flight → hotel. The car is the **terminal node** of the dependency chain, so
   removing it shortens the chain rather than breaking it; a two-link chain still
   proves that one decision constrains the next.
   **If cut, give the hotel decision a time constraint** (e.g. a late check-in
   cutoff driven by the flight's arrival), so the *temporal* dependency the car
   leg demonstrated survives in the hotel leg. Costs nothing to build.
3. **Vendor endpoints 7 and 8** *(demoted, D-013)* → six providers is still a real
   comparison. Keep the declined-provider moment by declining one of the remaining
   six.
4. **The approval prompt** → describe it in the README, don't build it.
5. **`SetRegularKey`** → mention as intended production design.

### Below the line — NEVER cut

- The trace panel
- The provider registry (hardcoded URLs = we lose the discovery criterion)
- One real XRPL transaction with a memo
- The failure path
- The README

If we are down to only those five, we still have a valid, decent entry.

---

## Milestone summary

| Milestone | Time | Test |
|---|---|---|
| M1 | T+3 | A hash on the explorer + text streaming to a page |
| M2 | T+7 | Agent pays a 402 and gets live data back |
| **M3** | **T+11** | **Full happy path end to end** |
| M4 | T+17 | **Hard feature freeze** |
| Submit | T+24 | Repo, video, form, hashes |
