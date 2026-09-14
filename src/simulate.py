from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path

from .engine import decide_status
from .normalization import enrich_extraction


def base_case() -> dict:
    return {
        "language": "en", "customer_name": "John Smith", "phone": "+44 7700 123456", "email": "john@example.com",
        "pickup": {"date_text": "18 July", "date_iso": None, "time_text": "10:00", "location": "Kos Airport"},
        "return": {"date_text": "23 July", "date_iso": None, "time_text": None, "location": None},
        "vehicle": {"category": "small", "transmission": "automatic", "model_text": None},
        "competitor": {"price_mentioned": False, "price_text": None}, "multiple_requests": False, "ambiguities": [], "confidence": 0.97,
    }

SCENARIOS = {
    "smooth": {"missing_name": .08, "missing_phone": .18, "missing_category": .04, "low_conf": .015, "conflict": .015, "multiple": .005, "bad_phone": .02},
    "base": {"missing_name": .15, "missing_phone": .28, "missing_category": .08, "low_conf": .035, "conflict": .03, "multiple": .012, "bad_phone": .04},
    "adverse": {"missing_name": .24, "missing_phone": .38, "missing_category": .14, "low_conf": .07, "conflict": .06, "multiple": .025, "bad_phone": .08},
}


def run(seed: int = 20260913, n: int = 50000) -> dict:
    rng = random.Random(seed)
    results = {}
    for name, p in SCENARIOS.items():
        counts = Counter()
        for _ in range(n):
            x = base_case()
            if rng.random() < p["missing_name"]: x["customer_name"] = None
            if rng.random() < p["missing_phone"]: x["phone"] = None
            if rng.random() < p["missing_category"]: x["vehicle"]["category"] = None
            if rng.random() < p["low_conf"]: x["confidence"] = 0.65
            if rng.random() < p["conflict"]: x["ambiguities"].append({"code":"conflicting_dates","severity":"high","detail":"synthetic"})
            if rng.random() < p["multiple"]: x["multiple_requests"] = True
            if rng.random() < p["bad_phone"] and x["phone"] is not None: x["phone"] = "123"
            x = enrich_extraction(x)
            d = decide_status(x)
            counts[d["status"]] += 1
        automated = counts["READY"] + counts["NEEDS_INFO"]
        results[name] = {
            "n": n, "counts": dict(counts), "automated_pct": round(automated / n * 100, 3),
            "human_review_pct": round(counts["HUMAN_REVIEW"] / n * 100, 3),
        }
    return results

if __name__ == "__main__":
    data = run()
    print(json.dumps(data, indent=2, sort_keys=True))
    out = Path(__file__).resolve().parents[1] / "evidence" / "simulation_results.json"
    out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
