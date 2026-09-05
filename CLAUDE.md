# CLAUDE.md — alternate.ai

Read this before doing anything. Re-read `PLAN.md` before starting any new phase.

---

## What we are building

**alternate.ai** — an autonomous **contingency management engine**.

> In aviation, the *alternate* is the backup airport you are required to nominate
> before you take off. A fallback designated in advance, funded in advance. That
> is exactly the product.

An organisation sets a **contingency profile** in advance: preferences, a spend
envelope, hard constraints. A **trigger loop** watches for events that break the
plan. When one fires, the agent matches it against a **template library** of
recovery playbooks, expands the chosen template with that user's profile and
history, pays for live availability across several providers, decides under hard
constraints, and **buys the fix itself**. No human in the loop for in-policy spend.

**The engine is domain-neutral (D-015).** Flight cancellation is one instance of a
general shape: an event breaks a plan, there is a short window, the fix means
buying from several unrelated parties under hard constraints. Logistics reroutes,
disaster-relief procurement and venue cancellations are the same shape.

**We build exactly one vertical: flight disruption.** Other industries are
described in the pitch and README, never implemented. That is honest *only*
because the engine has no flight-specific logic in it — a vertical is three data
files. See the scope rule below.

Demo scenario: cancelled flight SIN→CGK with a 09:00 meeting in Jakarta.

**One-line pitch:** a contingency engine that fixes broken plans by buying the
fix, inside a spending envelope you approved in advance.

### The claim discipline that keeps this honest

Because we build one vertical but claim generality, the claim is **architectural,
not demonstrated**. Two rules follow, and they are not negotiable:

- ✅ "Adding a vertical is a data file — here is the engine, with no flight code in it."
- ❌ "We support logistics and healthcare."

If flight-specific logic ever leaks into `engine.py`, `scoring.py`, `policy.py` or
`templates.py`, the Reachability claim becomes unsupported and we have broken our
own rule that no README claim may outrun the repo. A reviewer can check this by
reading one file. Keep it true.

### Why it needs autonomous payments (the thesis — protect this in every design choice)

1. **The envelope is a physical ceiling, not a policy check.** The session wallet
   holds exactly the envelope in RLUSD, and every agent purchase is an RLUSD
   payment to an allowlisted vendor. No bug, no prompt injection and no runaway
   loop can spend more, because there is no more. The account also holds a small
   XRP balance for network fees and account reserves, which the agent has no path
   to spend: the policy engine issues RLUSD payments to registry destinations and
   nothing else. This is a stronger safety property than any card-based agent can
   offer.
2. **Broad search requires sub-cent payments.** The registry holds 8 providers;
   the agent queries 7 and declines the eighth on purpose. Card rails cannot
   process a payment this small — that is a fact about rails, not about which
   asset settles it. Search breadth is where the value comes from: checking 7
   options instead of 2 is what finds the cheap hotel instead of the expensive one.

3. **A recommendation is worthless here.** The window is ~15 minutes. Anything
   routed through human approval loses the inventory.

If a design decision would weaken any of those three, it is the wrong decision.

**Scale (D-009, refined by D-012):** the demo runs a **$10 envelope** because the
testnet RLUSD faucet caps at 10 RLUSD/24h. **Purchases** scale 1/40; **discovery
does not** — it stays at the real **$0.02/query**, because the price of a data
query does not shrink because the trip is smaller. One set of numbers everywhere:

| | |
|---|---|
| Envelope | $10.00 |
| Discovery | 7 × $0.02 = **$0.14** |
| Purchases | $4.60 flight + $1.95 hotel + $0.49 car = $7.04 |
| Ends at | **$10.00 → $2.82** |
| Hotel cap | $6.25 (rejected option: $7.75) |

The RLUSD is a **revolving float, not a budget** — vendors are our own accounts,
so `python scripts/setup_wallets.py recycle` returns it. Only XRP fees are truly
spent (~0.00013 XRP/run against 100 XRP balances).

