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

<!-- Append new decisions below, numbered from D-007. -->
