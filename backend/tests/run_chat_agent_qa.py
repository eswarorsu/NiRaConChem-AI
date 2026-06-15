import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app import main as app_main  # noqa: E402


def assert_contains(value: str, expected: str) -> None:
    if expected.lower() not in value.lower():
        raise AssertionError(f"expected '{expected}' in '{value}'")


def main() -> int:
    app_main.get_groq_enhancement = lambda *args, **kwargs: None

    founder = app_main.chat(app_main.ChatRequest(message="Who founded NIRACONCHEM AI?"))
    assert founder.intent == "brand_identity"
    assert_contains(founder.reply, "Sravani Uppu")
    assert_contains(founder.reply, "10 years")

    broad = app_main.chat(app_main.ChatRequest(message="waterproofing"))
    assert broad.intent == "technical_consultation"
    assert broad.session_id
    assert broad.needs_clarification
    assert not broad.report_ready
    if not broad.questions:
        raise AssertionError("expected clarification questions for broad waterproofing query")

    follow_up = app_main.chat(
        app_main.ChatRequest(
            session_id=broad.session_id,
            message="It is for a Dubai basement, concrete substrate, hydrostatic water pressure.",
        )
    )
    assert follow_up.session_id == broad.session_id
    assert follow_up.intent == "technical_consultation"
    assert not follow_up.needs_clarification
    assert follow_up.report_ready
    assert follow_up.report_endpoint == "/recommend/report"
    assert follow_up.report_payload and "query" in follow_up.report_payload
    assert len(follow_up.session["messages"]) == 4
    assert follow_up.session["requirements"]["problem_requirement"] == "waterproofing"

    step_start = app_main.chat(app_main.ChatRequest(message="waterproofing"))
    step_area = app_main.chat(app_main.ChatRequest(session_id=step_start.session_id, message="roof"))
    assert step_area.intent == "technical_consultation"
    assert step_area.needs_clarification
    assert step_area.requirements["application_area"] == "roof"

    step_substrate = app_main.chat(app_main.ChatRequest(session_id=step_start.session_id, message="screed"))
    assert step_substrate.intent == "technical_consultation"
    assert step_substrate.needs_clarification
    assert step_substrate.requirements["substrate"] == "screed"

    step_exposure = app_main.chat(app_main.ChatRequest(session_id=step_start.session_id, message="uv/heat"))
    assert step_exposure.intent == "technical_consultation"
    assert step_exposure.needs_clarification
    assert step_exposure.requirements["exposure"] in {"uv", "heat"}
    if "project location" not in step_exposure.missing_requirements:
        raise AssertionError("expected only project location to remain missing before location answer")

    step_location = app_main.chat(app_main.ChatRequest(session_id=step_start.session_id, message="dubai"))
    assert step_location.intent == "technical_consultation"
    assert not step_location.needs_clarification
    assert step_location.report_ready
    assert step_location.requirements["location"] == "dubai"

    details_first = app_main.chat(
        app_main.ChatRequest(message="Dubai basement concrete hydrostatic pressure")
    )
    assert details_first.needs_clarification
    assert details_first.requirements["location"] == "dubai"
    assert details_first.requirements["application_area"] == "basement"
    spaced_requirement = app_main.chat(
        app_main.ChatRequest(session_id=details_first.session_id, message="water proofing")
    )
    assert spaced_requirement.intent == "technical_consultation"
    assert not spaced_requirement.needs_clarification
    assert spaced_requirement.report_ready
    assert spaced_requirement.requirements["problem_requirement"] == "waterproofing"

    location_first = app_main.chat(app_main.ChatRequest(message="hi"))
    location_step = app_main.chat(app_main.ChatRequest(session_id=location_first.session_id, message="dubai"))
    area_step = app_main.chat(app_main.ChatRequest(session_id=location_first.session_id, message="roof"))
    substrate_step = app_main.chat(app_main.ChatRequest(session_id=location_first.session_id, message="concrete"))
    exposure_step = app_main.chat(app_main.ChatRequest(session_id=location_first.session_id, message="uv/heat"))
    assert exposure_step.intent == "technical_consultation"
    assert exposure_step.needs_clarification
    assert exposure_step.missing_requirements == ["problem or required system"]
    assert_contains(exposure_step.reply, "One last detail")
    if "Before I recommend a system or generate the final PDF report" in exposure_step.reply:
        raise AssertionError("expected adaptive final clarification copy")
    assert location_step.requirements["location"] == "dubai"
    assert area_step.requirements["application_area"] == "roof"
    assert substrate_step.requirements["substrate"] == "concrete"

    location_final = app_main.chat(
        app_main.ChatRequest(session_id=location_first.session_id, message="water proofing")
    )
    assert not location_final.needs_clarification
    assert location_final.report_ready
    assert location_final.requirements["problem_requirement"] == "waterproofing"

    technical = app_main.chat(
        app_main.ChatRequest(
            message="basement waterproofing in Dubai for concrete with hydrostatic water pressure"
        )
    )
    assert technical.intent == "technical_consultation"
    assert not technical.needs_clarification
    assert technical.report_ready
    assert technical.recommendation
    assert technical.sources
    assert_contains(technical.reply, "Cold fluid-applied polyurethane")

    print("PASS chat founder, clarification, and technical recommendation checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
