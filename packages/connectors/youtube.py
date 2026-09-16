"""YouTube discovery connector using the official YouTube Data API only.

Per plan.md 12.3: this connector may search and use official metadata, but must
never download arbitrary captions/audio/video. Transcript processing is limited to
content the user themselves pastes in (USER_PROVIDED_TRANSCRIPT) or content the
video's own owner has authorized (CREATOR_AUTHORIZED_TRANSCRIPT) via the official
captions.download endpoint, which requires that user's own OAuth grant. Everything
else stays METADATA_ONLY: the LLM can still build a curriculum around the title,
description, and channel, and the learner watches the embedded video directly.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from packages.connectors.base import (
    ConnectorHealth,
    ContentAccess,
    LearningSourceConnector,
    ResourceCandidate,
    SearchRequest,
    SourceContent,
)

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


class YouTubeConnector(LearningSourceConnector):
    provider = "youtube"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def search(self, request: SearchRequest) -> list[ResourceCandidate]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            search_resp = await client.get(
                SEARCH_URL,
                params={
                    "key": self.api_key,
                    "q": request.query,
                    "part": "snippet",
                    "type": "video",
                    "maxResults": request.max_results,
                    "relevanceLanguage": request.language,
                    "safeSearch": "strict",
                    "videoEmbeddable": "true",
                },
            )
            search_resp.raise_for_status()
            items = search_resp.json().get("items", [])
            video_ids = [item["id"]["videoId"] for item in items if "videoId" in item.get("id", {})]
            if not video_ids:
                return []

            details_resp = await client.get(
                VIDEOS_URL,
                params={
                    "key": self.api_key,
                    "id": ",".join(video_ids),
                    "part": "snippet,contentDetails,status",
                },
            )
            details_resp.raise_for_status()
            details = {v["id"]: v for v in details_resp.json().get("items", [])}

        candidates: list[ResourceCandidate] = []
        retrieved_at = datetime.now(timezone.utc).isoformat()
        for video_id in video_ids:
            video = details.get(video_id)
            if not video:
                continue
            snippet = video["snippet"]
            status = video.get("status", {})
            if not status.get("embeddable", True):
                continue
            candidates.append(
                ResourceCandidate(
                    provider=self.provider,
                    external_id=video_id,
                    title=snippet.get("title", ""),
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    author=snippet.get("channelTitle"),
                    content_type="video",
                    language=snippet.get("defaultAudioLanguage", request.language),
                    duration_seconds=_parse_duration(video.get("contentDetails", {}).get("duration")),
                    license_name=status.get("license", "youtube"),
                    embeddable=True,
                    content_access=ContentAccess.METADATA_ONLY,
                    retrieved_at=retrieved_at,
                    metadata={"description": snippet.get("description", "")},
                )
            )
        return candidates

    async def fetch_permitted_content(self, candidate: ResourceCandidate) -> SourceContent | None:
        # Only metadata is ever fetched automatically for YouTube. Full transcript
        # ingestion requires an explicit user-provided or creator-authorized path,
        # handled by ManualContentConnector, never here.
        return SourceContent(
            text=candidate.metadata.get("description", ""),
            permission_basis=ContentAccess.METADATA_ONLY,
        )

    async def healthcheck(self) -> ConnectorHealth:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    SEARCH_URL,
                    params={"key": self.api_key, "q": "test", "part": "id", "maxResults": 1},
                )
            if resp.status_code >= 400:
                return ConnectorHealth(ok=False, detail=f"status {resp.status_code}")
            return ConnectorHealth(ok=True)
        except httpx.HTTPError as exc:
            return ConnectorHealth(ok=False, detail=str(exc))


def _parse_duration(iso_duration: str | None) -> int | None:
    if not iso_duration:
        return None
    import re

    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration)
    if not match:
        return None
    hours, minutes, seconds = (int(g) if g else 0 for g in match.groups())
    return hours * 3600 + minutes * 60 + seconds
