"""Wikipedia / MediaWiki connector using the official Action API.

Content is openly licensed (CC BY-SA), so unlike YouTube this connector may fetch
and process full article text, not just metadata. Attribution (title, URL, revision,
retrieval time) is always retained on the resulting resource.
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

CC_BY_SA = "CC BY-SA 4.0"


class MediaWikiConnector(LearningSourceConnector):
    provider = "mediawiki"

    def __init__(self, api_base: str = "https://en.wikipedia.org/w/api.php") -> None:
        self.api_base = api_base

    async def search(self, request: SearchRequest) -> list[ResourceCandidate]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                self.api_base,
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": request.query,
                    "srlimit": request.max_results,
                    "format": "json",
                    "formatversion": "2",
                },
            )
            resp.raise_for_status()
            results = resp.json().get("query", {}).get("search", [])

        retrieved_at = datetime.now(timezone.utc).isoformat()
        candidates = []
        for item in results:
            title = item["title"]
            candidates.append(
                ResourceCandidate(
                    provider=self.provider,
                    external_id=title,
                    title=title,
                    url=f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                    author="Wikipedia contributors",
                    content_type="article",
                    language=request.language,
                    duration_seconds=None,
                    license_name=CC_BY_SA,
                    embeddable=False,
                    content_access=ContentAccess.OPENLY_LICENSED,
                    retrieved_at=retrieved_at,
                    metadata={
                        "snippet": item.get("snippet", ""),
                        "pageid": item.get("pageid"),
                        "revision_timestamp": item.get("timestamp"),
                    },
                )
            )
        return candidates

    async def fetch_permitted_content(self, candidate: ResourceCandidate) -> SourceContent | None:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                self.api_base,
                params={
                    "action": "query",
                    "prop": "extracts",
                    "explaintext": 1,
                    "titles": candidate.external_id,
                    "format": "json",
                    "formatversion": "2",
                },
            )
            resp.raise_for_status()
            pages = resp.json().get("query", {}).get("pages", [])
        if not pages or "extract" not in pages[0]:
            return None
        return SourceContent(text=pages[0]["extract"], permission_basis=ContentAccess.OPENLY_LICENSED)

    async def healthcheck(self) -> ConnectorHealth:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    self.api_base,
                    params={"action": "query", "meta": "siteinfo", "format": "json"},
                )
            if resp.status_code >= 400:
                return ConnectorHealth(ok=False, detail=f"status {resp.status_code}")
            return ConnectorHealth(ok=True)
        except httpx.HTTPError as exc:
            return ConnectorHealth(ok=False, detail=str(exc))
