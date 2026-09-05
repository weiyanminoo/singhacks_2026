# Phase 0 — Setup

**Status:** partial — everything done except the RLUSD balance and the
CLI-verified RLUSD payment, both blocked on a human faucet claim (see below)
**Time:** T+0
**Owner:** both

## What we built

- `scripts/setup_wallets.py` — four commands: `accounts` (generate + faucet-fund,
  idempotent), `trustlines` (RLUSD trust line on session + 8 vendors),
  `recycle` (sweep vendor RLUSD back to the session wallet), `show`.
  Seeds are written to `wallets.json`, which is gitignored.
- `.env.example` / `.env`, `requirements.txt`, root `.gitignore`.
- 10 funded testnet accounts and 9 RLUSD trust lines (hashes in
  `TRANSACTIONS.md`).

## Accounts

| Role | Address |
|---|---|
| treasury | `rQwmdaTDK2MkgjMmkcAXCAuRx3o4BpJL3j` |
| session | `r9Pwpy1iBRXFEeZdn8ix51tUJfoj2PCwD8` |
| flights_skyline | `rwqggQdGuh8iPGJiBZLsTGP4GhytVukGeR` |
| flights_aeroconnect | `rn5D1RfpZine6vuSwT6VnQkT9mmjffW6ET` |
| hotels_aurora | `r4tdKneC9ebjXYrdfpwiL9qLXZ9P9eWuqK` |
| hotels_transit_inn | `rBNwjhcoy68gs9c7JckA4mF71W4KoYAmKn` |
| hotels_meridian | `rrnffhbGZPu7wfvjXjThwxUPH6fCEcE9tu` |
| ground_swiftcar | `rJd6N2JLeQtYaaSkFU6Fpx8vAhh6CvnGLE` |
| ground_metrolink | `rMeWHgWnsqxWjztYvwxCEH3kZKfbZWfYk9` |
| data_status | `rwtGAc2QzvMkhcE1kZpiicegd1yfQj6Cky` |

Each holds 100 XRP (operational only — reserves and fees) and one RLUSD trust
line with a limit of 10,000.

## RLUSD on testnet — the exact steps

**Issuer:** `rQhWct2fv4Vc4KRjRgMrxa8xPN9Zx9iLKV`
**Currency:** `524C555344000000000000000000000000000000` (hex "RLUSD", right-padded)

The issuer address is **not** on xrpl.org or the faucet page. We found it in the
vendored official dev-portal skill at
`xrpl-dev-portal/.claude/skills/xrpl-skills/xrpl-payments/references/payments.md`
as `RLUSD_ISSUER_TESTNET`, then verified it on ledger (Domain `https://ripple.com/`,
master key disabled — consistent with a genuine Ripple-operated issuer).

**Ordering matters:** XRPL requires a trust line *before* an account can receive
an IOU (`tecNO_LINE` otherwise). So the sequence is issuer address → `TrustSet`
→ claim from faucet, not the other way round. This is why finding the issuer
independently of the faucet was on the critical path.

```bash
python scripts/setup_wallets.py accounts      # 10 accounts, faucet-funded
python scripts/setup_wallets.py trustlines    # 9 TrustSet, needs RLUSD_ISSUER in .env
# then: claim 10 RLUSD at https://tryrlusd.com/ to the SESSION address
python scripts/setup_wallets.py show
```

## Decisions made

- **D-009** — demo runs at 1/40 scale ($10 envelope) on genuine RLUSD, because
  the faucet caps at 10 RLUSD/24h.
- **D-010** — `x402-xrpl`, not `x402-secure`. Different packages.
- **D-011** — cut-list item 1 executed: RLUSD token escrow is unavailable, so the
  refundable hold becomes a vendor-initiated refund `Payment`.
- D-007 verified in practice, below.

## What broke, and how we fixed it

**The $400 envelope is unfundable.** tryrlusd.com dispenses 10 RLUSD per 24 hours
behind GitHub OAuth, with no API. We only discovered the cap by loading the page —
it is not in any docs we read first. Cost: a reopened design decision (D-009) and
~25 minutes. Fix: scale the demo 1/40 and recycle the envelope between runs, since
the vendors are our own accounts.

**A checksum-invalid address in the RLUSD skill docs.** `rlusd-skills`
`skills/rlusd-x402/SKILL.md` shows `--require-issuer rBvKgF3jSZWdJcwSsmoJspoXGpHUhBGurg`
in a copy-pasteable command. It fails base58 checksum —
`is_valid_classic_address()` returns False, the node answers `actMalformed`.
~15 minutes lost before we validated it locally rather than trusting the doc.
Both entries are in `FEEDBACK.md`.

**Token escrow is gated on an issuer flag, not just the amendment.** `TokenEscrow`
shows `enabled=true`, which reads as "available", but the issuer must also set
`lsfAllowTrustLineLocking`. Ripple's testnet RLUSD issuer does not
(`Flags = 0x819a0000`). The five-minute timebox in `CLAUDE.md` paid for itself —
this would have been discovered in Phase 3 otherwise.

**`x402-secure` is not the XRPL x402 SDK.** See D-010. Caught before installing.

## Deviations from PLAN.md

- Envelope magnitude changed from $400 to $10 (D-009). Single-asset RLUSD stands.
- Escrow removed from Phase 3 (D-011); refund-`Payment` fallback replaces it.
- `bash skills/install.sh` and the feedback-hook install were struck as already
  done. Re-running `install.sh` on Windows would replace the working junctions
  with stale copies, because MSYS `ln -s` deep-copies.
- Escrow *verification* had already moved from Phase 0 to Phase 3; D-011 now
  removes it entirely.

## Verification

- **D-007 confirmed in practice.** Live testnet via `server_info`:
  `base_fee_xrp = 1e-05`, `reserve_base_xrp = 1`, `reserve_inc_xrp = 0.2`.
  Mainnet snapshot (`xrpl-fee-settings.json`, for README Feasibility only):
  `BaseFeeDrops = 10`, `ReserveBaseDrops = 1000000`,
  `ReserveIncrementDrops = 200000`. **They agree today** — a clean data point for
  the mainnet-readiness section, and exactly the comparison D-007 was designed to
  make possible.
- 10 accounts funded, verified with `account_info`.
- 9 `TrustSet` transactions, all `tesSUCCESS`, hashes in `TRANSACTIONS.md`.
- `x402-xrpl` 0.3.2 imports cleanly on Python 3.13.1.
- x402 testnet config from the official quickstart: facilitator
  `https://xrpl-facilitator-testnet.t54.ai`, network `xrpl:1`.
- `xrpl-up` exists on npm at `0.3.0-beta.1` (run via `npx`, no `node_modules`).

**Still outstanding:** claim 10 RLUSD to the session wallet, then one
CLI-verified RLUSD payment on the explorer. Both need a human GitHub sign-in.

## Feeds README sections

*What is real and what is simulated*, *Running it*.
