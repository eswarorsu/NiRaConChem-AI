import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app import main as app_main  # noqa: E402


CASES_PATH = Path(__file__).with_name("recommendation_cases.json")


def lower_join(values: object) -> str:
    if values is None:
        return ""
    if isinstance(values, dict):
        return " ".join(lower_join(value) for value in values.values())
    if isinstance(values, list):
        return " ".join(lower_join(value) for value in values)
    return str(values).lower()


def contains_any(haystack: str, needles: list[str]) -> bool:
    return any(needle.lower() in haystack for needle in needles)


def run_case(case: dict) -> tuple[bool, list[str], dict]:
    recommendation = app_main.build_recommendation(case["query"])
    profile = recommendation.selected_product_profile or {}
    products_text = lower_join(recommendation.recommended_products) + " " + lower_join(profile.get("products"))
    system_text = lower_join(recommendation.best_recommended_system)
    category = lower_join(profile.get("category"))
    categories = lower_join(profile.get("categories"))
    areas = lower_join(profile.get("application_areas"))
    supporting = lower_join(recommendation.supporting_datasheet_references)

    failures: list[str] = []
    if case.get("expected_category"):
        expected = case["expected_category"].lower()
        if expected not in category and expected not in categories:
            failures.append(f"expected category '{expected}', got category='{category}' categories='{categories}'")

    if case.get("expected_area"):
        expected = case["expected_area"].lower()
        if expected not in areas:
            failures.append(f"expected area '{expected}', got areas='{areas}'")

    if case.get("expected_system_any") and not contains_any(system_text, case["expected_system_any"]):
        failures.append(f"expected system containing any {case['expected_system_any']}, got '{recommendation.best_recommended_system}'")

    if case.get("expected_products_any") and not contains_any(products_text, case["expected_products_any"]):
        failures.append(f"expected product containing any {case['expected_products_any']}, got '{products_text}'")

    if case.get("must_not_system_any") and contains_any(system_text, case["must_not_system_any"]):
        failures.append(f"system contains forbidden value from {case['must_not_system_any']}: '{recommendation.best_recommended_system}'")

    if not recommendation.supporting_datasheet_references:
        failures.append("missing supporting datasheet references")

    summary = {
        "query": case["query"],
        "system": recommendation.best_recommended_system,
        "manufacturer": recommendation.best_manufacturer,
        "product": profile.get("product_name"),
        "category": profile.get("category"),
        "areas": profile.get("application_areas", []),
        "supporting": recommendation.supporting_datasheet_references,
    }
    return not failures, failures, summary


def main() -> int:
    app_main.get_groq_enhancement = lambda *args, **kwargs: None
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    passed = 0
    failed = 0
    for case in cases:
        ok, failures, summary = run_case(case)
        status = "PASS" if ok else "FAIL"
        print(f"{status} {case['query']}")
        print(json.dumps(summary, indent=2))
        if failures:
            for failure in failures:
                print(f"  - {failure}")
            failed += 1
        else:
            passed += 1
    print(f"\nResult: {passed} passed, {failed} failed, {len(cases)} total")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
