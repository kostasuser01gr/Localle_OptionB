from __future__ import annotations

import hashlib
from typing import Any, Callable

from .config import DEFAULT_CONFIG
from .email_normalizer import normalize_message
from .engine import build_reply_plan, decide_status, merge_extractions, request_row
from .normalization import enrich_extraction
from .reply_templates import compose_reply
from .store import SQLiteStore

Extractor = Callable[[dict[str, Any]], dict[str, Any]]


def request_id_for_thread(thread_id: str) -> str:
    return "REQ-" + hashlib.sha256(thread_id.encode("utf-8")).hexdigest()[:10].upper()


def process_message(message: dict[str, Any], extractor: Extractor, store: SQLiteStore, config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    normalized = normalize_message(message)
    mid = normalized["message_id"]
    tid = normalized["thread_id"]
    if not mid or not tid:
        raise ValueError("message_id and thread_id are required")

    with store.transaction() as conn:
        if store.message_seen(mid, conn):
            decision = decide_status({}, duplicate_message=True)
            return {"normalized": normalized, "decision": decision, "reply": "", "duplicate": True}

        if normalized["disposition"] != "PROCESS":
            decision = decide_status({}, inbound_disposition=normalized["disposition"])
            store.record_message(message_id=mid, thread_id=tid, request_id=None, result_status=decision["status"], conn=conn)
            return {"normalized": normalized, "decision": decision, "reply": "", "duplicate": False}

        extracted = extractor(normalized)
        enriched = enrich_extraction(extracted, model_map=cfg.get("vehicle_model_map") or {})
        existing = store.get_request(tid, conn)
        if existing:
            merged, conflicts = merge_extractions(existing["payload"], enriched)
            revision = int(existing["revision"]) + 1
            request_id = existing["request_id"]
        else:
            merged, conflicts = enriched, []
            revision = 1
            request_id = request_id_for_thread(tid)

        decision = decide_status(merged, minimum_confidence=float(cfg.get("minimum_confidence", 0.85)))
        plan = build_reply_plan(merged, decision, holding_reply_enabled=bool(cfg.get("human_review_holding_reply_enabled", True)))
        reply = compose_reply(plan, cfg.get("verified_business_facts") or {})
        row = request_row(request_id, tid, mid, merged, decision, plan, revision=revision)
        store.upsert_request(thread_id=tid, request_id=request_id, revision=revision, payload=merged, status=decision["status"], conn=conn)
        store.record_message(message_id=mid, thread_id=tid, request_id=request_id, result_status=decision["status"], conn=conn)
        return {
            "normalized": normalized,
            "extraction": merged,
            "conflicts": conflicts,
            "decision": decision,
            "reply_plan": plan,
            "reply": reply,
            "row": row,
            "duplicate": False,
            "send_allowed_by_logic": bool(decision.get("auto_send_allowed")) or plan.get("strategy") == "SAFE_HOLDING_REPLY",
            "send_enabled": bool(cfg.get("auto_send_enabled", False)),
        }
