from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class JobOut(BaseModel):
    id: UUID
    job_type: str
    status: str
    attempt_count: int
    error_code: str | None
    error_summary: str | None
    created_at: datetime
    finished_at: datetime | None

    class Config:
        from_attributes = True
