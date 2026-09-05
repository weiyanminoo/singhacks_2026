# FEEDBACK.md — XRPL builder feedback

**Builder Feedback is 10% of the hackathon grade.** This file plus the automated
feedback hook plus the final Google form make up that score.

**How to use this:** every time you hit friction, add two lines. Right then, not
later. A docs gap, a confusing error, a flag you didn't know you needed, a
tutorial that skipped a step, a flaky endpoint. Specific beats polite.

At T+22, clean this into constructive points and submit the form.

- Feedback hook installed: ☐ (from `agent-instruction.md`, hour 0)
- Final Google form submitted: ☐ (https://forms.gle/FZckiEAMU8oWXVbX7)

---

## Google form — draft answers

**Re-check before submitting.** These describe state as of the engine milestone.
If the XRPL executor adapter and x402 integration land, update Q1 and Q4.

### Q1 · What did you build on XRPL?

alternate.ai — an autonomous contingency management engine. An organisation sets
a contingency profile in advance (preferences, hard constraints, a spend
envelope). A trigger loop watches an event feed; when an event breaks the plan,
the agent matches it against a declarative playbook, personalises the recovery
from the user's profile and decision history, pays per query to check live
availability across providers, decides under hard constraints, and buys the fix.
The engine is domain-neutral — all domain knowledge is data, so the demo vertical
(flight disruption) is one YAML file. Logistics reroutes and disaster-relief
procurement are the same shape.

What we used on XRPL specifically:

- **Payment** with **SourceTag** and **Memos** on every agent transaction. The
  memo carries `booking_ref|decision:<id>|rule:<policy_rule>`, so anyone opening
  a transaction on the explorer sees which decision caused it and which policy
  rule permitted it. That is our answer to agent traceability.
- **TrustSet** — RLUSD trust lines on the session wallet and all 8 supplier
  accounts (9 transactions, all tesSUCCESS).
- **TicketCreate / TicketSequence** — pre-allocated sequence numbers so the
  discovery leg submits concurrently instead of one ledger close at a time.
- **Live `server_info` reads** for fees and reserves. Nothing is hardcoded.
- **The spending ceiling is the wallet balance, not a code check.** The session
  wallet holds exactly the envelope, so no bug, prompt injection or runaway loop
  can exceed it — the money is not there.
- x402 (`x402-xrpl`) for pay-per-query discovery against the t54 testnet
  facilitator.

### Q2 · Practical concerns or problems building on XRPL?

Yes — six, roughly in order of time lost.

1. **The testnet RLUSD faucet is a hard blocker for agentic work.** 10 RLUSD per
   24 hours, behind GitHub OAuth, wallet-connect only, no address field, no API.
   Our accounts were created programmatically and already had trust lines set,
   but there is no way to say "send it to rXXX". The only path was exporting a
   family seed into a browser extension — precisely the habit security guidance
   says never to build. It then failed anyway: the site hung on "setting up
   trustline" (work we had already done, which it could not detect), and forcing
   it produced a generic "PREPARATION ERROR". Nothing ever reached the ledger. A
   10 RLUSD cap also makes a realistic spend envelope impossible, so our demo
   runs at 1/40 scale.
2. **An enabled amendment is not a usable feature.** `TokenEscrow` shows
   `enabled: true`, which reads as available. But locking an issued token also
   requires the *issuer* to set `lsfAllowTrustLineLocking`, and Ripple's testnet
   RLUSD issuer does not (`Flags = 0x819a0000`). We only found this because we
   checked the issuer's flags directly. We cut escrow as a result.
3. **The testnet RLUSD issuer address is not discoverable.** It is not on
   xrpl.org, not on the faucet page. We found it in the vendored dev-portal
   agent skill. This matters because trust lines must exist *before* an account
   can receive an IOU (`tecNO_LINE`), so the issuer address is on the critical
   path — you need it before you can ask for any tokens.
4. **Transport choice costs ~3x latency and nothing says so.** `submit_and_wait`
   over JSON-RPC took 13.6s per payment against a ~2.5s ledger close; the same
   code on WebSocket took 4.6s. Seven concurrent ticketed payments: 21.8s vs
   9.2s. Two thirds of our settlement time was client-side polling.
5. **Amendment and fee APIs are mainnet-only and do not say so.** The common
   endpoints (xrpscan `/amendments`, `/object/FeeSettings`) return mainnet state
   with no network field in the payload, so a cached copy looks authoritative
   for whatever chain you are on. We nearly gated code on mainnet amendment
   status while building on Testnet, where amendments activate earlier.
6. **A docs example used a checksum-invalid address.** `t54-labs/rlusd-skills`
   ships `--require-issuer rBvKgF3jSZWdJcwSsmoJspoXGpHUhBGurg` in a
   copy-pasteable command; it fails base58 validation. Agents copy these
   verbatim.

### Q3 · Did the XRPL AI Starter Kit save time, or get in the way?

Genuinely both, and the split is instructive.

**Saved time.** The vendored official dev-portal skills were the single most
useful artifact we touched. `xrpl-payments/references/payments.md` contained
`RLUSD_ISSUER_TESTNET`, the constant that unblocked our whole setup and that we
could not find on xrpl.org or the faucet. Having the XLS specs and docs indexes
locally also meant our agent could answer XRPL questions without guessing.

**Got in the way.** The bundled `xrpl-amendments.json` and
`xrpl-fee-settings.json` are mainnet snapshots presented without any network
label, and the skill instructs the agent to check amendment availability there.
On testnet that guidance is wrong, and it is wrong in the direction that makes
you under-claim features. We had to write our own rule: live values from our own
node for anything the code depends on, the JSON snapshots only for
mainnet-readiness claims in the writeup.

Two smaller frictions: `skills/install.sh` uses `ln -s`, which deep-copies under
MSYS on Windows, so the "installed" skill silently rots because the refresh
script only updates the canonical directory. And the skill directory is
committed as a git symlink, which Windows checks out as a text file containing
the target path, so no agent can see the skill at all until you fix it by hand.

**Suggestion:** stamp every bundled snapshot with the network it came from, and
make the install path Windows-aware (a directory junction works without admin).

### Q4 · Would you take this to mainnet? What is stopping you?

Yes for the ledger mechanics — nothing we rely on is exotic, and the economics
work. We measured mainnet at 10 drops base fee, 1 XRP account reserve and 0.2
XRP per object, which is negligible against the value of a recovered trip.
Testnet and mainnet reserve values agree today, so our measured costs carry over.

What stops us shipping tomorrow, honestly:

1. **Key management.** The agent signs with a seed in `.env`. `SetRegularKey`
   gives us a rotatable key without moving funds, but real deployment needs
   policy-gated signing with the master key in custody — the OpenWallet
   delegated-access model is the right shape and we have not built it.
2. **Duplicate booking and partial-itinerary rollback.** Stateful bookings
   punish naive retries: a duplicate call is a duplicate booking, and a
   three-leg recovery that fails on leg three leaves two legs paid for. Our
   duplicate-purchase guard is a partial answer, not a solution. This is the
   hardest unsolved problem in the product and it is not XRPL's fault.
3. **Facilitator dependency.** The testnet x402 facilitator is best-effort with
   no committed SLA. Production needs either a contracted facilitator or our own.
4. **Real inventory.** Our suppliers are mocks. Integration is NDC/GDS/direct
   APIs, with the x402 wrapper as the only genuinely new component.
5. **Compliance.** We are not merchant of record; we act under delegated
   authority against a preauthorised envelope. That position needs legal review
   before real money moves.

### Q5 · Additional comments

**The docs are written for human-paced wallets, not agents.** That is the single
biggest gap we hit. An agent submits many small transactions, so per-transaction
overhead dominates in a way it never does when a person clicks send. Everything
that cost us time follows from that: transport choice, sequence collisions,
concurrent submission.

`TicketCreate` is the correct answer to concurrent submission from one account —
each ticket carries its own sequence, removing the collision that otherwise
forces serialisation. Combined with WebSocket it took our discovery leg from
~95s to 9.2s. But Tickets appear in the reference under account management, not
in any agentic-payments guidance, so the path a builder naturally finds is a
global mutex, which is both slower and less correct.

**What would have saved us the most time:** an agentic-payments quickstart that
covers, in its first ten minutes — transport choice and why it matters, Tickets
for concurrency, trust-line ordering before funding (`tecNO_LINE`), the
Ripple-epoch offset, and the distinction between an amendment being enabled and
a feature being usable given issuer flags. Every one of those cost us real time,
and none of them are hard once stated.

---

## Template

```
### [HH:MM] Short title
**Area:** xrpl-py / x402 / facilitator / RLUSD / escrow / docs / starter kit / skill
**What happened:** …
**Time lost:** …
**What would have helped:** …
```

---

## Entries

<!-- Add entries below as you hit them. Do not wait until the end. -->

### [T+1] `submit_and_wait` over JSON-RPC costs ~3x the ledger, and nothing says so
**Area:** xrpl-py
**What happened:** A single `submit_and_wait` over `AsyncJsonRpcClient` took
**13.6s** against a testnet ledger closing every **~2.5s**. Seven concurrent
ticketed payments took 21.8s; the identical code on `AsyncWebsocketClient` took
**9.2s**, and a single payment dropped to 4.6s. So roughly two thirds of our
settlement latency was client-side polling, not consensus. Nothing in the docs or
the client's own docstrings indicates that transport choice carries a ~3x latency
penalty — both clients are presented as interchangeable, and JSON-RPC is the one
most quickstarts reach for because it needs no connection lifecycle.
**Time lost:** ~40 min, and we nearly shipped a design that would have blown a
90-second latency budget on polling overhead.
**What would have helped:** say plainly in the xrpl-py client docs that
`submit_and_wait` polls on JSON-RPC and should not be used on a latency budget,
and that WebSocket is the right transport for anything submitting more than a
couple of transactions. A one-line note on the client comparison page would do
it. The deeper point for agentic work: agents submit many small transactions, so
per-transaction overhead dominates in a way it does not for human-paced wallets —
worth its own note in the agent/payments guidance.

### [T+0] Testnet RLUSD faucet caps at 10 RLUSD/24h behind GitHub OAuth
**Area:** RLUSD
**What happened:** tryrlusd.com is the only testnet RLUSD faucet the docs point
to. It requires GitHub sign-in and dispenses "10 RLUSD every 24 hours". We are
building an agentic-payments demo whose whole thesis is a preauthorised spending
envelope — ours is $400. There is no path to funding a realistic envelope on
testnet, and no bulk/API option for hackathon or CI use. It also means the
8 vendor accounts in a multi-provider demo cannot be funded to test receipt
paths. The cap silently forces every XRPL agent-payment demo either into
sub-$10 amounts or off real RLUSD entirely, which undercuts the "use RLUSD for
agentic payments" story the ecosystem is pushing.
**Time lost:** ~25 min, plus a design decision that has to be reopened.
**What would have helped:** a higher testnet ceiling (or a request-with-reason
form), an API endpoint so setup can be scripted, and a line in the RLUSD docs
stating the cap up front — we only found it by loading the faucet page. Ideally
publish the testnet RLUSD issuer address in the docs so builders can set trust
lines before they have any balance.

### [T+0] RLUSD skill docs use a checksum-invalid placeholder address
**Area:** RLUSD / starter kit
**What happened:** `t54-labs/rlusd-skills` `skills/rlusd-x402/SKILL.md` shows
`--require-issuer rBvKgF3jSZWdJcwSsmoJspoXGpHUhBGurg` in a runnable example.
That address fails base58 checksum validation — `is_valid_classic_address()`
returns False and the node answers `actMalformed`. It reads as a real issuer
because the surrounding command is copy-pasteable. The one real address in the
repo (`rMxCKbEDwqr76QuheSUMdEGf4B9xJ8m5De`, in
`use-rlusd-xrpl/references/issuer-settings.md`) is mainnet-only and not labelled
as such next to the testnet examples.
**Time lost:** ~15 min chasing a fake address against testnet.
**What would have helped:** use an obviously-fake form (`rEXAMPLE...`) for
placeholders, or real per-network addresses in a small table — mainnet issuer,
testnet issuer, devnet issuer — since the whole point of the skill is that an
agent will copy these verbatim.

---

## Prompts, if you're stuck on what to write

Things worth capturing when they come up:

**Docs and discoverability**
- Was the answer findable from xrpl.org, or did you have to read source?
- Did `llms.txt` / the skill's docs indexes actually help your coding agent?
- Anything the docs assert that turned out to be version- or amendment-dependent?

**Amendments and features**
- Did you have to check `xrpl-amendments.json` to know whether something was live?
- Token escrow: were the issuer flag requirements (Allow Trust Line Locking,
  mandatory CancelAfter) clearly documented?

**x402 on XRPL**
- How was the t54 facilitator setup? Any surprises in the 402 challenge shape?
- Did the SDK behave the same server-side and client-side?
- Latency per paid call — acceptable for a real-time product?
- Reliability of the testnet facilitator over a long session

**RLUSD**
- Faucet experience, trust line setup, anything non-obvious
- Was the CLI or the agent skills repo useful?

**Agent ergonomics**
- Sequence number handling for concurrent submissions — was this documented
  anywhere obvious, or did you discover it by failing?
- Ripple epoch vs Unix time — how many people lose an hour to this?
- Wallet delegation: did OpenWallet / regular keys cover what an agent needs?

**Mainnet readiness**
- What would you need before running this on mainnet?
- Cost per transaction at scale, using real fee/reserve values
- Key management for an agent spending real money
- Compliance gaps you noticed

---

## Suggestions for the ecosystem

Bigger-picture asks. What would have made this build faster?

<!-- e.g. an agent-payments quickstart that covers sequence handling and
     epoch conversion in the first ten minutes -->
