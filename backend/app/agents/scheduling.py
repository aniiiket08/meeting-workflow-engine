from datetime import datetime, timedelta, timezone
from typing import Any
from dateutil.parser import parse as parse_date

from app.core.errors import ValidationFailed
from app.services.calendar_service import calendar_service
from app.services.slot_scorer import AttendeeSchedule, SlotCandidate, score_slot_candidates
from app.observability.tracer import record_tool_call, trace_agent


@trace_agent(agent_name="scheduling_agent")
def run_scheduling_agent(
    attendee_emails: list[str],
    duration_minutes: int = 60,
    target_date_iso: str | None = None,
    priority_emails: list[str] | None = None,
    meeting_id: int | None = None,
) -> list[dict[str, Any]]:
    """Standalone Scheduling Agent function.

    Generates candidate slots, evaluates free/busy schedules from the calendar service,
    and returns top 3 ranked slots with one-line editorial reasons.
    """
    if not attendee_emails:
        raise ValidationFailed("At least one attendee is required to find meeting slots.")
    if duration_minutes <= 0:
        raise ValidationFailed("Meeting duration must be greater than zero.")

    priority_set = set(priority_emails or [])

    # Target date or default to next business day at 9 AM UTC
    if target_date_iso:
        try:
            base_dt = parse_date(target_date_iso)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValidationFailed("Target date is invalid.", details={"target_date": target_date_iso}) from exc
        if base_dt.tzinfo is None:
            base_dt = base_dt.replace(tzinfo=timezone.utc)
    else:
        now = datetime.now(timezone.utc)
        base_dt = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)

    # Fetch busy schedules (integrates mock calendar + environment weekly timetable)
    busy_map = calendar_service.get_busy_slots(attendee_emails, target_date=base_dt)
    record_tool_call(
        "calendar_service.get_busy_slots",
        {"attendee_count": len(attendee_emails), "target_date": base_dt.isoformat()},
        {"busy_event_count": sum(len(events) for events in busy_map.values())},
    )
    schedules = [
        AttendeeSchedule(
            email=email,
            is_priority=(email in priority_set),
            busy_slots=busy_map.get(email, []),
            availability_known=email in busy_map,
        )
        for email in attendee_emails
    ]

    # Generate 6 candidate slots across working hours (9 AM - 5 PM)
    candidates: list[SlotCandidate] = []
    current_time = base_dt.replace(hour=9, minute=0, second=0, microsecond=0)

    for i in range(6):
        cand_start = current_time + timedelta(hours=i * 1.5)
        cand_end = cand_start + timedelta(minutes=duration_minutes)
        candidates.append(SlotCandidate(start_time=cand_start, end_time=cand_end))

    # Score candidates
    scored = score_slot_candidates(candidates, schedules)
    record_tool_call(
        "slot_scorer.score_slot_candidates",
        {"candidate_count": len(candidates), "attendee_count": len(schedules)},
        {"ranked_count": len(scored)},
    )

    # Return top 3
    top_3 = scored[:3]
    return [
        {
            "slot_index": idx + 1,
            "start_time": s.start_time.isoformat(),
            "end_time": s.end_time.isoformat(),
            "score": s.score,
            "reason": s.reason,
            "conflicts": s.conflicts,
        }
        for idx, s in enumerate(top_3)
    ]
