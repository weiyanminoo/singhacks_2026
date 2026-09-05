"""Spending controls.

The envelope is a physical ceiling — the wallet holds exactly that much, so a
bug cannot exceed it. These checks sit *inside* that hard limit and exist to
catch the things a balance cannot: spending the whole envelope on the wrong
category, buying the same thing twice, or committing more than the user
authorised without asking.

Every refusal returns a rule name. That name goes into the transaction memo, so
the explorer shows which rule permitted a payment.
"""
from __future__ import annotations

from decimal import Decimal


class Ledger:
    """Running spend for one incident."""

    def __init__(self, caps: dict):
        self.envelope = Decimal(str(caps["envelope"]))
        self.approval_threshold = Decimal(str(caps.get("approval_threshold", self.envelope)))
        self.per_category = {k: Decimal(str(v)) for k, v in (caps.get("per_category") or {}).items()}
        self.spent = Decimal("0")
        self.by_category: dict[str, Decimal] = {}
        self.bought: set[tuple[str, str]] = set()

    @property
    def remaining(self) -> Decimal:
        return self.envelope - self.spent

    def check(self, *, amount, category: str, item_id: str) -> dict:
        """Can we buy this? Returns allowed / needs_approval / rule / reason."""
        amt = Decimal(str(amount))

        if (category, item_id) in self.bought:
            return self._no("duplicate_purchase_guard",
                            f"already bought {item_id} for this incident")

        # Category cap is checked BEFORE the envelope. When an option breaks
        # both, the category rule is the more specific and more useful thing to
        # report: "this is more than we spend on lodging" explains a policy,
        # where "we are running low" only describes a balance.
        cap = self.per_category.get(category)
        if cap is not None:
            used = self.by_category.get(category, Decimal("0"))
            if used + amt > cap:
                return self._no(f"{category}_cap",
                                f"${amt} breaks the ${cap} {category} cap")

        if amt > self.remaining:
            return self._no("envelope_cap",
                            f"${amt} exceeds ${self.remaining} remaining in the envelope")

        if amt > self.approval_threshold:
            return {"allowed": True, "needs_approval": True,
                    "rule": "approval_threshold",
                    "reason": f"${amt} is over the ${self.approval_threshold} auto-approve limit"}

        return {"allowed": True, "needs_approval": False,
                "rule": f"{category}_cap" if cap is not None else "envelope_cap",
                "reason": ""}

    def commit(self, *, amount, category: str, item_id: str) -> None:
        amt = Decimal(str(amount))
        self.spent += amt
        self.by_category[category] = self.by_category.get(category, Decimal("0")) + amt
        self.bought.add((category, item_id))

    def status(self) -> dict:
        return {
            "funded": f"{self.envelope:.2f}",
            "spent": f"{self.spent:.2f}",
            "remaining": f"{self.remaining:.2f}",
            "pct": float(self.remaining / self.envelope) if self.envelope else 0.0,
            "tx_count": len(self.bought),
        }

    @staticmethod
    def _no(rule: str, reason: str) -> dict:
        return {"allowed": False, "needs_approval": False, "rule": rule, "reason": reason}
