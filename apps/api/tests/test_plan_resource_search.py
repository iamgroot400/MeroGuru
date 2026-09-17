import asyncio
from types import SimpleNamespace

from app.services.plan_service import _search_lesson_resources


def test_searches_overlap_and_preserve_results():
    async def run():
        started = set()
        both_started = asyncio.Event()
        def connector(name):
            async def search(request):
                started.add(name)
                if len(started) == 2:
                    both_started.set()
                await asyncio.wait_for(both_started.wait(), timeout=1)
                return [name]
            return SimpleNamespace(provider=name, search=search)
        return await _search_lesson_resources(connector("youtube"), connector("mediawiki"), "variables")
    assert asyncio.run(run()) == ["youtube", "mediawiki"]


def test_connector_failure_keeps_other_results():
    async def broken(request):
        raise RuntimeError("offline")
    async def working(request):
        return ["article"]
    result = asyncio.run(_search_lesson_resources(
        SimpleNamespace(provider="youtube", search=broken),
        SimpleNamespace(provider="mediawiki", search=working), "variables",
    ))
    assert result == ["article"]


def test_without_youtube_key():
    async def search(request):
        return ["article"]
    assert asyncio.run(_search_lesson_resources(None, SimpleNamespace(provider="mediawiki", search=search), "variables")) == ["article"]
