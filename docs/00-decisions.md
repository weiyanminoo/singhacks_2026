# Decision log

Every non-obvious choice, and every cut-list item executed. Append only.

Template:

```
### D-00N · <title>
**Date/time:** T+X
**Context:** …
**Decision:** …
**Alternatives considered:** …
**Consequence:** …
```

---

## Pre-agreed (before T+0)

These were settled during planning. Recorded here so the reasoning survives.

### D-001 · XRPL Testnet only, no EVM sidechain
**Context:** The challenge explicitly disqualifies blockchain logic built on the
XRPL EVM Sidechain or any other chain.
**Decision:** All on-chain functionality runs on XRPL Testnet using native
primitives only.
**Alternatives considered:** None viable.
**Consequence:** No smart contracts available. Conditional logic must use native
Escrow (crypto-conditions, time bounds), Payment Channels, and multisign. This is
a constraint that pushes us toward more interesting primitive usage than most
teams will attempt.

### D-002 · Two assets — RLUSD for value, XRP for micropayments and escrow
**Context:** An envelope displayed in XRP is illegible to a viewer; they cannot
tell whether 312 XRP is a lot. Token escrow requires the issuer to have
`Allow Trust Line Locking` enabled, which we cannot set on testnet RLUSD.
**Decision:** RLUSD for the three purchases and the envelope balance. XRP for the
eight discovery micro-payments and for escrow.
**Alternatives considered:** All-XRP (illegible UI); all-RLUSD (blocked on the
issuer flag).
**Consequence:** The UI reads `$400.00 → $118.40`. Defensible in the README as a
design choice: stablecoin for value transfer where price stability matters,
native asset for high-frequency micropayments and conditional holds.

