from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

CATEGORY_ALIASES = {
    "MINI": {"mini", "fiat panda", "panda", "city car", "kleinwagen", "citadine", "utilitaria", "μικρό"},
    "ECONOMY": {"economy", "small", "small car", "économique", "economica", "económico", "οικονομικό"},
    "COMPACT": {"compact", "compact car", "kompakt", "compacte", "compatto", "συμπαγές"},
    "SUV": {"suv", "crossover", "4x4"},
    "SEVEN_SEATER": {"7 seater", "7-seater", "seven seater", "7 posti", "7 places", "7 sitzer", "7θέσιο", "7 θεσιο"},
    "VAN": {"van", "minivan", "people carrier", "monovolume"},
    "CONVERTIBLE": {"convertible", "cabrio", "cabriolet", "decapotable"},
    "PREMIUM": {"premium", "luxury", "executive", "luxe", "lusso"},
}


def normalize_phone(raw: Any) -> dict[str, Any]:
    if raw is None or not str(raw).strip():
        return {"raw": None, "normalized": None, "status": "missing"}
    value = str(raw).strip()
    ext_removed = re.split(r"(?:ext\.?|extension|x)\s*\d+", value, flags=re.I)[0]
    compact = re.sub(r"[^\d+]", "", ext_removed)
    if compact.startswith("00"):
        compact = "+" + compact[2:]
    plus_count = compact.count("+")
    digits = re.sub(r"\D", "", compact)
    if plus_count > 1 or ("+" in compact and not compact.startswith("+")):
        return {"raw": value, "normalized": compact, "status": "invalid_format"}
    if not (8 <= len(digits) <= 15):
        return {"raw": value, "normalized": compact or None, "status": "invalid_length"}
    normalized = ("+" + digits) if compact.startswith("+") else digits
    return {"raw": value, "normalized": normalized, "status": "plausible"}


def normalize_vehicle(extraction: dict[str, Any], model_map: dict[str, str] | None = None) -> dict[str, Any]:
    vehicle = deepcopy(extraction.get("vehicle") or {})
    raw = str(vehicle.get("category") or "").strip()
    model = str(vehicle.get("model_text") or "").strip()
    normalized = None
    evidence = ""
    folded = raw.casefold()
    if folded:
        for category, aliases in CATEGORY_ALIASES.items():
            if folded in {x.casefold() for x in aliases}:
                normalized = category
                evidence = "category_alias"
                break
    if not normalized and model and model_map:
        mapped = model_map.get(model.casefold())
        if mapped:
            normalized = mapped
            evidence = "verified_model_map"
    vehicle["category_normalized"] = normalized
    vehicle["normalization_evidence"] = evidence or None
    return vehicle


def _ambiguous_numeric_date(text: Any, iso_value: Any) -> bool:
    if iso_value or not isinstance(text, str):
        return False
    # 03/04 or 03.04 is ambiguous when both first components can be month/day.
    m = re.search(r"(?<!\d)(\d{1,2})[\/.](\d{1,2})(?!\d)", text.strip())
    if not m:
        return False
    a, b = int(m.group(1)), int(m.group(2))
    return 1 <= a <= 12 and 1 <= b <= 12 and a != b


def enrich_extraction(extraction: dict[str, Any], *, model_map: dict[str, str] | None = None) -> dict[str, Any]:
    enriched = deepcopy(extraction)
    phone = normalize_phone(enriched.get("phone"))
    enriched["phone_raw"] = phone["raw"]
    enriched["phone_normalized"] = phone["normalized"]
    enriched["phone_status"] = phone["status"]
    enriched["vehicle"] = normalize_vehicle(enriched, model_map=model_map)
    ambiguities = list(enriched.get("ambiguities") or [])
    if phone["status"].startswith("invalid"):
        ambiguities.append({
            "code": "invalid_phone_format",
            "severity": "medium",
            "detail": f"Phone was present but failed plausibility validation: {phone['status']}",
        })
    for side in ("pickup", "return"):
        block = enriched.get(side) or {}
        if _ambiguous_numeric_date(block.get("date_text"), block.get("date_iso")):
            ambiguities.append({
                "code": f"ambiguous_{side}_numeric_date",
                "severity": "medium",
                "detail": f"{side.title()} date is numerically ambiguous and has no safe ISO resolution",
            })
    enriched["ambiguities"] = ambiguities
    return enriched
