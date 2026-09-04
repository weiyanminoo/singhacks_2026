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