### D-003 · Hybrid agent — LLM plans and selects, Python scores
**Context:** A pure-LLM decision loop is non-deterministic and will make a poor
choice on the one run we record.
**Decision:** The LLM parses the objective, chooses which providers to query,
selects among scored options, and writes the human-readable reasoning line. All
constraint scoring, cap enforcement and arithmetic is deterministic Python.
**Alternatives considered:** Pure LLM (unreliable); pure rules (not an AI agent
in any meaningful sense, and fails the challenge's intent).
**Consequence:** Reproducible demo. Described in the README as "deterministic
constraint scoring with LLM-driven planning and selection."

### D-004 · Mock vendors, stated openly
**Context:** Real travel API sandbox approval (Amadeus, Sabre, Agoda) takes days.
We have 24 hours.
**Decision:** Six mock providers with genuinely different pricing, inventory and
latency, written by us. Declared near the top of the README.
**Alternatives considered:** Scraping (slow, fragile, legally shaky, and would
break on stage); a single real API (rate-limited, would undermine the
multi-provider comparison that is the point).
**Consequence:** More reproducible for a reviewer, and lets us engineer genuinely
interesting trade-offs. The README must carry a credible integration path
(NDC/GDS/direct hotel APIs, with the x402 wrapper as the only new component).

### D-005 · No frontend build tooling
**Context:** 24 hours, two people, neither dedicated to frontend.
**Decision:** One `index.html`, Tailwind via CDN, vanilla JS consuming Server-Sent
Events. No npm, no bundler, no build step.
**Alternatives considered:** React/Next.js — a second environment that can break
at 3am for no scoring benefit.
**Consequence:** Nothing to install or build. The trace panel is a div that
appends lines. Roughly 150 lines of JS total.

### D-006 · Serialize XRPL submissions from the start
**Context:** Concurrent transaction submissions from one account collide on
`Sequence`, and this surfaces as confusing intermittent failures.
**Decision:** A single async lock around all submissions, implemented in Phase 1.
**Alternatives considered:** Explicit sequence management (more correct, more
code); discovering it later (guaranteed to cost 90 minutes at a bad moment).
**Consequence:** Slightly slower under load. Noted in the README's scalability
section as something production would replace with per-wallet sequence pools.

---

## During the build

<!-- Append new decisions below, numbered from D-009. -->

### D-002a · Single-asset envelope — all agent spending in RLUSD
**Supersedes:** [D-002](#d-002--two-assets--rlusd-for-value-xrp-for-micropayments-and-escrow). D-002 is kept above for the reasoning history.
**Date/time:** T+0
**Context:** D-002 split spending across two assets — RLUSD for purchases, XRP for
discovery and escrow. The agreed `envelope_status()` contract returns one
`remaining` string, which cannot represent two asset balances. Resolving it with
two counters was considered and rejected: the single strongest asset we have is
one number that is the ceiling, and splitting it weakens the story more than the
two-asset design gains.
**Decision:** All agent spending is RLUSD — the seven discovery payments and the
three purchases alike. The envelope *is* the session wallet's RLUSD trust line
balance. One number, one ceiling, one story.
**Alternatives considered:** Two counters (weakens the headline claim); pinned-rate
XRP→USD display conversion (introduces a rate nobody can verify and an oracle
question at judging).
**Consequence:** Every vendor account needs an RLUSD trust line — eight `TrustSet`
transactions, scripted once in `scripts/setup_wallets.py` during Phase 0. XRP in
the session account becomes operational only: base reserve, owner reserves, and
~10 drops per transaction in fees. It is not agent-spendable, because the policy
engine only ever issues RLUSD payments to allowlisted registry destinations.
The sub-cent argument is unaffected — it was always about rails, not denomination.
A $0.02 payment is impossible on card networks whatever the asset, and x402 on
XRPL settles RLUSD. Escrow asset is resolved separately in Phase 0 by inspecting
the testnet RLUSD issuer's `lsfAllowTrustLineLocking` flag; if unset, escrow is
cut to a vendor-initiated refund `Payment` and conditional escrow is described as
production design.

### D-006a · Per-account locks plus Tickets, superseding the global lock
**Supersedes:** [D-006](#d-006--serialize-xrpl-submissions-from-the-start). D-006 is kept above for the reasoning history.
**Date/time:** T+0
**Context:** D-006 mandated a single async lock around all submissions. Two
problems surfaced before any code was written. First, the constraint is wrong in
scope: sequence collisions are *per-account*, so one global lock needlessly
serialises the treasury and session wallets, which have independent sequence
streams. Second, it is too slow for the target: the happy path is ~13
transactions, and at a ~3–5s ledger close, fully serialised settlement consumes
40–65 seconds before a single LLM token is generated — against a 90-second story
and a 2-minute M3 ceiling. `TicketBatch` is `enabled=true`, so the ledger already
offers the correct primitive.
**Decision:** Per-account locks, not one global lock. Plus `TicketCreate` to
pre-allocate eight tickets on the session wallet, so the discovery leg fires
concurrently with `TicketSequence` set and `Sequence: 0`. That collapses the
discovery leg from roughly 35 seconds to about one ledger close.
**Alternatives considered:** Keeping the global lock (misses M3's timing);
explicit manual sequence management (more code, same benefit, more ways to be
wrong under concurrency).
**Consequence:** Meets the latency budget, and is a materially better Technical
Depth story than a mutex — we used a live amendment to solve a real constraint
rather than working around it. Earns a paragraph in the README performance
section. **Fallback:** if tickets are not working by the end of Phase 1, fall back
to per-account locks, record it here, and describe the intended design in the
README. Phase 2 is not to be spent on this.

### D-007 · Live testnet values for code, mainnet JSON snapshots for README claims
**Date/time:** T+0
**Context:** `CLAUDE.md` required reading fees and reserves from
`skills/xrpl-agentic-resources/resources/xrpl-fee-settings.json` and checking
amendment status in `xrpl-amendments.json`. Both files are produced by
`refresh.sh` from `xrpscan.com/api/v1/...`, which is **mainnet** state — but we
build on Testnet. Testnet enables amendments earlier than mainnet, so the rule as
written would make us under-claim available features, and the reserve figures are
mainnet reserves. They agree today (10 drops base fee, 1 XRP account reserve,
0.2 XRP owner reserve) but are not guaranteed to.
**Decision:** Split the usage by purpose. Anything the **code** depends on is read
live from our own node connection (`server_info` / `server_state`) against the
network we are actually on. The JSON snapshots are used **only** for
mainnet-readiness claims in the README's Feasibility section.
**Alternatives considered:** Using the JSON files for everything (unsound);
dropping them entirely (loses a genuinely useful Feasibility input).
**Consequence:** Correct behaviour on testnet, and a stronger Feasibility section:
we can present testnet actuals *and* mainnet projections sourced from live
mainnet state, which is better than either alone. Costs one helper that reads
`server_info` at startup.

### D-009 · Demo runs at 1/40 scale on real RLUSD — $10 envelope, not $400
**Refines:** [D-002a](#d-002a--single-asset-envelope--all-agent-spending-in-rlusd). The single-asset ruling stands; only the magnitude changes.
**Date/time:** T+0
**Context:** D-002a set the envelope at $400 in real testnet RLUSD. The only
testnet RLUSD faucet the docs point to (tryrlusd.com) dispenses **10 RLUSD per
24 hours, behind GitHub OAuth**, with no API and no bulk path. $400 is
unreachable — daily claims for the whole event would not get close.
**Decision:** Keep everything in genuine RLUSD and scale the demo by 1/40.
Envelope **$10.00**; hotel cap $6.25; ground cap $1.00; approval threshold $3.75;
purchases $4.60 / $1.95 / $0.49; end state **$10.00 → $2.96**. Every figure is a
real RLUSD amount on a real trust line.
**Alternatives considered:** Issuing our own testnet stablecoin at full $400 scale
(unlimited and scriptable, but not Ripple's RLUSD, and a self-issued token coded
`RLUSD` risks reading as counterfeit); a hybrid of both; reverting to an XRP
envelope (reopens the two-asset problem D-002a closed).
**Consequence:** Everything on ledger is authentic RLUSD, which is the strongest
possible answer to "is this real?" — at the cost of the legible $400 headline.
Two follow-ons:
1. **The envelope is recycled, not consumed.** At 10/24h we would get ~one
   end-to-end run per day, which cannot survive Phase 3 testing plus three demo
   takes. The vendors are our own accounts, so
   `python scripts/setup_wallets.py recycle` sweeps vendor RLUSD back to the
   session wallet. Only XRP fees are truly spent.
2. **The README must separate demo scale from real-world economics.** Discovery
   at 1/40 is $0.0005/query, which is realistic for XRPL but *not* what a real
   data API costs. Feasibility should quote the real ~$0.02/query — the price of
   information does not scale with the size of the trip — and state plainly that
   the testnet demo is scaled because of the faucet cap. **Open question for
   Phase 2:** whether the x402 facilitator enforces a minimum price above
   $0.0005. If it does, discovery pricing moves back toward $0.02 and the
   envelope split changes.

### D-012 · Discovery stays at the real $0.02/query; only purchases scale
**Refines:** [D-009](#d-009--demo-runs-at-140-scale-on-real-rlusd--10-envelope-not-400).
**Date/time:** T+0
**Context:** D-009 scaled everything by 1/40, which put discovery at $0.0005/query.
That broke the demo in two ways. The beat sheet says *"pays a couple of cents per
query"* while 7 × $0.0005 = **$0.0035** — the envelope counter barely moves, so
the 20 seconds we spend watching discovery accumulate shows nothing, and the
narration is simply false. It also forced us to carry two different discovery
figures (demo vs README) and keep them straight forever.
**Decision:** Purchases scale 1/40; **discovery does not**. Discovery is
$0.02/query — the real price — giving $0.14 across 7 queries, 1.4% of a $10
envelope. Envelope reads **$10.00 → $2.82**.
**Alternatives considered:** Strict 1/40 on everything (internally consistent, but
invisible on screen and makes the narration a lie); raising the envelope
(impossible — faucet cap, D-009).
**Consequence:** The cost of a data query does not shrink because the trip is
smaller, so this is *more* honest than proportional scaling, not less. Demo
numbers and README unit economics are now the same number, so the dual
bookkeeping D-009 imposed disappears. Discovery is visible on screen and the
narration is accurate. Also near-certainly above any x402 facilitator minimum,
which de-risks the open question in D-009.
**Standing instruction:** if the facilitator *does* enforce a minimum above
$0.02, **stop and ask** — do not pick a fallback unilaterally.

### D-010 · x402 package is `x402-xrpl`, not `x402-secure`
**Date/time:** T+0
**Context:** `CLAUDE.md` named `x402-secure` in the stack, taken from the t54
GitHub link in the resource list. On inspection they are two different packages,
both real on PyPI. `x402-secure` (0.1.4) is t54's Trustline risk-engine client
SDK, and the vendored repo builds a facilitator *proxy* (its own
`pyproject.toml` is `x402-secure-proxy`, pinned to `>=3.11,<3.13`).
`x402-xrpl` (0.3.3) is "XRPL implementation of x402 payments (presigned Payment
scheme) with client + FastAPI" — the actual 402→pay→retry loop, on both merchant
and client side — and is what the official quickstart at xrpl-x402.t54.ai
installs.
**Decision:** Use `x402-xrpl`. Installed 0.3.2. `x402-secure` is not a dependency.
**Alternatives considered:** Both (extra SDK surface for a Trustline governance
angle we do not need); `x402-secure` alone (would leave us hand-rolling the 402
loop).
**Consequence:** Matches the official quickstart, so its docs and examples apply
directly. Note the proxy repo's `<3.13` cap does **not** apply to us — we are on
Python 3.13.1 and `x402-xrpl` requires only `>=3.11`. Testnet config confirmed:
facilitator `https://xrpl-facilitator-testnet.t54.ai`, network `xrpl:1`.

### D-011 · Cut-list item 1 executed — RLUSD token escrow is unavailable
**Date/time:** T+0
**Context:** `CLAUDE.md` required a five-minute Phase 0 check of whether the
testnet RLUSD issuer has `lsfAllowTrustLineLocking` set, since `TokenEscrow`
being an enabled amendment is not sufficient — the issuer must permit locking.
Verified against the real issuer `rQhWct2fv4Vc4KRjRgMrxa8xPN9Zx9iLKV` (Domain
`https://ripple.com/`, master key disabled, clawback enabled):
`Flags = 0x819a0000` → `lsfDefaultRipple`, `lsfDisallowXRP`, `lsfDisableMaster`,
`lsfRequireDestTag`, `lsfDepositAuth`, `lsfAllowTrustLineClawback`.
**`lsfAllowTrustLineLocking` is NOT set.**
**Decision:** Escrow is cut per cut-list item 1. The refundable hold becomes a
**vendor-initiated refund `Payment`** back to the session wallet. Conditional
escrow is described in the README as the production design.
**Alternatives considered:** Escrowing XRP instead (reintroduces the two-asset
envelope D-002a deliberately closed); asking Ripple to set the flag (not
available to us, and not in a 24-hour window).
**Consequence:** The failure path still demonstrates the same thing end to end —
agent pays, vendor is sold out, money returns, agent reroutes — and the demo
narration was already written to be mechanism-neutral. The README must say why
escrow is better than a refund: funds return automatically on a time bound,
without depending on the vendor's cooperation or solvency. That contrast is a
stronger Technical Depth point than a working escrow would have been on its own.
Removes `EscrowCreate`/`Finish`/`Cancel` from the Phase 3 checklist and the
XRPL integration table.

### D-004a · Provider count — 8 registered, 7 queried, 1 declined
**Supersedes:** the count in [D-004](#d-004--mock-vendors-stated-openly) only. The
mock-vendor reasoning in D-004 stands unchanged.
**Date/time:** T+0
**Context:** The count was inconsistent across the planning docs — the `CLAUDE.md`
thesis said 8 providers, the architecture and Phase 2 said 6, and M3 said 8
discovery payments. That number appears in the pitch, the registry, the demo
narration and the Feasibility cost breakdown, so it had to be pinned.
**Decision:** **8** providers in the registry — 2 flight, 3 hotel, 2 ground,
1 status/waiver. **7** queried at ~$0.02 = **$0.14**. **1 declined on purpose.**
**Alternatives considered:** 6 registered / 6 queried (loses the search-vs-commit
moment); keeping the numbers vague (guarantees a contradiction a judge can find).
**Consequence:** The declined provider must be a real registry entry the agent
evaluates and turns down, visible in the trace with its stated reason — never a
narrative flourish. Adding entries is nearly free because the vendor app is one
file with data-driven handlers. Which of the 8 is declined is decided at Phase 3,
from the run. Cut-list item 2 now drops endpoints 7 and 8, leaving 6 registered,
and the declined-provider moment survives by declining one of the remaining six.

### D-008 · `SetRegularKey` — key delegation is demonstrated, offline custody is not
**Date/time:** T+0
**Context:** `CLAUDE.md` claimed the master key "stays offline." In this build the
master seed is in `.env` on the demo machine, so that claim is not supported by
what we actually do. Our own rule is that no README claim may outrun what `docs/`
records.
**Decision:** Keep the `SetRegularKey` transaction — it is one transaction and it
genuinely demonstrates key delegation on ledger. Narrow the claim to what is
true: *the agent signs with a regular key that can be rotated or disabled without
moving funds*. Offline master-key custody is stated as intended production
design and explicitly noted as not demonstrated here.
**Alternatives considered:** Dropping the transaction (loses a real, cheap
demonstration); keeping the original wording (an unsupported claim in the
section judges probe hardest).
**Consequence:** A smaller claim we can defend under questioning instead of a
larger one we cannot. Remains cut-list item 5 if time forces it.
