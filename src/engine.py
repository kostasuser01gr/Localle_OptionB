from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Any

REQUIRED_FIELDS = (
    "customer_name",
    "phone",
    "pickup.date_text",
    "return.date_text",
    "vehicle.category",
)

HIGH_RISK_AMBIGUITIES = {
    "return_before_pickup",
    "conflicting_dates",
    "conflicting_customer_identity",
    "conflicting_phone",
    "multiple_requests_in_one_message",
    "conflicting_customer_name",
    "conflicting_pickup_date_text",
    "conflicting_return_date_text",
    "conflicting_vehicle_category",
}

MEDIUM_RISK_REQUIRING_INFO = {
    "invalid_phone_format",
    "ambiguous_numeric_date",
    "ambiguous_pickup_numeric_date",
    "ambiguous_return_numeric_date",
}

NEUTRAL_VALUES = {
    "vehicle.transmission": {"unspecified", "unknown", "not specified"},
}

# Fields a customer can naturally correct in a follow-up. Identity changes remain review-only.
CORRECTABLE_FIELDS = {
    "phone",
    "email",
    "pickup.date_text",
    "pickup.date_iso",
    "pickup.time_text",
    "pickup.location",
    "return.date_text",
    "return.date_iso",
    "return.time_text",
    "return.location",
    "vehicle.category",
    "vehicle.category_normalized",
    "vehicle.transmission",
    "vehicle.model_text",
    "competitor.price_text",
}

ALWAYS_MUTABLE_FIELDS = {"language"}


