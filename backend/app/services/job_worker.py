import base64
import logging
import threading
from typing import Any

from sqlalchemy import update
from app.db.models.job import Job
from app.db.session import SessionLocal

logger = logging.getLogger("meeting_organizer")
_worker_thread: threading.Thread | None = None
_stop = threading.Event()
_MAX_ATTEMPTS = 3


def enqueue_job(
    db: Any,
    job_type: str,
    user_id: int,
    payload: dict[str, Any],
    progress_text: str,
    meeting_id: int | None = None,
) -> Job:
    if meeting_id is not None:
        active = (
            db.query(Job)
            .filter(
                Job.meeting_id == meeting_id,
                Job.type == job_type,
                Job.status.in_(["pending", "running"]),
            )
            .order_by(Job.created_at.desc())
            .first()
        )
        if active is not None:
            return active
    job = Job(
        type=job_type,
        status="pending",
        progress_text=progress_text,
        payload_json=payload,
        user_id=user_id,
        meeting_id=meeting_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _process(job: Job, db: Any) -> dict[str, Any]:
    payload = job.payload_json or {}
    if job.type == "meeting_start":
        from app.agents.scheduling import run_scheduling_agent

        slots = run_scheduling_agent(**payload)
        return {"meeting_id": job.meeting_id, "slots": slots}

    if job.type == "meeting_confirm":
        from app.db.models.meeting import Meeting, MeetingStatus
        from app.agents.room_booking import run_room_booking_agent

        meeting = db.query(Meeting).filter(Meeting.id == job.meeting_id).first()
        if meeting is None:
            raise RuntimeError("Meeting was not found while processing confirmation.")
        if payload["is_online"]:
            from dateutil.parser import parse as parse_date
            from mcp_server.server import MCPServerSkeleton

            start_dt = parse_date(payload["selected_start_time"])
            end_dt = parse_date(payload["selected_end_time"])
            zoom = MCPServerSkeleton().call_tool(
                "zoom_create_meeting",
                {
                    "topic": meeting.title,
                    "start_time": start_dt.isoformat(),
                    "duration_minutes": max(15, int((end_dt - start_dt).total_seconds() // 60)),
                    "timezone": "UTC",
                    "idempotency_key": f"meeting_{meeting.id}_{start_dt.isoformat()}",
                },
                agent_name="scheduling_agent",
            )
            meeting.start_time = start_dt
            meeting.end_time = end_dt
            meeting.room_id = None
            meeting.zoom_meeting_id = str(zoom.get("id"))
            meeting.zoom_join_url = zoom.get("join_url")
            meeting.status = MeetingStatus.ROOM_BOOKED
            db.commit()
            return {"status": "online", "zoom": zoom}
        booking = run_room_booking_agent(
            db=db,
            meeting_id=meeting.id,
            headcount=payload["headcount"],
            start_time_iso=payload["selected_start_time"],
            end_time_iso=payload["selected_end_time"],
            equipment_needed=payload["equipment_needed"],
            room_id=payload["room_id"],
        )
        return {"room_booking": booking}

    if job.type in {"transcript_paste", "transcript_upload"}:
        from app.core.pii import redact_pii
        from app.db.models.meeting import Meeting, MeetingStatus
        from app.db.models.minutes import Transcript
        from app.services.stt import stt_service
        from app.api.routes.minutes import _minutes_response, _save_minutes_from_transcript
        from app.db.models.agenda import Decision

        meeting = db.query(Meeting).filter(Meeting.id == job.meeting_id).first()
        if meeting is None:
            raise RuntimeError("Meeting was not found while processing transcript.")
        if job.type == "transcript_paste":
            result = stt_service.process_pasted_transcript(payload["text"])
        else:
            result = stt_service.transcribe(
                base64.b64decode(payload["audio_base64"]),
                filename=payload.get("filename") or "meeting_audio.wav",
            )
        redacted = redact_pii(result["text"])
        transcript = db.query(Transcript).filter(Transcript.meeting_id == meeting.id).first()
        if transcript is None:
            transcript = Transcript(meeting_id=meeting.id)
            db.add(transcript)
        transcript.raw_text = result["text"]
        transcript.redacted_text = redacted
        transcript.language = result.get("language", "en")
        transcript.content_hash = result["hash"]
        meeting.status = MeetingStatus.TRANSCRIBED
        db.flush()
        minutes = _save_minutes_from_transcript(db, meeting, transcript, commit=False)
        decisions = db.query(Decision).filter(Decision.meeting_id == meeting.id).all()
        return {
            "status": "processed",
            "transcript_id": transcript.id,
            "redacted_text": redacted,
            "minutes": _minutes_response(minutes, transcript, decisions),
        }

    if job.type == "minutes_draft":
        from app.api.routes.minutes import _minutes_response, _save_minutes_from_transcript
        from app.db.models.agenda import Decision
        from app.db.models.meeting import Meeting
        from app.db.models.minutes import Transcript

        transcript = db.query(Transcript).filter(Transcript.meeting_id == job.meeting_id).first()
        meeting = db.query(Meeting).filter(Meeting.id == job.meeting_id).first()
        if transcript is None or meeting is None:
            raise RuntimeError("Transcript or meeting was not found while drafting minutes.")
        minutes = _save_minutes_from_transcript(db, meeting, transcript, commit=False)
        decisions = db.query(Decision).filter(Decision.meeting_id == meeting.id).all()
        return _minutes_response(minutes, transcript, decisions)

    if job.type == "agenda_generate":
        from app.api.routes.agendas import run_agenda_agent
        from app.db.models.agenda import Agenda, AgendaStatus
        from app.db.models.meeting import Meeting, MeetingStatus

        meeting = db.query(Meeting).filter(Meeting.id == job.meeting_id).first()
        if meeting is None:
            raise RuntimeError("Meeting was not found while drafting agenda.")
        agenda_model = run_agenda_agent(
            db=db, meeting_id=meeting.id, agenda_items_text=meeting.agenda_items_text or None
        )
        agenda = Agenda(
            meeting_id=meeting.id,
            items_json=[item.model_dump() for item in agenda_model.items],
            status=AgendaStatus.DRAFT,
        )
        db.add(agenda)
        meeting.status = MeetingStatus.AGENDA_DRAFTED
        db.flush()
        return {
            "id": agenda.id,
            "meeting_id": meeting.id,
            "items": agenda.items_json,
            "status": agenda.status.value,
            "approved_at": agenda.approved_at.isoformat() if agenda.approved_at else None,
            "meeting_title": meeting.title,
            "duration_minutes": meeting.duration_minutes,
            "agenda_items_text": meeting.agenda_items_text,
        }

    if job.type == "minutes_approve":
        from app.agents.follow_up import follow_up_graph
        from app.db.models.minutes import Minutes

        minutes = db.query(Minutes).filter(Minutes.id == payload["minutes_id"]).first()
        if minutes is None:
            raise RuntimeError("Approved minutes were not found.")
        return follow_up_graph.invoke(
            {"meeting_id": job.meeting_id, "action_items": minutes.action_items_json},
            config={"configurable": {"db": db}},
        )

    if job.type == "minutes_distribute":
        from app.agents.distribution import run_distribution_agent

        return run_distribution_agent(db=db, meeting_id=job.meeting_id)

    raise RuntimeError(f"Unknown job type: {job.type}")


def _run_one() -> bool:
    db = SessionLocal()
    try:
        selected = (
            db.query(Job)
            .filter(Job.status == "pending", Job.attempts < _MAX_ATTEMPTS)
            .order_by(Job.created_at.asc(), Job.id.asc())
            .first()
        )
        if selected is None:
            return False
        job_id = selected.id
        claim = db.execute(
            update(Job)
            .where(Job.id == job_id, Job.status == "pending")
            .values(
                status="running",
                progress_text={
                    "meeting_start": "Finding meeting times...",
                    "meeting_confirm": "Confirming meeting time and venue...",
                    "transcript_paste": "Extracting tasks...",
                    "transcript_upload": "Transcribing audio...",
                    "minutes_draft": "Drafting minutes...",
                    "agenda_generate": "Drafting agenda...",
                    "minutes_approve": "Creating follow-up tasks...",
                    "minutes_distribute": "Distributing approved minutes...",
                }.get(selected.type, "Working..."),
                attempts=Job.attempts + 1,
            )
        )
        if claim.rowcount != 1:
            db.rollback()
            return False
        db.commit()
        job = (
            db.query(Job)
            .filter(Job.id == job_id)
            .first()
        )
        if job is None:
            return True
        try:
            result = _process(job, db)
            job = db.query(Job).filter(Job.id == job_id).first()
            if job is None:
                return True
            job.status = "completed"
            job.progress_text = "Complete"
            job.result_json = result
            job.result_ref = f"{job.type}:{job.meeting_id or job_id}"
            job.payload_json = None
            job.error = None
            db.commit()
        except Exception as exc:
            db.rollback()
            job = db.query(Job).filter(Job.id == job_id).first()
            if job is None:
                return True
            job.error = f"{type(exc).__name__}: {exc}"
            if job.attempts >= _MAX_ATTEMPTS:
                job.status = "failed"
                job.progress_text = "Failed"
            else:
                job.status = "pending"
                job.progress_text = f"Retrying ({job.attempts}/{_MAX_ATTEMPTS})..."
            db.commit()
            logger.exception("Background job %s failed on attempt %d", job_id, job.attempts)
        return True
    finally:
        db.close()


def _worker_loop() -> None:
    while not _stop.is_set():
        try:
            if not _run_one():
                _stop.wait(0.5)
        except Exception:
            logger.exception("Background job worker iteration failed")
            _stop.wait(1)


def start_worker() -> None:
    global _worker_thread
    db = SessionLocal()
    try:
        db.query(Job).filter(Job.status == "running", Job.attempts < _MAX_ATTEMPTS).update(
            {"status": "pending", "progress_text": "Resuming after server restart..."},
            synchronize_session=False,
        )
        db.query(Job).filter(Job.status == "running", Job.attempts >= _MAX_ATTEMPTS).update(
            {
                "status": "failed",
                "progress_text": "Failed",
                "error": "Server restarted after the final retry; job did not complete.",
            },
            synchronize_session=False,
        )
        db.commit()
    finally:
        db.close()
    _stop.clear()
    _worker_thread = threading.Thread(target=_worker_loop, name="meeting-job-worker", daemon=True)
    _worker_thread.start()


def stop_worker() -> None:
    _stop.set()
    if _worker_thread and _worker_thread.is_alive():
        _worker_thread.join(timeout=2)
