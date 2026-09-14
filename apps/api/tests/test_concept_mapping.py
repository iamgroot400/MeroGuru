from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from packages.ai_providers.base import StructuredResult
from packages.learning_engine.concept_mapping import (
    Concept,
    ConceptGraphError,
    generate_concept_map,
    topological_order,
)


def _concept(id_, prereqs=None, minutes=30):
    return Concept(
        id=id_,
        title=id_,
        description="",
        difficulty="beginner",
        estimated_minutes=minutes,
        prerequisite_ids=prereqs or [],
    )


def test_topological_order_respects_prerequisites():
    concepts = [
        _concept("c3", prereqs=["c2"]),
        _concept("c1"),
        _concept("c2", prereqs=["c1"]),
    ]
    ordered = topological_order(concepts)
    order_ids = [c.id for c in ordered]
    assert order_ids.index("c1") < order_ids.index("c2") < order_ids.index("c3")


def test_cycle_is_rejected():
    concepts = [
        _concept("a", prereqs=["b"]),
        _concept("b", prereqs=["a"]),
    ]
    with pytest.raises(ConceptGraphError):
        topological_order(concepts)


def test_unknown_prerequisite_is_rejected():
    concepts = [_concept("a", prereqs=["does-not-exist"])]
    with pytest.raises(ConceptGraphError):
        topological_order(concepts)


def test_self_loop_is_rejected():
    concepts = [_concept("a", prereqs=["a"])]
    with pytest.raises(ConceptGraphError):
        topological_order(concepts)


async def test_bare_array_response_is_normalized_and_accepted():
    """Some models (observed with llama3.1) return a bare JSON array instead of
    the requested {"concepts": [...]} object. That's valid, well-formed data in
    the wrong shape -- it should be accepted, not rejected as invalid output."""
    bare_array = [
        {
            "id": "c1",
            "title": "Guitar basics",
            "description": "Hold and posture.",
            "difficulty": "beginner",
            "estimated_minutes": 30,
            "prerequisite_ids": [],
        },
        {
            "id": "c2",
            "title": "First chords",
            "description": "Open chords.",
            "difficulty": "beginner",
            "estimated_minutes": 45,
            "prerequisite_ids": ["c1"],
        },
        {
            "id": "c3",
            "title": "Simple songs",
            "description": "Play a song.",
            "difficulty": "beginner",
            "estimated_minutes": 60,
            "prerequisite_ids": ["c2"],
        },
    ]
    provider = AsyncMock()
    provider.generate_structured.return_value = StructuredResult(data=bare_array, valid=False)

    concepts = await generate_concept_map(
        provider=provider,
        goal_title="Learn guitar",
        goal_description="Play simple songs",
        starting_level="beginner",
    )
    assert [c.id for c in concepts] == ["c1", "c2", "c3"]


async def test_genuinely_invalid_output_still_raises():
    provider = AsyncMock()
    provider.generate_structured.return_value = StructuredResult(
        data={"not_concepts": []}, valid=False, validation_errors=["'concepts' is a required property"]
    )
    with pytest.raises(ConceptGraphError):
        await generate_concept_map(
            provider=provider,
            goal_title="Learn guitar",
            goal_description="Play simple songs",
            starting_level="beginner",
        )
