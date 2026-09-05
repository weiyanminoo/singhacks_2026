"""Load and validate contingency playbooks.

Nothing here knows what a flight is. A template describes steps that need
resources of some category, which steps depend on which, and what must hold.
The words "transport", "lodging" and so on are data, not code (D-015).
"""
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
VERTICALS = ROOT / "verticals"

# A playbook has either top-level `steps` (single recovery path) or `plans`
# (competing recovery paths, each with its own steps). Both shapes are valid.
REQUIRED = ("id", "name", "triggers", "discovery", "caps", "scoring")


class TemplateError(ValueError):
    """A playbook is malformed. Fail loudly — a silent bad template is worse."""


def load(vertical: str) -> dict:
    path = VERTICALS / vertical / "template.yaml"
    if not path.exists():
        raise TemplateError(f"no template at {path}")
    tpl = yaml.safe_load(path.read_text(encoding="utf-8"))
    validate(tpl)
    return tpl


def available() -> list[str]:
    return sorted(p.name for p in VERTICALS.iterdir() if (p / "template.yaml").exists())


def validate(tpl: dict) -> None:
    missing = [k for k in REQUIRED if k not in tpl]
    if missing:
        raise TemplateError(f"template missing keys: {', '.join(missing)}")

    if "steps" not in tpl and "plans" not in tpl:
        raise TemplateError("template needs either 'steps' or 'plans'")

    if "plans" in tpl:
        pids = [p["id"] for p in tpl["plans"]]
        if len(pids) != len(set(pids)):
            raise TemplateError("duplicate plan ids")
        if not any(p.get("steps") for p in tpl["plans"]):
            raise TemplateError("at least one plan must have steps to execute")
        for plan in tpl["plans"]:
            _validate_steps(plan.get("steps", []), where=f"plan '{plan['id']}'")

    _validate_steps(tpl.get("steps", []), where="template")

    caps = tpl["caps"]
    if "envelope" not in caps:
        raise TemplateError("caps.envelope is required — it is the spending ceiling")


def _validate_steps(steps: list[dict], *, where: str) -> None:
    ids = [s["id"] for s in steps]
    if len(ids) != len(set(ids)):
        raise TemplateError(f"duplicate step ids in {where}")
    seen: set[str] = set()
    for step in steps:
        for key in ("id", "category"):
            if key not in step:
                raise TemplateError(f"{where}: step {step.get('id', '?')} missing '{key}'")
        for dep in step.get("depends_on", []):
            if dep not in seen:
                raise TemplateError(
                    f"{where}: step '{step['id']}' depends on '{dep}', which is not "
                    "defined before it — steps are executed in order"
                )
        seen.add(step["id"])


def matches(tpl: dict, event: dict) -> bool:
    """Does this playbook apply to this event?

    A trigger matches on event type, optionally narrowed by a `when` expression
    over the event payload.
    """
    for trig in tpl["triggers"]:
        if trig.get("event_type") != event.get("type"):
            continue
        cond = trig.get("when")
        if not cond:
            return True
        if _evaluate(cond, event):
            return True
    return False


_COND = re.compile(r"^payload\.(\w+)\s*(>=|<=|==|>|<)\s*(-?\d+(?:\.\d+)?)$")


def _evaluate(cond: str, event: dict) -> bool:
    """Tiny comparison evaluator: `payload.field >= number`.

    Deliberately not eval(). A template is data; data must not execute.
    """
    m = _COND.match(cond.strip())
    if not m:
        raise TemplateError(f"unsupported trigger condition: {cond!r}")
    field, op, target = m.group(1), m.group(2), float(m.group(3))
    actual = event.get("payload", {}).get(field)
    if actual is None:
        return False
    a, t = float(actual), target
    return {">=": a >= t, "<=": a <= t, "==": a == t, ">": a > t, "<": a < t}[op]


def resolve(text: str, ctx: dict) -> str:
    """Fill `{profile.constraints.arrive_by}` style slots from a context dict."""
    def sub(m):
        cur = ctx
        for part in m.group(1).split("."):
            if not isinstance(cur, dict) or part not in cur:
                return m.group(0)          # leave unresolved slots visible
            cur = cur[part]
        return str(cur)
    return re.sub(r"\{([\w.]+)\}", sub, text or "")