---

## Hard constraints

| Constraint | Value |
|---|---|
| Time | 24 hours total |
| Team | 2 people |
| Blockchain | **XRPL only.** Testnet. |
| **Forbidden** | **XRPL EVM Sidechain, or any other chain. Disqualifying.** |

### Absolute rules

- **NEVER** use the XRPL EVM Sidechain, Ethereum, Base, Solana, or any non-XRPL
  chain. All on-chain logic runs on XRPL Testnet.
- **NEVER** add npm, node_modules, a bundler, or a frontend build step. *(This rule
  is about the frontend. `pip` is fine and expected — see the approved dependency
  list under Technical decisions.)*
- **NEVER** add a database. In-memory dicts + one JSON file.
- **NEVER** hardcode XRPL fees or reserve amounts, and **never read them from the
  JSON snapshots for code purposes** — those are mainnet. Anything the code
  depends on comes live from our own node connection (`server_info` /
  `server_state`) on the network we are actually running against. See D-007.
- **NEVER** assert an amendment is live on **testnet** by checking
  `resources/xrpl-amendments.json` — that file is mainnet state from xrpscan.
  Check the testnet node via `server_info` (`amendment_blocked` / `feature`) for
  anything the code relies on.
- **The JSON snapshots** (`xrpl-fee-settings.json`, `xrpl-amendments.json`) are for
  **mainnet-readiness claims in the README's Feasibility section only** — "here is
  what this costs on mainnet today, at these live reserve and fee levels." Present
  testnet actuals *and* mainnet projections; that is stronger than either alone.
- **NEVER** commit seeds or private keys. Use `.env`, ship `.env.example`.
- **NEVER** integrate a real travel API (Amadeus, Sabre, Agoda). Sandbox approval
  takes days. All vendors are our own mocks. We say so in the README.
- **NEVER** start a new phase before the current phase's success criteria in
  `PLAN.md` are met.

### Behavioural rules for you (Claude Code)

- **Scope discipline is the whole game.** If asked to build X, build X. Do not add
  error-handling frameworks, abstraction layers, config systems, or "while I was
  here" refactors. We have 24 hours.
- **Prefer boring.** Standard library over a dependency. A dict over a class. A
  function over a factory. If a solution needs more than ~50 lines, propose the
  simpler version first.
- **Never silently swallow an XRPL error.** Surface it. A failed transaction that
  looks like a success will cost hours.
- **Append every successful transaction hash to `TRANSACTIONS.md` immediately.**
  Never batch this.
- **When you hit developer friction, add two lines to `FEEDBACK.md`.** Docs gaps,
  confusing errors, flaky endpoints. This is 10% of the grade.
- **Ask before installing any new dependency.**
- **At the start of each session:** read `PLAN.md`, state which phase we are in,
  and build only what that phase lists.

---

## Documentation is continuous, not a final step

Two documentation surfaces, with different jobs. Keeping both current as we go is
part of "done," not a Phase 5 activity.

### `docs/` — the working record (write during the phase)

Raw, technical, honest. What we built, what we chose, what broke, what we
learned. Future-us and the README both draw from it.

**At the end of every phase, before moving on:**

1. Write or update `docs/phase-N-<name>.md` using the template in
   `docs/README.md`
2. Append any architectural decision to `docs/00-decisions.md` (one entry:
   context, decision, consequence)
3. Update the relevant `README.md` sections (see the map below)
4. Commit with `docs: phase N — <summary>`

**Also write to `docs/` immediately, mid-phase, when:**
- A decision is made that contradicts something in `CLAUDE.md` or `PLAN.md`
- A cut-list item is executed (record what was cut and why)
- A workaround is applied that a reviewer would otherwise find confusing
- An XRPL or x402 behaviour surprises us (this feeds `FEEDBACK.md` too)

### `README.md` — the graded submission (update as we go)

