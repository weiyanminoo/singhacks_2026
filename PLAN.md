# PLAN.md — alternate.ai build roadmap

24 hours. 2 people. ~34 productive person-hours.

**Rule: do not start a phase until the previous phase's success criteria are met.**
If a milestone slips, execute the cut list at the bottom. No debate.

**Every phase ends with three things**, not one: working code, a
`docs/phase-N-*.md` entry, and the mapped README sections filled in. A phase is
not done until all three are done.

---

## Roles

- **Person A — the money spine.** XRPL wallets, payments, escrow, memos, the
  vendor app, x402 both sides, receipt ledger.
- **Person B — the brain and the face.** Agent orchestration, registry, policy
  engine, scoring, SSE, UI, approval flow.

Person B works against stubs from minute one. Person A replaces them underneath.

---

## Phase 0 — Setup (T+0 → T+1) · BOTH

Nothing else starts until this is done.

- [ ] `bash skills/install.sh`
- [ ] `bash skills/xrpl-agentic-resources/scripts/refresh.sh`
- [ ] Install the feedback hook from `agent-instruction.md` — **10% of grade**
- [ ] Read https://xrpl-x402.t54.ai/#setup
- [ ] Create 2 testnet accounts (treasury, session), fund generously from faucet
- [ ] Get testnet RLUSD from https://tryrlusd.com/, set trust lines
- [ ] Verify one payment + one escrow round-trip via `xrpl-up` CLI, before any app code
- [ ] Repo skeleton, `.env.example`, `docs/`, `TRANSACTIONS.md`, `FEEDBACK.md`
- [ ] Both read the interface contract in `CLAUDE.md` out loud and agree it

**Success:** wallets funded, RLUSD held, one CLI-verified payment on the explorer,
hook running, both people agree the contract.

**Write:** `docs/phase-0-setup.md` — account addresses and roles, exact faucet and
trust line steps, anything that did not work first time.
**README:** *What is real vs simulated*, *Running it*.

---

## Phase 1 — Skeleton (T+1 → T+3)

**Person A**
- [ ] `xrpl_ops.py`: connect, sign, submit, wait for validation
- [ ] Sequence serialization (async lock) — **do this now, not later**
- [ ] Ripple-epoch helper (`unix_to_ripple(ts) = ts - 946684800`)
- [ ] One RLUSD `Payment` with `SourceTag` + `Memos`, landed and verified
- [ ] Fee/reserve values read from `xrpl-fee-settings.json`, not hardcoded

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

## Phase 2 — The paid loop (T+3 → T+7)

**Person A**
- [ ] `vendors/main.py`: one FastAPI app, routers for `/flights/skyline`,
      `/hotels/aurora`, `/data/status`
- [ ] x402-gate them via `x402-secure`, priced in XRP drops
- [ ] `x402_client.py`: real 402 challenge → pay → retry
- [ ] Free tier on data endpoints returns schema + stale sample; paid returns live

**Person B**
- [ ] `registry.py`: 6 providers with id, capability, endpoint, price, reliability
- [ ] `agent.py`: objective parsing → provider selection → query loop
- [ ] `policy.py`: per-tx cap, category cap, envelope cap, approval threshold,
      duplicate-purchase guard
- [ ] `scoring.py`: deterministic constraint scoring

### ✅ MILESTONE M2 (T+7)
**The agent picks a provider from the registry, receives a 402, pays on XRPL, and
gets live data back.** The commercial loop exists in miniature.

*If M2 slips past T+8: cut items 1 and 2 from the cut list immediately.*

**Write:** `docs/phase-2-x402-loop.md` — the exact 402 challenge and response
shape observed, facilitator setup and pinned version, per-call latency measured,
the free-tier pattern, the registry schema.
**README:** *x402 usage*, *Agentic transaction flow*, *Starter Kit integration*.

---

## Phase 3 — The full journey (T+7 → T+11)

**Person A**
- [ ] Remaining 3 vendor routers with genuinely different price/inventory/latency
- [ ] `EscrowCreate` for the hotel hold; `EscrowFinish` on check-in;
      `EscrowCancel` path
- [ ] `SetRegularKey` on the session wallet
- [ ] `receipts.py`: JSON ledger mapping tx_hash ↔ decision_id ↔ policy_rule ↔ booking_ref

**Person B**
- [ ] **The dependency chain** — this is the centrepiece:
      flight time decided → constrains hotel choice → constrains car timing
- [ ] Search-vs-commit decision: the agent explicitly reasons about whether one
      more $0.02 query is worth the time given decaying inventory
- [ ] At least one **rejected** option shown with the reason
      (e.g. "$310 Aurora Grand meets all criteria but breaks $250 cap")
- [ ] `/approve` page: pending approval, two buttons, resolves the block
- [ ] Explorer links rendered inline next to each purchase in the UI
- [ ] Reset button

### ✅ MILESTONE M3 (T+11) — THE CRITICAL ONE
**The full happy path runs start to finish in under 2 minutes:** cancellation →
8 discovery payments → dependent decisions → 3 purchases → confirmations →
envelope drained → all hashes visible and clickable.

*If M3 slips past T+12: cut items 3 and 4, go straight to Phase 5.*

**Write:** `docs/phase-3-agent-decisions.md` — the scoring function and its
weights, how the dependency chain is sequenced, the search-vs-commit heuristic,
what the LLM decides vs what Python decides, a full annotated trace from one run.
**README:** *How the agent creates value* (paste a real trace), *Customer
journey*, *Architecture*, *Transaction hashes* table.

---

## Phase 4 — Sleep + failure + polish (T+11 → T+17)

**T+11 → T+14: sleep in staggered shifts.** Do not skip. Hour 19 spent debugging
what you broke at hour 18 is the classic way to lose.

**Person A (T+14 → T+17)**
- [ ] Failure path: vendor returns sold-out AFTER payment → escrow cancel /
      refund → agent reroutes → only the second option is paid
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
      broken down (~$0.16 discovery + ~$0.10 inference + settlement fees *cited
      from `xrpl-fee-settings.json`*), latency budget, what breaks at 10k
      concurrent disruptions, real integration path (NDC/GDS/direct hotel APIs),
      reliability caveats incl. the testnet facilitator being best-effort, and
      the **duplicate-booking / partial-itinerary rollback problem** named
      explicitly
- [ ] One line on interoperability: MPP is backwards-compatible with x402, so an
      MPP client could consume our endpoints unchanged

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

1. **Escrow** → plain `Payment` instead. README describes the escrow design and
   the transaction shape we would have used.
2. **Vendor endpoints 5 and 6** → four providers is still a real comparison.
3. **The car booking leg** → keep flight → hotel. The dependency chain survives
   with two legs.
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
