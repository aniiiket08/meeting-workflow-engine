import logging
from typing import Any, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.agents.action_tracker import run_action_tracker_agent
from app.agents.distribution import run_distribution_agent
from app.agents.reminder import run_reminder_agent
from app.core.errors import ToolError
from app.db.models.action import ActionItem
from app.db.models.meeting import Meeting, MeetingStatus

logger = logging.getLogger("meeting_organizer")


class FollowUpState(TypedDict, total=False):
    meeting_id: int
    action_items: list[dict[str, Any]]
    action_ids: list[int]
    distribution: dict[str, Any]
    reminders_sent: int


def _request_db(config: RunnableConfig) -> Session:
    db = config.get("configurable", {}).get("db")
    if db is None:
        raise RuntimeError("The follow-up graph requires a database session.")
    return db


def create_approved_actions(
    state: FollowUpState, config: RunnableConfig
) -> dict[str, list[int]]:
    db = _request_db(config)
    meeting_id = state["meeting_id"]
    existing = db.query(ActionItem).filter(ActionItem.meeting_id == meeting_id).all()
    if existing:
        return {"action_ids": [item.id for item in existing]}

    actions = run_action_tracker_agent(
        db=db,
        meeting_id=meeting_id,
        extracted_actions=state.get("action_items", []),
    )
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if meeting:
        meeting.status = MeetingStatus.ACTIONS_TRACKED
        db.commit()
    return {"action_ids": [item.id for item in actions]}


def distribute_approved_minutes(
    state: FollowUpState, config: RunnableConfig
) -> dict[str, Any]:
    db = _request_db(config)
    try:
        result = run_distribution_agent(db=db, meeting_id=state["meeting_id"])
    except ToolError as exc:
        if "Email delivery is not configured" in str(exc):
            logger.info(
                "SMTP unconfigured; minutes distribution skipped for meeting_id=%s without blocking workflow",
                state["meeting_id"],
            )
            result = {"status": "skipped", "reason": "smtp_not_configured"}
        else:
            raise
    if result.get("status") in {"distributed", "skipped"}:
        meeting = db.query(Meeting).filter(Meeting.id == state["meeting_id"]).first()
        if meeting:
            meeting.status = MeetingStatus.DISTRIBUTED
            db.commit()
    return {"distribution": result}


def run_meeting_reminders(
    state: FollowUpState, config: RunnableConfig
) -> dict[str, int]:
    try:
        result = run_reminder_agent(db=_request_db(config), meeting_id=state["meeting_id"])
        return {"reminders_sent": result["reminders_sent"]}
    except ToolError as exc:
        if "Email delivery is not configured" in str(exc):
            logger.info(
                "SMTP unconfigured; reminders skipped for meeting_id=%s without blocking workflow",
                state["meeting_id"],
            )
            return {"reminders_sent": 0}
        raise


def build_follow_up_graph():
    builder = StateGraph(FollowUpState)
    builder.add_node("create_actions", create_approved_actions)
    builder.add_node("distribute_minutes", distribute_approved_minutes)
    builder.add_node("reminders", run_meeting_reminders)
    builder.set_entry_point("create_actions")
    builder.add_edge("create_actions", "distribute_minutes")
    builder.add_edge("distribute_minutes", "reminders")
    builder.add_edge("reminders", END)
    return builder.compile()


follow_up_graph = build_follow_up_graph()