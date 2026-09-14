from __future__ import annotations

import re
from typing import Any

# Deterministic guard around AI-rendered customer replies. This is intentionally
# conservative: a rejected reply goes to review rather than being auto-sent.
_INTERNAL_TOKENS = re.compile(
    r"\b(?:HUMAN_REVIEW|NEEDS_INFO|NO_CHANGE|READY|extraction confidence|system prompt|internal status|automation workflow)\b",
    re.I,
)
_PRICE_PATTERN = re.compile(
    r"(?:[€$£]\s*\d)|(?:\b\d+(?:[.,]\d{1,2})?\s*(?:€|eur|euros?|usd|gbp|pounds?|dollars?)\b)",
    re.I,
)
_CONFIRMATION_PATTERNS = [
    re.compile(r"\b(?:booking|reservation|availability)\b.{0,30}\b(?:confirmed|guaranteed|available)\b", re.I),
    re.compile(r"\b(?:buchung|reservierung|verfügbarkeit)\b.{0,30}\b(?:bestätigt|garantiert|verfügbar)\b", re.I),
    re.compile(r"\b(?:réservation|disponibilité)\b.{0,30}\b(?:confirmée?|garantie?|disponible)\b", re.I),
    re.compile(r"\b(?:prenotazione|disponibilità)\b.{0,30}\b(?:confermata|garantita|disponibile)\b", re.I),
    re.compile(r"\b(?:reserva|disponibilidad)\b.{0,30}\b(?:confirmada|garantizada|disponible)\b", re.I),
    re.compile(r"(?:κράτησ|διαθεσιμότ).{0,40}(?:επιβεβαι|διαθέσιμ|εγγυη)", re.I),
]
_VEHICLE_ASSIGNMENT = re.compile(
    r"\b(?:your car is|we have assigned|vehicle assigned|car allocated)\b|(?:το όχημά σας είναι|σας έχει ανατεθεί όχημα)",
    re.I,
)
_COMPETITOR_ATTACK = re.compile(
    r"\b(?:scam|fraud|dishonest|cheat|fake price|rip[- ]?off)\b|(?:απάτη|απατεών|κοροϊδ)",
    re.I,
)


def deterministic_reply_guard(body: str, plan: dict[str, Any] | None = None) -> dict[str, Any]:
    plan = plan or {}
    text = (body or "").strip()
    reasons: list[str] = []

    if not text:
        reasons.append("empty_reply")
    if len(text) > 2500:
        reasons.append("reply_too_long")
    if _INTERNAL_TOKENS.search(text):
        reasons.append("internal_state_exposed")
    if _PRICE_PATTERN.search(text):
        # The exercise contains a reference price, but the automation has no live
        # quote source. Exact currency values are therefore never auto-sent.
        reasons.append("unverified_numeric_price")
    if any(p.search(text) for p in _CONFIRMATION_PATTERNS):
        reasons.append("booking_or_availability_claim")
    if _VEHICLE_ASSIGNMENT.search(text):
        reasons.append("vehicle_assignment_claim")
    if _COMPETITOR_ATTACK.search(text):
        reasons.append("competitor_attack")
    if "```" in text:
        reasons.append("markdown_code_fence")

    strategy = str(plan.get("strategy") or "")
    if strategy in {"NO_REPLY", "HOLD_FOR_HUMAN"} and text:
        reasons.append("unexpected_reply_for_hold_strategy")

    return {
        "safe": not reasons,
        "reasons": reasons,
        "body": text,
    }