**~70% of the score is read out of this repo, and the README carries most of it.**
Treating it as a final-hour write-up is the single most common way to lose marks.

It ships as a skeleton with HTML comments marking each section. **Fill sections in
as the underlying work lands** — do not wait for Phase 5. Phase 5 is for
polishing, screenshots and the two long-form sections (Reachability, Beyond the
prototype), not for starting from zero.

**Phase → README section map:**

| After phase | Fill in these README sections |
|---|---|
| 0 Setup | What is real vs simulated; Running it |
| 1 Skeleton | XRPL integration table; Memo format |
| 2 Paid loop | x402 usage; Agentic transaction flow; Starter Kit integration |
| 3 Full journey | How the agent creates value (paste a real trace); Customer journey; Architecture; Transaction hashes |
| 4 Failure + polish | Trust & governance table; Failure handling |
| 5 Submission | Problem; Product; Why autonomous payments; Reachability; Commercial model; Beyond the prototype; screenshots |

**Rule: never write a README claim that `docs/` does not support.** If the README
says the agent rejects out-of-policy options, `docs/` should record how and
`tests/` should cover it.

---

## Judging weights — optimise for these

| Criterion | Weight | Where it is judged |
|---|---|---|
| Reachability | 20% | **README** |
| Creativity | 20% | Demo + README |
| Feasibility | 20% | **README** |
| Technical Depth | 20% | **Repo (incl. tests + docs/)** |
| UX & Design | 10% | Demo |
| Builder Feedback | 10% | **Hook + FEEDBACK.md + form** |

---

## Architecture

```
Browser (index.html)                    Phone/2nd tab (/approve)
  trace panel · envelope · tx links       approve / deny
            │  SSE                              │ poll
            └──────────────┬────────────────────┘
                           │
                 ┌─────────▼──────────┐
                 │  app/  FastAPI     │
                 │  agent · policy    │
                 │  registry · wallet │
                 └─────────┬──────────┘
                           │ x402 (402 → pay → retry)
                 ┌─────────▼──────────┐
                 │ vendors/ FastAPI   │  8 routers, x402-gated
                 │ flights · hotels   │
                 │ ground  · data     │
                 └─────────┬──────────┘
                           │
                 ┌─────────▼──────────┐
                 │ t54 facilitator    │  xrpl-x402.t54.ai
                 └─────────┬──────────┘
                           │
                 ┌─────────▼──────────┐
                 │   XRPL Testnet     │
                 │ Payment · Memos    │
                 │ Memos · SourceTag  │
                 └────────────────────┘
```

### Engine shape (D-015) — the domain lives in data, not code

```
  Event sources            Profile store          Template library
  poll · webhook · manual   profiles/*.json        verticals/*/template.yaml
         \                       |                      /
          +----------> Trigger evaluator <-------------+
                              |
                     Contingency Engine          ← NO domain logic here
              match template → plan → score → act
                              |
         +--------------------+--------------------+
         |                    |                    |
     Registry            Policy/caps            Executor
   (resources for      (budget, approval)    adapters: mock | xrpl
    this vertical)                                   |
                              SSE trace → UI
```

Swapping industry = swapping data files, zero code change. That property *is* the
Reachability argument, so protect it.

### Layout

