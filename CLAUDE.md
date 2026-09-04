# CLAUDE.md — alternate.ai

Read this before doing anything. Re-read `PLAN.md` before starting any new phase.

---

## What we are building

**alternate.ai** — an autonomous disruption recovery agent.

> In aviation, the *alternate* is the backup airport you are required to nominate
> before you take off. A fallback designated in advance, funded in advance. That
> is exactly the product.

A traveller (or their employer) sets a **spend envelope** before a trip: a fixed
budget with rules attached. When their plan breaks — flight cancelled at 11pm —
an AI agent pays for live availability data across several providers, decides on
a recovery plan under hard constraints, and **buys the fix itself** in ~90
seconds. No human in the loop for in-policy spend.

Demo scenario: cancelled flight SIN→CGK with a 09:00 meeting in Jakarta.

**One-line pitch:** a recovery agent that fixes broken plans by buying the fix,
inside a spending envelope you approved in advance.

### Why it needs autonomous payments (the thesis — protect this in every design choice)

1. **The envelope is a physical ceiling, not a policy check.** The session wallet
   holds exactly $400. No bug, no prompt injection, no runaway loop can spend
   more, because the money is not there. This is a stronger safety property than
   any card-based agent can offer.
2. **Broad search requires sub-cent payments.** The agent queries 8 providers at
   ~$0.02 each. Card rails cannot process a 2-cent payment. Search breadth is
   where the value comes from — checking 8 options instead of 2 is what finds the
   $78 hotel instead of the $310 one.
3. **A recommendation is worthless here.** The window is ~15 minutes. Anything
   routed through human approval loses the inventory.

If a design decision would weaken any of those three, it is the wrong decision.

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
- **NEVER** add npm, node_modules, a bundler, or a frontend build step.
- **NEVER** add a database. In-memory dicts + one JSON file.
- **NEVER** hardcode XRPL fees or reserve amounts. Read them from
  `skills/xrpl-agentic-resources/resources/xrpl-fee-settings.json`.
- **NEVER** assert an amendment is live without checking `enabled` in
  `skills/xrpl-agentic-resources/resources/xrpl-amendments.json`.
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
                 │ vendors/ FastAPI   │  6 routers, x402-gated
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
                 │ Payment · Escrow   │
                 │ Memos · SourceTag  │
                 └────────────────────┘
```

### Layout

```
alternate-ai/
├── CLAUDE.md · PLAN.md · README.md · DEMO.md
├── TRANSACTIONS.md · FEEDBACK.md · .env.example
├── docs/
│   ├── README.md            index + conventions + templates
│   ├── 00-decisions.md      running decision log
│   └── phase-N-*.md         one per phase
├── app/
│   ├── main.py          FastAPI: SSE stream, run trigger, approval endpoints
│   ├── agent.py         orchestrator: plan → discover → decide → buy
│   ├── policy.py        caps, approval thresholds, duplicate guard
│   ├── registry.py      provider registry (discovery happens HERE, not hardcoded URLs)
│   ├── scoring.py       DETERMINISTIC constraint scoring
│   ├── wallet.py        session wallet, treasury, balances
│   ├── xrpl_ops.py      payment / escrow / memo helpers
│   ├── x402_client.py   402 challenge handling
│   ├── receipts.py      receipt ledger (tx ↔ decision ↔ policy rule)
│   └── static/index.html
├── vendors/main.py      ALL mock providers, one app, x402-gated routers
├── tests/               test_policy.py, test_scoring.py
└── scripts/setup_wallets.py
```

**One vendor app with six routers. Not six services.** Endpoints:
`/flights/skyline`, `/flights/aeroconnect`, `/hotels/aurora`,
`/hotels/transit-inn`, `/ground/swiftcar`, `/data/status`.

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
create_hold(provider_id, amount_xrp, booking_ref, cancel_after_s) -> {
    "ok": bool, "tx_hash": str, "escrow_seq": int
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

**Stack:** Python 3.11+, FastAPI, `xrpl-py`, `x402-secure` (t54-labs).
Frontend is ONE `index.html` with Tailwind via CDN and vanilla JS over SSE.

**Assets — two, deliberately:**
- **RLUSD** for the 3 purchases and the envelope balance. Dollar-denominated so
  the UI reads `$400.00 → $118.40`, far more legible than XRP amounts.
  Faucet: https://tryrlusd.com/
- **XRP** for the 8 discovery micro-payments and for escrow.

Escrow stays in XRP to avoid the TokenEscrow `Allow Trust Line Locking` issuer
flag requirement, which we cannot set on testnet RLUSD. Frame this in the README
as a design choice: stablecoin for value transfer, native asset for
high-frequency micropayments and conditional holds.

**Agent is hybrid, not pure LLM:**
- LLM: parse objective, choose which providers to query, select among scored
  options, write the human-readable reasoning line.
- Deterministic Python: constraint scoring, cap enforcement, arithmetic.

A pure-LLM decision loop will pick something stupid on the take we record. In the
README call this "deterministic constraint scoring with LLM-driven planning and
selection."

**Every transaction carries `SourceTag` + `Memos`:**

```python
{
  "SourceTag": 4021,                       # agent identifier
  "Memos": [{"Memo": {
      "MemoType": to_hex("alternate/booking"),
      "MemoData": to_hex("BK-7741|decision:d_014|rule:hotel_cap_250")
  }}]
}
```

Traceability answer: anyone can open a transaction on the explorer and see which
decision caused it and which policy rule permitted it.

**`SetRegularKey` on the session wallet.** Agent signs with the regular key;
master key stays offline, rotatable without moving funds.

---

## Known traps (each of these costs an hour)

- **Ripple epoch.** `FinishAfter` / `CancelAfter` are seconds since 2000-01-01,
  not Unix. Subtract `946684800`. One helper, used everywhere.
- **Sequence collisions.** Concurrent submissions from one account fail.
  Serialize payments through a single async lock, or manage `Sequence`
  explicitly. Do this in Phase 1, not when it breaks in Phase 3.
- **Account reserves.** Each escrow object locks a reserve. Fund generously early.
- **Faucet limits.** Fund everything in hour 1. Do not be re-funding at hour 20.
- **LLM latency.** Cap reasoning tokens and use a fast model, or the 90-second
  story becomes 4 minutes.
- **Token escrow.** Requires the issuer to have Allow Trust Line Locking enabled.
  We avoid this entirely by escrowing XRP.

---

## Key resources

- Facilitator setup: https://xrpl-x402.t54.ai/#setup
- x402 SDK: https://github.com/t54-labs/x402-secure
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
