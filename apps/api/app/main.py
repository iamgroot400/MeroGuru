from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import assessments, credentials, goals, jobs, plans, resources
from app.core.config import cors_allowed_origins
from app.core.ratelimit import RateLimitMiddleware

app = FastAPI(title="MeroGuru API", version="0.1.0")

# This API has no authentication, so the origin allowlist is the only thing
# stopping an arbitrary page the operator visits from reading and writing their
# data. A wildcard here is not "no cross-user data to protect" -- the risk is
# cross-origin, not cross-user. Set APP_BASE_URL (and CORS_EXTRA_ORIGINS if the
# frontend is served from somewhere else) rather than widening this.
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins(),
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Content-Type"],
)
app.add_middleware(RateLimitMiddleware)

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