```
singhacks_2026/
├── CLAUDE.md · PLAN.md · README.md · DEMO.md
├── TRANSACTIONS.md · FEEDBACK.md · .env.example
├── docs/
│   ├── README.md            index + conventions + templates
│   ├── 00-decisions.md      running decision log
│   └── phase-N-*.md         one per phase
├── app/                 ← NO domain logic anywhere in here
│   ├── main.py          FastAPI: SSE stream, trigger + approval endpoints
│   ├── engine.py        orchestrator: match template → plan → score → act
│   ├── templates.py     load + validate playbook files
│   ├── profiles.py      user profile: preferences, constraints, history
│   ├── triggers.py      polling loop over a pluggable event source + manual fire
│   ├── registry.py      resource registry, loaded from the vertical's data file
│   ├── scoring.py       DETERMINISTIC constraint scoring
│   ├── policy.py        caps, approval thresholds, duplicate guard
│   ├── executor.py      adapters: mock | xrpl
│   ├── wallet.py        session wallet, treasury, balances
│   ├── xrpl_ops.py      payment / refund / memo helpers
│   ├── x402_client.py   402 challenge handling
│   ├── receipts.py      receipt ledger (tx ↔ decision ↔ policy rule)
│   └── static/index.html
├── verticals/           ← ALL domain knowledge lives here
│   └── flight-disruption/
│       ├── template.yaml    recovery playbook: steps, slots, constraints
│       ├── registry.yaml    the 8 providers for this domain
│       └── events.yaml      mock event feed the trigger loop polls
├── profiles/            traveller-01.json — preferences, budget, history
├── vendors/main.py      ALL 8 mock providers, one app, x402-gated routers
├── tests/               test_policy.py, test_scoring.py, test_templates.py
└── scripts/setup_wallets.py
```

**The test that keeps D-015 honest:** grep `app/` for "flight", "hotel", "airport".
If it hits anything outside a comment, domain logic has leaked and the
Reachability claim is no longer true.

**One vendor app with eight routers. Not eight services.** Data-driven handlers,
so extra providers are nearly free.

| # | Endpoint | Capability |
|---|---|---|
| 1 | `/flights/skyline` | flight |
| 2 | `/flights/aeroconnect` | flight |
| 3 | `/hotels/aurora` | hotel |
| 4 | `/hotels/transit-inn` | hotel |
| 5 | `/hotels/meridian` | hotel |
| 6 | `/ground/swiftcar` | ground |
| 7 | `/ground/metrolink` | ground |
| 8 | `/data/status` | status / waiver |

**8 registered, 7 queried, 1 declined.** The declined provider is the
search-vs-commit moment: it must be a real registry entry the agent evaluates and
turns down, visible in the trace with the stated reason — never a narrative
flourish. Which one is declined is decided at Phase 3, from the run, not fixed here.

---

## Interface contract (agreed, do not renegotiate)

```python
# x402_client.py
pay_and_fetch(provider_id, path, params, max_price) -> {
    "ok": bool, "data": dict, "price_paid": str,
    "tx_hash": str, "ledger_index": int
}

# xrpl_ops.py
purchase(provider_id, item_id, amount_rlusd, booking_ref, decision_id) -> {
    "ok": bool, "tx_hash": str, "confirmation_code": str
}
# Escrow was cut at T+0 (D-011), so create_hold() is replaced by the refund path.
# This is the ONE contract change since it was agreed; everything else stands.
refund(provider_id, amount_rlusd, booking_ref, decision_id) -> {
    "ok": bool, "tx_hash": str
}

# wallet.py
envelope_status() -> {"funded": str, "spent": str, "remaining": str, "tx_count": int}
```

Person B builds against stubs returning fake hashes from minute one. Person A
makes them real underneath. Neither blocks the other.

### Trace event schema (drives the whole UI)

```python
{"type": "trace",    "id": str, "text": str, "detail": str|None,
                     "cost": str|None, "status": "running"|"done"|"rejected"}
{"type": "purchase", "label": str, "amount": str, "tx_hash": str, "explorer_url": str}
{"type": "envelope", "remaining": str, "spent": str, "pct": float}
{"type": "approval", "reason": str, "amount": str, "option": str}
{"type": "error",    "text": str, "recovery": str}
```

---

## Technical decisions (already made — do not revisit)

**Stack:** Python 3.13, FastAPI, `xrpl-py`, `x402-xrpl` (t54-labs, D-010).
Frontend is ONE `index.html` with Tailwind via CDN and vanilla JS over SSE.

**Approved dependencies — nothing else without asking:**

