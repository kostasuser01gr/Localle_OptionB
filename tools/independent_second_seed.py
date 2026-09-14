from __future__ import annotations

import json
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.engine import build_reply_plan, decide_status
from src.simulate import run as simulation_run
from tests.test_parity import random_case
from tools import stress_scenarios as stress

SEED = 20261031


def main() -> None:
    probability = simulation_run(seed=SEED, n=50_000)

    stress.SEED = SEED
    multi_turn = stress.multiturm_invariants(40_000)
    reply_safety = stress.reply_safety_fuzz(30_000)
    decision_fuzz = stress.random_decision_invariants(100_000)

    rng = random.Random(SEED)
    rows = [random_case(rng) for _ in range(10_000)]
    proc = subprocess.run(
        ["node", str(ROOT / "tests" / "js_runner.js")],
        input=json.dumps(rows),
        text=True,
        capture_output=True,
        check=True,
    )
    js = json.loads(proc.stdout)
    for i, (row, js_result) in enumerate(zip(rows, js)):
        decision = decide_status(
            row["extraction"],
            minimum_confidence=row["minimum_confidence"],
            duplicate_message=row["duplicate_message"],
            inbound_disposition=row["inbound_disposition"],
        )
        reply = build_reply_plan(
            row["extraction"], decision,
            holding_reply_enabled=row["holding_reply_enabled"],
        )
        if decision != js_result["decision"] or reply != js_result["reply"]:
            raise AssertionError(f"second-seed parity mismatch at case {i}")

    report = {
        "result": "PASS",
        "seed": SEED,
        "python_js_parity": {"cases": 10_000, "result": "PASS"},
        "multi_turn": multi_turn,
        "reply_safety": reply_safety,
        "decision_fuzz": decision_fuzz,
        "probability": probability,
        "synthetic_note": "Second independent random-seed run; probability rates are synthetic, not observed production metrics.",
    }
    (ROOT / "evidence" / "independent_second_seed_validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
