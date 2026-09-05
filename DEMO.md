# DEMO.md — the 3-minute demo

Record at T+20. Screen recording with narration over the top. **Never live.**
Expect three takes.

Carries Creativity (20%) and UX (10%). The other 70% lives in the repo.

---

## Rules

- **Never say "travel" in the first ten seconds.** Open on the broken plan and the
  closing window. Let the viewer discover it's an airport.
- **Do not narrate the architecture.** The diagram is on screen for 5 seconds and
  lives in the README. Every second explaining the stack is stolen from the loop.
- **Do not explain the tech stack.** Nobody scores you on FastAPI.
- **Show rejections, not just selections.** A rejected option with a stated reason
  proves reasoning. A selection proves nothing.
- **Show failure.** Almost no team does. It is 20 of your most differentiated
  seconds.
- Trace panel must be legible at small size. Test scaled down.

---

## Beat sheet

| Time | On screen | Say |
|---|---|---|
| **0:00–0:18** | Title card, then the app pre-trigger | "It's 9pm and your plan just broke. So did four hundred other people's. You're all now racing for the same thirty rooms and the same handful of seats. You have about fifteen minutes before the good options are gone, and you will lose that race, because you're a tired person on a phone." |
| **0:18–0:30** | Envelope config: $10, hotel cap $6.25, max 25 min, meeting 09:00. Then architecture diagram, 5s, silent. | "In aviation, the alternate is the backup airport you nominate before you take off. alternate.ai is a budget you approve before you travel — and when something breaks, an agent spends it to fix the problem." |
| **0:30–0:50** | Cancellation fires. Trace streams. Discovery payments tick up, tx count climbing. | "It reads your constraints, then pays a couple of cents per query to check what's actually available right now — seven providers in forty seconds. A person checks two." |
| **0:50–1:10** | The search-vs-commit line. The declined 8th provider visible in the trace with its reason. | "Here it decides an eighth query isn't worth it — the best option has two rooms left and it's been searching forty seconds. That's an agent weighing information against the risk of losing the option." |
| **1:10–1:30** | **The rejection.** Aurora Grand $7.75 struck through with the reason. Then the dependency chain: flight → hotel → car. | "It rejects a hotel that meets every requirement except the price cap. Then it picks the 06:40 flight, which fixes the hotel it can choose, which fixes when the car comes." |
| **1:30–1:50** | Three purchases land. Hashes appear as clickable links. Envelope drains $10.00 → $2.96. | "Three purchases, on ledger, in about ninety seconds. Every hash is live on the explorer, and each carries the decision that caused it and the rule that permitted it." |
| **1:50–2:05** | Approval prompt on a phone. Reason shown. Tap approve. | "One option needs permission. That's the boundary — in-policy spend is autonomous, anything outside it asks." |
| **2:05–2:25** | **Failure.** Hotel sells out after payment. Funds return, agent reroutes and rebooks. | "Now watch it fail. The hotel sells out after we've paid. The money comes back, it rebooks elsewhere. No human touched that." <!-- Wording is deliberately asset- and mechanism-neutral so it holds whether the return is an EscrowCancel or the refund-Payment fallback (cut list 1). If escrow survives, say "the hold cancels, the money comes back." --> |
| **2:25–2:40** | Split screen, or a single line of text | "Take away autonomous payment and the same agent has to ask before every purchase. By the time approval comes back, the room is gone. Same agent, same data, worse outcome. The ability to act *is* the product." |
| **2:40–3:00** | Three vertical names, then the business line | "Swap the provider registry and the constraints and this runs a delivery van breakdown, a stopped production line, a cancelled venue. We sell it to travel management companies at ten dollars per traveller per month — and we take no margin on what the agent buys, because the moment we profit from its choices, nobody trusts it to spend their money." |

---

## Shot list

Capture separately, cut together:

1. Envelope configuration screen
2. Architecture diagram (still, 5s)
3. Full agent run, uncut — **the master take**
4. Phone screen with the approval prompt (film the actual phone if possible)
5. Explorer page for one purchase, showing the decoded memo
6. Failure run
7. Constrained-mode run for the counterfactual

---

## Pre-record checklist

- [ ] Reset button works, state is clean
- [ ] **Every figure in the beat sheet replaced with numbers from the actual
      recorded run** — `$2.96`, the discovery total and the
      timings above are placeholders, not targets to hit
- [ ] Full run lands under 2 minutes
- [ ] All explorer links resolve
- [ ] Trace panel legible when scaled to half size
- [ ] No API keys, seeds, or `.env` contents visible anywhere on screen
- [ ] Browser has no personal tabs, bookmarks, or notifications
- [ ] Do Not Disturb on
- [ ] 1080p minimum
- [ ] Narration read once out loud, timed

---

## If something breaks during recording

Do not debug on camera. Stop, fix, re-record from the top. A clean 2:50 beats a
3:20 with an unplanned recovery.

If a feature is genuinely broken at T+20, cut that beat and give the time to the
failure path and the closing. **Never cut the failure path.**