```
fastapi, uvicorn, httpx, xrpl-py, python-dotenv, x402-xrpl, openai, pytest
```

**Asset — one, deliberately (D-002a, supersedes D-002):**

All agent spending is **RLUSD**: the 7 discovery payments and the 3 purchases
alike. The envelope *is* the session wallet's RLUSD trust line balance — one
number, one ceiling, one story. The UI reads `$10.00 → $2.82` (D-009, D-012).

**Live testnet values, already set up:**

| | |
|---|---|
| RLUSD issuer | `rQhWct2fv4Vc4KRjRgMrxa8xPN9Zx9iLKV` |
| Currency (hex) | `524C555344000000000000000000000000000000` |
| Session wallet | `r9Pwpy1iBRXFEeZdn8ix51tUJfoj2PCwD8` |
| Faucet | https://tryrlusd.com/ — 10 RLUSD/24h, GitHub sign-in, **manual** |

Trust lines are set on the session wallet and all 8 vendors. Between runs, use
`python scripts/setup_wallets.py recycle` — the envelope is recycled from the
vendor accounts, not consumed.

XRP in the session account is **operational only** — base reserve, owner reserves,
~10 drops per transaction in fees. It is not agent-spendable, because the policy
engine only ever issues RLUSD payments to allowlisted registry destinations.

Consequence to handle in Phase 0: **every vendor account needs an RLUSD trust
line** — 8 `TrustSet` transactions, scripted once in `scripts/setup_wallets.py`.

**Escrow asset — RESOLVED T+0, escrow is CUT (D-011).** The check was run:
issuer `rQhWct2fv4Vc4KRjRgMrxa8xPN9Zx9iLKV` has `Flags = 0x819a0000`, and
**`lsfAllowTrustLineLocking` is NOT set** — so RLUSD token escrow is unavailable,
regardless of `TokenEscrow` being an enabled amendment. Cut-list item 1 applies:
the refundable hold is a **vendor-initiated refund `Payment`** back to the session
wallet. Do not build `EscrowCreate`/`Finish`/`Cancel`. The README describes
conditional escrow as the production design and says why it is better — funds
return automatically on a time bound, without depending on the vendor's
cooperation or solvency.

**Agent is hybrid, not pure LLM:**
- LLM: parse objective, choose which providers to query, select among scored
  options, write the human-readable reasoning line.
- Deterministic Python: constraint scoring, cap enforcement, arithmetic.

A pure-LLM decision loop will pick something stupid on the take we record. In the
README call this "deterministic constraint scoring with LLM-driven planning and
selection."

**LLM provider: OpenAI** (we have credits). `OPENAI_API_KEY` in `.env.example`.

- Use the **fastest small model available**. Confirm the exact id against the live
  model list (`client.models.list()`) at implementation time — do not trust a
  model name from memory. `gpt-4o-mini` is the placeholder until verified.
- **Cap output tokens hard.** The LLM writes short reasoning lines and makes
  selections; it does not write essays.
- **Exactly three call sites, no more:** (1) parse objective → constraints,
  (2) choose which providers to query, (3) select among scored options and write
  the one-line reason. Everything else is deterministic Python.
- **Latency budget:** if total LLM time across the run exceeds ~15s, cut call site
  (1) and hardcode the constraint set from the envelope config.

**Every transaction carries `SourceTag` + `Memos`:**

```python
{
  "SourceTag": 4021,                       # agent identifier
  "Memos": [{"Memo": {
      "MemoType": to_hex("alternate/booking"),
      "MemoData": to_hex("BK-7741|decision:d_014|rule:hotel_cap_6_25")
  }}]
}
```

Traceability answer: anyone can open a transaction on the explorer and see which
decision caused it and which policy rule permitted it.

**`SetRegularKey` on the session wallet** (D-008). Keep the transaction — it is one
transaction and it genuinely demonstrates key delegation on ledger.

- ✅ Claim: "the agent signs with a regular key that can be rotated or disabled
  without moving funds."
