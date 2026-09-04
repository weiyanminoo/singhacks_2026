# docs/

The working record of how alternate.ai was built. Raw, technical, honest.

**This is not the README.** `README.md` at the repo root is the polished
submission for judges. `docs/` is where the real detail lives — what we chose,
what broke, what we learned. The README draws from these files.

**Rule: never write a README claim that `docs/` does not support.**

---

## Index

| File | Covers |
|---|---|
| [00-decisions.md](00-decisions.md) | Running decision log. Every non-obvious choice and every cut. |
| `phase-0-setup.md` | Accounts, funding, trust lines, tooling |
| `phase-1-xrpl-foundation.md` | Payments, memos, sequence handling, epoch, fees |
| `phase-2-x402-loop.md` | 402 challenge shape, facilitator, registry, free tier |
| `phase-3-agent-decisions.md` | Scoring, dependency chain, search-vs-commit, LLM boundary |
| `phase-4-failure-and-controls.md` | Failure modes, governance model, test coverage |
| `phase-5-submission.md` | What was cut, what is simulated, known gaps |

---

## When to write

**At the end of every phase**, before starting the next one:
1. Write or update `phase-N-<name>.md`
2. Append any architectural decision to `00-decisions.md`
3. Update the mapped README sections (see the table in `CLAUDE.md`)
4. Commit: `docs: phase N — <summary>`

**Immediately, mid-phase**, when any of these happen:
- A decision contradicts `CLAUDE.md` or `PLAN.md`
- A cut-list item is executed
- A workaround is applied that would confuse a reviewer
- An XRPL or x402 behaviour surprises us (also add to `FEEDBACK.md`)

---

## Phase file template

```markdown
# Phase N — <name>

**Status:** complete / partial / cut
**Time:** T+X → T+Y
**Owner:** A / B / both

## What we built
<!-- Plain description. Files touched, what each does. -->

## How it works
<!-- The mechanism, with code snippets where they clarify. Enough that
     someone could rebuild it without reading every line. -->

## Decisions made
<!-- Anything non-obvious. Cross-reference 00-decisions.md entries. -->

## What broke, and how we fixed it
<!-- Be specific: the error, the cause, the fix, time lost.
     This feeds FEEDBACK.md. -->

## Deviations from PLAN.md
<!-- What we did differently and why. If nothing, say "none". -->

## Verification
<!-- How we know it works. Transaction hashes, test names,
     the manual check performed. -->

## Feeds README sections
<!-- Which README sections this phase filled in. -->
```

---

## Decision log entry template

```markdown
### D-00N · <title>
**Date/time:** T+X
**Context:** <the situation that forced a choice>
**Decision:** <what we chose>
**Alternatives considered:** <what we did not choose>
**Consequence:** <what this makes easier, what it makes harder>
```

---

## Style

- Write for someone who was not in the room. Ourselves in six hours counts.
- Record what actually happened, not what should have happened. A file that says
  "this took three tries because the epoch offset is not Unix time" is worth more
  than one that says "implemented escrow."
- Paste real output: transaction hashes, error messages, trace excerpts.
- Short is fine. Two honest paragraphs beat a page of narration.
- No marketing language. That belongs in the README.
