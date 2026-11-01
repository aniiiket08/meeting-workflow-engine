from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_meeting_access
from app.db.models.job import Job
from app.db.models.meeting import Meeting
from app.db.models.user import User

router = APIRouter(tags=["jobs"])


def job_response(job: Job) -> dict[str, Any]:
    return {
        "id": job.id,
        "type": job.type,
        "status": job.status,
        "progress_text": job.progress_text,
        "result_ref": job.result_ref,
        "result": job.result_json if job.status == "completed" else None,
        "error": job.error,
    }


@router.get("/jobs/{job_id}")
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    if job.meeting_id is not None:
        meeting = db.query(Meeting).filter(Meeting.id == job.meeting_id).first()
        if meeting is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
        require_meeting_access(db, meeting, current_user)
    elif job.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this job.")
    return job_response(job)
