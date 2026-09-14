from __future__ import annotations

from unittest.mock import MagicMock, patch

from packages.connectors.base import ContentAccess
from packages.connectors.mediawiki import MediaWikiConnector


def _fake_response(json_data: dict) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    return resp


class _FakeClient:
    def __init__(self, get_return):
        self._get_return = get_return

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, *args, **kwargs):
        return self._get_return


async def test_search_builds_openly_licensed_candidates():
    search_response = _fake_response(
        {
            "query": {
                "search": [
                    {"title": "Music theory", "snippet": "Intro to <b>music theory</b>", "pageid": 1, "timestamp": "2024-01-01T00:00:00Z"},
                ]
            }
        }
    )
    connector = MediaWikiConnector()
    with patch("httpx.AsyncClient", return_value=_FakeClient(search_response)):
        from packages.connectors.base import SearchRequest

        candidates = await connector.search(SearchRequest(query="music theory"))

    assert len(candidates) == 1
    assert candidates[0].title == "Music theory"
    assert candidates[0].content_access == ContentAccess.OPENLY_LICENSED
    assert candidates[0].license_name == "CC BY-SA 4.0"
    assert candidates[0].embeddable is False


async def test_fetch_permitted_content_returns_extract():
    from packages.connectors.base import ResourceCandidate

    connector = MediaWikiConnector()
    candidate = ResourceCandidate(
        provider="mediawiki",
        external_id="Music theory",
        title="Music theory",
        url="https://en.wikipedia.org/wiki/Music_theory",
        author="Wikipedia contributors",
        content_type="article",
        language="en",
        duration_seconds=None,
        license_name="CC BY-SA 4.0",
        embeddable=False,
        content_access=ContentAccess.OPENLY_LICENSED,
        retrieved_at="2024-01-01T00:00:00Z",
    )
    extract_response = _fake_response({"query": {"pages": [{"extract": "Music theory is the study of..."}]}})
    with patch("httpx.AsyncClient", return_value=_FakeClient(extract_response)):
        content = await connector.fetch_permitted_content(candidate)

    assert content is not None
    assert content.permission_basis == ContentAccess.OPENLY_LICENSED
    assert "Music theory" in content.text