- ❌ Do **not** claim: "the master key stays offline." The master seed is in `.env`
  on the demo machine. Offline custody is intended production design and is
  explicitly **not demonstrated** in this build.

---

## Known traps (each of these costs an hour)

- **Ripple epoch.** `FinishAfter` / `CancelAfter` are seconds since 2000-01-01,
  not Unix. Subtract `946684800`. One helper, used everywhere.
- **Sequence collisions.** Concurrent submissions from one account fail. The fix
  is **per-account locks plus Tickets** (D-006a, supersedes D-006) — *not* one
  global lock, which needlessly serialises independent wallets and is too slow
  for M3. Pre-allocate 8 tickets on the session wallet with `TicketCreate`, then
  fire the discovery leg concurrently with `TicketSequence` set and `Sequence: 0`.
  `TicketBatch` is a live amendment; verify on testnet before relying on it.
  Do this in Phase 1, not when it breaks in Phase 3. **Fallback:** if tickets are
  not working by the end of Phase 1, drop to per-account locks, record it in
  `docs/00-decisions.md`, and describe the intended design in the README. Do not
  burn Phase 2 on this.
- **Account reserves.** Each trust line locks a 0.2 XRP owner reserve. All 10
  accounts hold 100 XRP, so this is covered; watch it if we add ledger objects.
- **Faucet limits.** Fund everything in hour 1. Do not be re-funding at hour 20.
- **LLM latency.** Cap reasoning tokens and use a fast model, or the 90-second
  story becomes 4 minutes.
- **Token escrow.** Resolved and cut (D-011) — the issuer flag is unset. The trap
  worth remembering: an amendment showing `enabled=true` does **not** mean the
  feature is usable. `TokenEscrow` is live, but locking an issued token also needs
  the *issuer* to set `lsfAllowTrustLineLocking`. Amendment status is necessary,
  not sufficient.
- **`tecNO_LINE` ordering.** An account cannot receive an IOU before its trust
  line exists. Issuer address → `TrustSet` → then funding. This bit us in Phase 0:
  the RLUSD issuer address is not on the faucet page or xrpl.org, so it had to be
  found in the vendored dev-portal skill before anything could be claimed.

---

## Key resources

- Facilitator setup: https://xrpl-x402.t54.ai/#setup
- x402 SDK: `x402-xrpl` on PyPI (D-010). Docs: https://xrpl-x402.t54.ai/docs
- Facilitator (testnet): https://xrpl-facilitator-testnet.t54.ai  network `xrpl:1`
- NOT `x402-secure` (https://github.com/t54-labs/x402-secure) - that is the
  Trustline risk/proxy SDK, a different package
- RLUSD faucet: https://tryrlusd.com/
- RLUSD CLI: https://github.com/t54-labs/rlusd-cli
- CLI for quick verification: https://github.com/ripple/xrpl-up
- OpenWallet (delegated agent access, policy-gated signing): https://openwallet.sh/
- Agent credit reference: https://www.claw.credit/
- Explorer: https://testnet.xrpl.org/transactions/{hash}
- Local skill: `/xrpl-agentic-resources` (invoke it for XRPL questions)

---

## Definition of done

1. Agent runs end to end: objective → discovery payments → decision → purchases
   → delivered confirmations.
2. At least one successful XRPL transaction, hashes in `TRANSACTIONS.md` and
   clickable explorer links **in the UI**.
3. One failure path works live (sold-out-after-payment → refund → reroute).
4. Provider selection comes from `registry.py`, never hardcoded URLs.
5. `tests/` passes.
6. `docs/` has one file per completed phase plus a decision log.
7. README complete: problem, product, agent value, customer journey, agentic
   transaction flow, architecture, x402 flow, Starter Kit usage, transaction hash
   table, governance, failure handling, reproduce steps, beyond-the-prototype.
8. `FEEDBACK.md` has real entries; hook ran throughout; form submitted.
