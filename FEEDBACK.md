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
