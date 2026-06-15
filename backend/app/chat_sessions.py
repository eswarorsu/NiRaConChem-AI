from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

MAX_SESSION_MESSAGES = 40

_sessions: dict[str, dict] = {}


def new_session_id() -> str:
    return uuid4().hex


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_or_create_session(session_id: str | None = None) -> dict:
    key = session_id or new_session_id()
    if key not in _sessions:
        _sessions[key] = {
            "session_id": key,
            "messages": [],
            "requirements": {},
            "missing_requirements": [],
            "latest_recommendation": None,
            "report_ready": False,
            "report_payload": None,
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
    return _sessions[key]


def session_history(session: dict) -> list[dict[str, str]]:
    return [
        {"role": message["role"], "content": message["content"]}
        for message in session.get("messages", [])
        if message.get("role") in {"user", "assistant"} and message.get("content")
    ]


def append_message(session: dict, role: str, content: str) -> None:
    session.setdefault("messages", []).append(
        {
            "role": role,
            "content": content,
            "created_at": utc_now(),
        }
    )
    session["messages"] = session["messages"][-MAX_SESSION_MESSAGES:]
    session["updated_at"] = utc_now()


def update_session_from_chat_result(session: dict, result: dict) -> None:
    session["requirements"] = result.get("requirements") or {}
    session["missing_requirements"] = result.get("missing_requirements") or []
    session["latest_recommendation"] = result.get("recommendation")
    session["report_ready"] = bool(result.get("report_ready"))
    session["report_payload"] = result.get("report_payload")
    session["updated_at"] = utc_now()


def session_snapshot(session: dict) -> dict:
    return deepcopy(
        {
            "session_id": session["session_id"],
            "messages": session.get("messages", []),
            "requirements": session.get("requirements", {}),
            "missing_requirements": session.get("missing_requirements", []),
            "latest_recommendation": session.get("latest_recommendation"),
            "report_ready": session.get("report_ready", False),
            "report_payload": session.get("report_payload"),
            "created_at": session.get("created_at"),
            "updated_at": session.get("updated_at"),
        }
    )
