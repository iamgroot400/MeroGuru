from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import assessments, credentials, goals, jobs, plans, resources

app = FastAPI(title="MeroGuru API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # single-user, locally self-hosted app: no cross-user data to protect
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(goals.router, prefix="/api/v1")
app.include_router(credentials.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(plans.router, prefix="/api/v1")
app.include_router(assessments.router, prefix="/api/v1")
app.include_router(resources.router, prefix="/api/v1")


@app.get("/health/live")
def health_live() -> dict:
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready() -> dict:
    from sqlalchemy import text

    from app.db.session import SessionLocal

    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "ok"}
    except Exception as exc:  # readiness must fail loudly, not 500 silently
        return {"status": "degraded", "detail": str(exc)}
