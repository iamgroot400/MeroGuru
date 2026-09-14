from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.job import BackgroundJob
from app.schemas.job import JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: UUID, db: Session = Depends(get_db)) -> BackgroundJob:
    job = db.get(BackgroundJob, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    return job
