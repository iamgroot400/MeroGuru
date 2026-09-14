"""Turns a free-form learning goal into an ordered, acyclic concept graph via the
user's configured AI provider, with structured-output validation and cycle rejection.
"""
from __future__ import annotations

from dataclasses import dataclass

import jsonschema

from packages.ai_providers.base import AIProvider, GenerationRequest

CONCEPT_MAP_SCHEMA = {
    "type": "object",
    "required": ["concepts"],
    "properties": {
        "concepts": {
            "type": "array",
            "minItems": 3,
            "items": {
                "type": "object",
                "required": ["id", "title", "description", "difficulty", "estimated_minutes", "prerequisite_ids"],
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "difficulty": {"type": "string", "enum": ["beginner", "intermediate", "advanced"]},
                    "estimated_minutes": {"type": "integer", "minimum": 5, "maximum": 240},
                    "prerequisite_ids": {"type": "array", "items": {"type": "string"}},
                },
            },
        }
    },
}

SYSTEM_PROMPT = """You are a curriculum designer. Given a learner's goal, starting level, \
and available time, produce an ordered set of concepts (topics/skills) that must be \
learned to achieve the goal, each with clear prerequisites. Concepts already implied \
by the learner's stated starting level should be marked with minimal estimated time \
or omitted. Keep the graph acyclic: a concept's prerequisite_ids must only reference \
concepts that should be learned strictly before it. Do not invent prerequisites that \
are not genuinely required. Prefer 6-20 concepts for a focused goal."""


class ConceptGraphError(ValueError):
    pass


@dataclass
class Concept:
    id: str
    title: str
    description: str
    difficulty: str
    estimated_minutes: int
    prerequisite_ids: list[str]


async def generate_concept_map(
    provider: AIProvider,
    goal_title: str,
    goal_description: str,
    starting_level: str,
    language: str = "en",
) -> list[Concept]:
    user_prompt = (
        f"Goal: {goal_title}\n"
        f"Details: {goal_description}\n"
        f"Learner starting level: {starting_level}\n"
        f"Response language: {language}\n"
    )
    request = GenerationRequest(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt, max_tokens=3000)
    result = await provider.generate_structured(request, CONCEPT_MAP_SCHEMA)
    data = result.data
    if not result.valid:
        # Some models return the concept list as a bare JSON array instead of the
        # requested {"concepts": [...]} object -- valid JSON, wrong top-level shape.
        # Normalize and re-validate rather than rejecting otherwise-good output.
        if isinstance(data, list):
            data = {"concepts": data}
            try:
                jsonschema.validate(data, CONCEPT_MAP_SCHEMA)
            except jsonschema.ValidationError as exc:
                raise ConceptGraphError(f"model returned invalid concept map: {exc.message}") from exc
        else:
            raise ConceptGraphError(f"model returned invalid concept map: {result.validation_errors}")

    concepts = [Concept(**c) for c in data["concepts"]]
    _assert_acyclic(concepts)
    return concepts


def _assert_acyclic(concepts: list[Concept]) -> None:
    by_id = {c.id: c for c in concepts}
    unknown_refs = {
        prereq
        for c in concepts
        for prereq in c.prerequisite_ids
        if prereq not in by_id
    }
    if unknown_refs:
        raise ConceptGraphError(f"prerequisite_ids reference unknown concepts: {unknown_refs}")

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {c.id: WHITE for c in concepts}

    def visit(node_id: str, stack: list[str]) -> None:
        color[node_id] = GRAY
        for prereq in by_id[node_id].prerequisite_ids:
            if color[prereq] == GRAY:
                raise ConceptGraphError(f"dependency cycle detected: {' -> '.join(stack + [prereq])}")
            if color[prereq] == WHITE:
                visit(prereq, stack + [prereq])
        color[node_id] = BLACK

    for concept in concepts:
        if color[concept.id] == WHITE:
            visit(concept.id, [concept.id])


def topological_order(concepts: list[Concept]) -> list[Concept]:
    """Prerequisites always precede dependents. Raises ConceptGraphError on cycles."""
    _assert_acyclic(concepts)
    by_id = {c.id: c for c in concepts}
    visited: set[str] = set()
    ordered: list[Concept] = []

    def visit(node_id: str) -> None:
        if node_id in visited:
            return
        visited.add(node_id)
        for prereq in by_id[node_id].prerequisite_ids:
            visit(prereq)
        ordered.append(by_id[node_id])

    for concept in concepts:
        visit(concept.id)
    return ordered
