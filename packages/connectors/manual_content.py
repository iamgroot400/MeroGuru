"""Manual URL and user-provided text/transcript ingestion.

This is the primary legitimate path for turning a video into a curriculum:
the learner pastes a transcript they already have rights to (their own notes,
a transcript the creator shared, or one they copied from YouTube's own
auto-caption viewer for personal study use), and it is recorded with an
explicit permission basis rather than silently treated as freely reusable.
"""
from __future__ import annotations

from datetime import datetime, timezone

from packages.connectors.base import (
    ConnectorHealth,
    ContentAccess,
    LearningSourceConnector,
    ResourceCandidate,
    SearchRequest,
    SourceContent,
)


class ManualContentConnector(LearningSourceConnector):
    provider = "manual"

    async def search(self, request: SearchRequest) -> list[ResourceCandidate]:
        return []

    def build_candidate(
        self, url: str, title: str, content_access: ContentAccess
    ) -> ResourceCandidate:
        return ResourceCandidate(
            provider=self.provider,
            external_id=url,
            title=title,
            url=url,
            author=None,
            content_type="article" if content_access != ContentAccess.USER_PROVIDED_TRANSCRIPT else "transcript",
            language="en",
            duration_seconds=None,
            license_name=None,
            embeddable=False,
            content_access=content_access,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
        )

    async def fetch_permitted_content(self, candidate: ResourceCandidate) -> SourceContent | None:
        text = candidate.metadata.get("text")
        if not text:
            return None
        return SourceContent(text=text, permission_basis=candidate.content_access)

    async def healthcheck(self) -> ConnectorHealth:
        return ConnectorHealth(ok=True)
