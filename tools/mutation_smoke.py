from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
IGNORED_WORKSPACE_ARTIFACTS = (
    "__pycache__", "*.pyc", "evidence", ".git", ".venv", ".n8n-runtime", "*.zip",
)


def _workflow_mutator(fn: Callable[[dict], None]):
    def mutate(root: Path) -> None:
        for rel in (
            "n8n/localle_reservation_intake_v1.n8n.json",
            "n8n/Localle_Option_B_Reservation_Intake_FINAL.n8n.json",
        ):
            path = root / rel
            workflow = json.loads(path.read_text(encoding="utf-8"))
            fn(workflow)
            path.write_text(json.dumps(workflow, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return mutate


def _run_mutation(name: str, mutator: Callable[[Path], None], command: list[str]) -> dict:
    with tempfile.TemporaryDirectory(prefix="localle_mutation_") as tmp:
        target = Path(tmp) / "project"
        shutil.copytree(
            ROOT,
            target,
            ignore=shutil.ignore_patterns(*IGNORED_WORKSPACE_ARTIFACTS),
        )
        mutator(target)
        proc = subprocess.run(command, cwd=target, text=True, capture_output=True)
        detected = proc.returncode != 0
        if not detected:
            raise AssertionError(f"mutation was not detected: {name}")
        return {
            "mutation": name,
            "detected": True,
            "command": " ".join(command),
            "returncode": proc.returncode,
        }


def main() -> None:
    results: list[dict] = []

    results.append(_run_mutation(
        "workflow_active_true",
        _workflow_mutator(lambda w: w.__setitem__("active", True)),
        ["python3", "-m", "unittest", "tests.test_n8n_contract.N8nContractTests.test_safe_default_and_inactive"],
    ))

    def bad_request_key(workflow: dict) -> None:
        node = next(n for n in workflow["nodes"] if n["name"] == "UPSERT Request")
        node["parameters"]["columns"]["matchingColumns"] = ["message_id"]

    results.append(_run_mutation(
        "request_upsert_key_thread_id_to_message_id",
        _workflow_mutator(bad_request_key),
        ["python3", "-m", "unittest", "tests.test_n8n_contract.N8nContractTests.test_business_entity_and_event_matching_keys_are_locked"],
    ))

    def ambiguity_off(root: Path) -> None:
        path = root / "src" / "normalization.py"
        text = path.read_text(encoding="utf-8")
        start = text.index("def _ambiguous_numeric_date")
        boundary = text.find("\n\ndef ", start + 5)
        if boundary < 0:
            raise RuntimeError("ambiguous-date function boundary not found")
        replacement = "def _ambiguous_numeric_date(text: object, iso_value: object) -> bool:\n    return False\n"
        path.write_text(text[:start] + replacement + text[boundary:], encoding="utf-8")

    results.append(_run_mutation(
        "ambiguous_numeric_date_protection_removed",
        ambiguity_off,
        ["python3", "-m", "unittest", "tests.test_normalization.DateAmbiguityTests.test_ambiguous_pickup_numeric_date_is_flagged"],
    ))

    def greek_guard_off(root: Path) -> None:
        path = root / "src" / "reply_safety.py"
        text = path.read_text(encoding="utf-8")
        text = text.replace("(?:κράτησ|διαθεσιμότ)", "(?:NEVERMATCHGREEK|διαθεσιμότ)")
        path.write_text(text, encoding="utf-8")

    results.append(_run_mutation(
        "greek_booking_confirmation_guard_removed",
        greek_guard_off,
        ["python3", "-m", "unittest", "tests.test_reply_safety.ReplySafetyTests.test_greek_confirmation_rejected"],
    ))

    def price_guard_off(root: Path) -> None:
        path = root / "src" / "reply_safety.py"
        text = path.read_text(encoding="utf-8")
        original = 'r"(?:[€$£]\\s*\\d)|(?:\\b\\d+(?:[.,]\\d{1,2})?\\s*(?:€|eur|euros?|usd|gbp|pounds?|dollars?)\\b)"'
        if original not in text:
            raise RuntimeError("price guard literal not found")
        path.write_text(text.replace(original, 'r"(?!)"'), encoding="utf-8")

    results.append(_run_mutation(
        "numeric_price_guard_removed",
        price_guard_off,
        ["python3", "-m", "unittest", "tests.test_reply_safety.ReplySafetyTests.test_exact_price_rejected"],
    ))

    def retry_enabled(workflow: dict) -> None:
        node = next(n for n in workflow["nodes"] if n["name"] == "Reply in Same Gmail Thread")
        node["retryOnFail"] = True

    results.append(_run_mutation(
        "gmail_blind_retry_enabled",
        _workflow_mutator(retry_enabled),
        ["python3", "-m", "unittest", "tests.test_n8n_contract.N8nContractTests.test_send_failure_routes_to_human_review_not_blind_retry"],
    ))

    report = {
        "result": "PASS",
        "mutations_total": len(results),
        "mutations_detected": sum(bool(x["detected"]) for x in results),
        "mutations": results,
        "note": "Mutations are applied only in temporary copies and are never committed to release source.",
    }
    (ROOT / "evidence" / "mutation_smoke_results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