def get_path(obj: dict[str, Any], path: str) -> Any:
    cur: Any = obj
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def set_path(obj: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    cur = obj
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = value


def present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def equivalent(path: str, old: Any, new: Any) -> bool:
    if isinstance(old, str) and isinstance(new, str):
        return old.strip().casefold() == new.strip().casefold()
    return old == new


def neutral(path: str, value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return value.strip().casefold() in NEUTRAL_VALUES.get(path, set())


def missing_required(extraction: dict[str, Any]) -> list[str]:
    missing = [path for path in REQUIRED_FIELDS if not present(get_path(extraction, path))]
    if present(extraction.get("phone")) and str(extraction.get("phone_status") or "").startswith("invalid"):
        if "phone" not in missing:
            missing.append("phone")
    return missing


def _iso_date(value: Any) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def contradiction_reasons(extraction: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    pickup_iso = _iso_date(get_path(extraction, "pickup.date_iso"))
    return_iso = _iso_date(get_path(extraction, "return.date_iso"))
    if pickup_iso and return_iso and return_iso < pickup_iso:
        reasons.append("return_before_pickup")
    if extraction.get("multiple_requests"):
        reasons.append("multiple_requests_in_one_message")
    for ambiguity in extraction.get("ambiguities") or []:
        if not isinstance(ambiguity, dict):
            continue
        code = str(ambiguity.get("code") or "")
        severity = str(ambiguity.get("severity") or "")
        if severity == "high" or code in HIGH_RISK_AMBIGUITIES:
            if code and code not in reasons:
                reasons.append(code)
    return reasons


def decision_reasons(extraction: dict[str, Any], minimum_confidence: float) -> tuple[list[str], list[str]]:
    review = contradiction_reasons(extraction)
    if float(extraction.get("confidence") or 0.0) < minimum_confidence:
        review.append("low_extraction_confidence")
    info: list[str] = []
    for ambiguity in extraction.get("ambiguities") or []:
        if not isinstance(ambiguity, dict):
            continue
        code = str(ambiguity.get("code") or "")
        if code in MEDIUM_RISK_REQUIRING_INFO and code not in info:
            info.append(code)
    return list(dict.fromkeys(review)), info


def decide_status(
    extraction: dict[str, Any],
    *,
    minimum_confidence: float = 0.85,
    duplicate_message: bool = False,
    inbound_disposition: str = "PROCESS",
) -> dict[str, Any]:
    if inbound_disposition != "PROCESS":
        return {
            "status": "NO_CHANGE",
            "missing_fields": [],
            "human_review_reason": inbound_disposition.lower(),
            "next_action": "ignore_non_customer_event",
            "auto_send_allowed": False,
        }
    if duplicate_message:
        return {
            "status": "NO_CHANGE",
            "missing_fields": [],
            "human_review_reason": "duplicate_message_id",
            "next_action": "ignore_duplicate_event",
            "auto_send_allowed": False,
        }

    review_reasons, info_reasons = decision_reasons(extraction, minimum_confidence)
    if review_reasons:
        return {
            "status": "HUMAN_REVIEW",
            "missing_fields": missing_required(extraction),
            "human_review_reason": ",".join(review_reasons),
            "next_action": "human_review_before_commitment",
            "auto_send_allowed": False,
        }

    missing = missing_required(extraction)
    if "invalid_phone_format" in info_reasons and "phone" not in missing:
        missing.append("phone")
    if "ambiguous_pickup_numeric_date" in info_reasons and "pickup.date_text" not in missing:
        missing.append("pickup.date_text")
    if "ambiguous_return_numeric_date" in info_reasons and "return.date_text" not in missing:
        missing.append("return.date_text")
    if "ambiguous_numeric_date" in info_reasons:
        for field in ("pickup.date_text", "return.date_text"):
            if field not in missing:
                missing.append(field)

    if missing:
        return {
            "status": "NEEDS_INFO",
            "missing_fields": missing,
            "human_review_reason": "",
            "next_action": "ask_only_missing_required_fields",
            "auto_send_allowed": True,
        }

    return {
        "status": "READY",
        "missing_fields": [],
        "human_review_reason": "",
        "next_action": "continue_to_availability_or_quote_step",
        "auto_send_allowed": True,
    }


def _ambiguity_resolved_by_incoming(code: str, incoming: dict[str, Any]) -> bool:
    incoming_codes = {
        str(a.get("code") or "")
        for a in (incoming.get("ambiguities") or [])
        if isinstance(a, dict)
    }
    if code in incoming_codes:
        return False
    if code == "invalid_phone_format":
        return present(incoming.get("phone")) and not str(incoming.get("phone_status") or "").startswith("invalid")
    if code == "ambiguous_pickup_numeric_date":
        return present(get_path(incoming, "pickup.date_text")) or present(get_path(incoming, "pickup.date_iso"))
    if code == "ambiguous_return_numeric_date":
        return present(get_path(incoming, "return.date_text")) or present(get_path(incoming, "return.date_iso"))
    if code == "ambiguous_numeric_date":
        return (
            present(get_path(incoming, "pickup.date_text"))
            and present(get_path(incoming, "return.date_text"))
        )
    return False


def _dedupe_ambiguities(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "")
        detail = str(item.get("detail") or "")
        key = (code, detail)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def merge_extractions(existing: dict[str, Any], incoming: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Merge one new message into a request conversation.

    Safety properties:
    - neutral/unspecified values never erase known facts;
    - explicit correction messages may replace operational fields;
    - customer identity changes remain conflicts;
    - unresolved ambiguities survive later unrelated follow-ups;
    - confidence is conservative across a conversation (minimum of observed messages).
    """
    merged = deepcopy(existing)
    conflicts: list[str] = []
    corrections: list[str] = list(existing.get("_applied_corrections") or [])
    intent = str(incoming.get("message_intent") or "").casefold()
    is_correction = intent == "correction"

    paths = [
        "customer_name", "phone", "email", "language",
        "pickup.date_text", "pickup.date_iso", "pickup.time_text", "pickup.location",
        "return.date_text", "return.date_iso", "return.time_text", "return.location",
        "vehicle.category", "vehicle.category_normalized", "vehicle.transmission", "vehicle.model_text",
        "competitor.price_text",
    ]

    for path in paths:
        old = get_path(merged, path)
        new = get_path(incoming, path)
        if neutral(path, new) or not present(new):
            continue
        if path in ALWAYS_MUTABLE_FIELDS:
            set_path(merged, path, new)
            continue
        if neutral(path, old) or not present(old):
            set_path(merged, path, new)
            continue
        if equivalent(path, old, new):
            continue
        if is_correction and path in CORRECTABLE_FIELDS:
            set_path(merged, path, new)
            corrections.append(path)
        else:
            conflicts.append(path)

    merged["_applied_corrections"] = list(dict.fromkeys(corrections))
    merged["message_intent"] = incoming.get("message_intent") or existing.get("message_intent") or "follow_up"
    merged["multiple_requests"] = bool(existing.get("multiple_requests")) or bool(incoming.get("multiple_requests"))
    merged.setdefault("competitor", {})["price_mentioned"] = (
        bool(get_path(existing, "competitor.price_mentioned"))
        or bool(get_path(incoming, "competitor.price_mentioned"))
    )

    old_conf = float(existing.get("confidence") or 0.0)
    new_conf = float(incoming.get("confidence") or 0.0)
    if old_conf and new_conf:
        merged["confidence"] = min(old_conf, new_conf)
    else:
        merged["confidence"] = new_conf or old_conf

    # Phone derived fields only change when a phone fact is actually supplied.
    if present(incoming.get("phone")):
        merged["phone_raw"] = incoming.get("phone_raw")
        merged["phone_normalized"] = incoming.get("phone_normalized")
        merged["phone_status"] = incoming.get("phone_status")
    else:
        merged["phone_raw"] = existing.get("phone_raw")
        merged["phone_normalized"] = existing.get("phone_normalized")
        merged["phone_status"] = existing.get("phone_status")

    carried: list[dict[str, Any]] = []
    for ambiguity in existing.get("ambiguities") or []:
        if not isinstance(ambiguity, dict):
            continue
        code = str(ambiguity.get("code") or "")
        if not _ambiguity_resolved_by_incoming(code, incoming):
            carried.append(deepcopy(ambiguity))

    newest = [deepcopy(a) for a in (incoming.get("ambiguities") or []) if isinstance(a, dict)]
    merged["ambiguities"] = carried + newest
    for path in conflicts:
        merged["ambiguities"].append({
            "code": f"conflicting_{path.replace('.', '_')}",
            "severity": "high",
            "detail": f"Existing and follow-up values differ for {path}",
        })
    merged["ambiguities"] = _dedupe_ambiguities(merged["ambiguities"])
    return merged, conflicts


def build_reply_plan(extraction: dict[str, Any], decision: dict[str, Any], *, holding_reply_enabled: bool = True) -> dict[str, Any]:
    status = decision["status"]
    competitor = bool(get_path(extraction, "competitor.price_mentioned"))
    if status == "NO_CHANGE":
        strategy = "NO_REPLY"
    elif status == "HUMAN_REVIEW":
        strategy = "SAFE_HOLDING_REPLY" if holding_reply_enabled else "HOLD_FOR_HUMAN"
    elif status == "NEEDS_INFO":
        strategy = "ACKNOWLEDGE_CONFIRM_ASK_ONLY_MISSING"
    else:
        strategy = "ACKNOWLEDGE_CONFIRM_VALUE_AND_NEXT_STEP"
    return {
        "language": extraction.get("language") or "en",
        "strategy": strategy,
        "missing_fields": decision.get("missing_fields") or [],
        "confirmed": {
            "customer_name": extraction.get("customer_name"),
            "pickup_date": get_path(extraction, "pickup.date_text"),
            "return_date": get_path(extraction, "return.date_text"),
            "pickup_time": get_path(extraction, "pickup.time_text"),
            "pickup_location": get_path(extraction, "pickup.location"),
            "return_location": get_path(extraction, "return.location"),
            "vehicle_category": get_path(extraction, "vehicle.category"),
            "transmission": get_path(extraction, "vehicle.transmission"),
        },
        "include_total_cost_comparison": competitor and status in {"READY", "NEEDS_INFO"},
        "forbidden_claims": [
            "availability_confirmed",
            "booking_confirmed",
            "exact_quote_without_source",
            "vehicle_assignment",
        ],
        "must_not_attack_competitor": True,
    }


def request_row(request_id: str, thread_id: str, message_id: str, extraction: dict[str, Any], decision: dict[str, Any], reply_plan: dict[str, Any], revision: int = 1) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "thread_id": thread_id,
        "last_message_id": message_id,
        "revision": revision,
        "customer_name": extraction.get("customer_name"),
        "email": extraction.get("email"),
        "phone_raw": extraction.get("phone_raw") or extraction.get("phone"),
        "phone_normalized": extraction.get("phone_normalized"),
        "phone_status": extraction.get("phone_status"),
        "language": extraction.get("language"),
        "pickup_date_text": get_path(extraction, "pickup.date_text"),
        "pickup_date_iso": get_path(extraction, "pickup.date_iso"),
        "pickup_time": get_path(extraction, "pickup.time_text"),
        "pickup_location": get_path(extraction, "pickup.location"),
        "return_date_text": get_path(extraction, "return.date_text"),
        "return_date_iso": get_path(extraction, "return.date_iso"),
        "return_time": get_path(extraction, "return.time_text"),
        "return_location": get_path(extraction, "return.location"),
        "vehicle_category_raw": get_path(extraction, "vehicle.category"),
        "vehicle_category_normalized": get_path(extraction, "vehicle.category_normalized"),
        "transmission": get_path(extraction, "vehicle.transmission"),
        "model_text": get_path(extraction, "vehicle.model_text"),
        "competitor_price_mentioned": bool(get_path(extraction, "competitor.price_mentioned")),
        "competitor_price_text": get_path(extraction, "competitor.price_text"),
        "missing_fields": ",".join(decision.get("missing_fields") or []),
        "status": decision["status"],
        "human_review_reason": decision.get("human_review_reason") or "",
        "extraction_confidence": extraction.get("confidence"),
        "reply_language": reply_plan.get("language") or "en",
        "reply_strategy": reply_plan.get("strategy") or "",
        "next_action": decision.get("next_action") or "",
    }
