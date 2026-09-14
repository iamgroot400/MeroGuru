"""Versioned prompt + schema for turning one or more concepts into a lesson:
explanation, a practice task, and a short quiz. Kept separate from concept mapping
per plan.md 15.2 ("do not use one large prompt for the entire system").
"""
from __future__ import annotations

LESSON_CONTENT_SCHEMA = {
    "type": "object",
    "required": ["explanation", "practice_task", "quiz"],
    "properties": {
        "explanation": {"type": "string", "minLength": 50},
        "practice_task": {"type": "string", "minLength": 20},
        "quiz": {
            "type": "array",
            "minItems": 2,
            "maxItems": 4,
            "items": {
                "type": "object",
                "required": ["prompt", "options", "correct_answer", "explanation"],
                "properties": {
                    "prompt": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 5},
                    "correct_answer": {"type": "string"},
                    "explanation": {"type": "string"},
                },
            },
        },
    },
}

SYSTEM_PROMPT = """You are writing one day's lesson for a self-paced learner. Given \
the concept(s) being taught and any supplied source excerpts, write:
1. A clear, self-contained explanation appropriate to the learner's level. If source \
excerpts are supplied, ground factual claims in them; do not invent facts unsupported \
by general knowledge or the given sources.
2. A concrete practice task the learner can complete without supervision.
3. A short multiple-choice quiz (2-4 questions) that tests understanding of the \
explanation, each with exactly one correct_answer that matches one of the options \
verbatim.
Keep the explanation length proportional to the concept's estimated time budget."""


def build_user_prompt(concept_titles: list[str], concept_descriptions: list[str], source_excerpt: str | None) -> str:
    lines = [f"Concepts for this lesson: {', '.join(concept_titles)}"]
    for title, desc in zip(concept_titles, concept_descriptions):
        lines.append(f"- {title}: {desc}")
    if source_excerpt:
        lines.append(f"\nSupplied source excerpt (ground claims in this where relevant):\n{source_excerpt[:3000]}")
    return "\n".join(lines)
