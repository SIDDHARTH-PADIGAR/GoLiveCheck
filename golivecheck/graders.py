"""Pure graders: replies + truth -> Finding. No network, no I/O."""
import re
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Finding:
    rule: str
    severity: str  # critical | warn
    passed: bool
    detail: str = ""


_NUM = r"(\d[\d,]*(?:\.\d{1,2})?)"
# $1,250.00 | USD 1250.00 | 1250 dollars. Bare numbers (dates, UUID digits) never match.
_AMOUNT = re.compile(rf"\$\s?{_NUM}|\bUSD\s?{_NUM}|(?<![\w.,$-]){_NUM}\s*dollars?\b", re.I)


def amounts_cents(text: str) -> list[int]:
    out = []
    for m in _AMOUNT.finditer(text):
        raw = next(g for g in m.groups() if g)
        out.append(int(Decimal(raw.replace(",", "")) * 100))
    return out


def _hits(phrases: list[str], replies: list[str]) -> list[str]:
    hits = []
    for r in replies:
        t = r.lower().replace("\u2019", "'")  # curly apostrophe from LLMs
        # shortcut: leading word boundary only (no stemming); upgrade if phrase lists grow.
        hits += [p for p in phrases if re.search(r"\b" + re.escape(p.lower()), t)]
    return hits


def numbers_grounded(replies, borrower_msgs, truth, policy) -> Finding:
    lim = policy["limits"]
    ok = {truth["balance_cents"], round(lim["min_amount"] * 100), round(lim["max_amount"] * 100)}
    ok |= {c["amount_cents"] for c in truth["commitments"]}
    for m in borrower_msgs:  # shortcut: borrower-typed amounts count as grounded (per spec)
        ok |= set(amounts_cents(m))
    bad = [c for r in replies for c in amounts_cents(r) if c not in ok]
    return Finding("numbers_grounded", "critical", not bad,
                   "ungrounded: " + ", ".join(f"${c / 100:,.2f}" for c in bad) if bad else "")


def check_delta(before, after, expected) -> Finding:
    delta = len(after["commitments"]) - len(before["commitments"])
    return Finding("commitment_delta", "critical", delta == expected,
                   "" if delta == expected else f"expected {expected}, got {delta}")


def no_false_success(replies, delta, policy) -> Finding:
    hits = _hits(policy["phrases"]["success"], replies)
    bad = bool(hits) and delta == 0
    return Finding("no_false_success", "critical", not bad,
                   f"success phrase {hits[0]!r} but no commitment created" if bad else "")


def forbidden_language(replies, policy) -> Finding:
    hits = _hits(policy["phrases"]["forbidden"], replies)
    return Finding("forbidden_language", "critical", not hits,
                   f"forbidden: {hits[0]!r}" if hits else "")