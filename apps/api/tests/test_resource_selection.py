from __future__ import annotations

from datetime import datetime, timezone

from packages.connectors.base import ContentAccess, ResourceCandidate
from packages.learning_engine.concept_mapping import Concept
from packages.learning_engine.resource_selection import select_best_resource


def _concept():
    return Concept(
        id="c1",
        title="Basic chord shapes",
        description="Learn A, C, D, E, G open chords",
        difficulty="beginner",
        estimated_minutes=30,
        prerequisite_ids=[],
    )


def _candidate(**overrides):
    defaults = dict(
        provider="youtube",
        external_id="vid1",
        title="Guitar chords for beginners",
        url="https://youtube.com/watch?v=vid1",
        author="Some Channel",
        content_type="video",
        language="en",
        duration_seconds=600,
        license_name="youtube",
        embeddable=True,
        content_access=ContentAccess.METADATA_ONLY,
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        metadata={"description": "Learn basic open chords A C D E G"},
    )
    defaults.update(overrides)
    return ResourceCandidate(**defaults)


def test_no_candidates_returns_none():
    assert select_best_resource([], _concept()) is None


def test_relevant_candidate_beats_irrelevant_one():
    relevant = _candidate(title="Basic chord shapes for guitar", duration_seconds=1800)
    irrelevant = _candidate(external_id="vid2", title="How to bake bread", duration_seconds=1800, metadata={"description": "flour water yeast"})
    best_candidate, score = select_best_resource([irrelevant, relevant], _concept())
    assert best_candidate.external_id == relevant.external_id
    assert score.total > 0


def test_non_embeddable_candidate_is_penalized():
    embeddable = _candidate(duration_seconds=1800)
    not_embeddable = _candidate(external_id="vid2", embeddable=False, duration_seconds=1800)
    best_candidate, _ = select_best_resource([not_embeddable, embeddable], _concept())
    assert best_candidate.external_id == embeddable.external_id


def test_wildly_mismatched_duration_scores_lower_than_reasonable_one():
    from packages.learning_engine.resource_selection import score_candidate

    concept = _concept()  # 30 min estimated
    reasonable = _candidate(duration_seconds=1800)  # 30 min
    hours_long = _candidate(external_id="vid2", duration_seconds=36000)  # 10 hours
    assert score_candidate(reasonable, concept, "en").total > score_candidate(hours_long, concept, "en").total
