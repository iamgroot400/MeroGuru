"""Versioned prompt + schema for turning one or more concepts into a lesson:
explanation, a practice task, and a short quiz. Kept separate from concept mapping
per plan.md 15.2 ("do not use one large prompt for the entire system").

Content is written in Markdown (rendered by the frontend) so a lesson reads like a
structured page -- headings, bold key terms, worked examples -- rather than a wall
of plain prose. This is deliberately more prescriptive than a minimal prompt: small
and mid-size models default to generic, thin explanations unless the structure is
spelled out.
"""
from __future__ import annotations

LESSON_CONTENT_SCHEMA = {
    "type": "object",
    "required": ["explanation", "key_takeaways", "practice_task", "quiz"],
    "properties": {
        "explanation": {"type": "string", "minLength": 80},
        "key_takeaways": {
            "type": "array",
            "minItems": 2,
            "maxItems": 4,
            "items": {"type": "string"},
        },
        "practice_task": {"type": "string", "minLength": 30},
        "quiz": {
            "type": "array",
            "minItems": 3,
            "maxItems": 4,
            "items": {
                "type": "object",
                "required": ["prompt", "options", "correct_answer", "explanation"],
                "properties": {
                    "prompt": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 5},
                    "correct_answer": {"type": "string"},
                    "explanation": {"type": "string"},
                },
            },
        },
    },
}

SYSTEM_PROMPT = """You are writing one day's lesson for a self-paced learner, in Markdown. \
Given the concept(s) being taught, the learner's level, and any supplied source excerpts, \
produce a JSON object with these fields:

"explanation" -- Markdown text, structured like this:
- Open with one sentence saying plainly what this concept is and why it matters, before \
any jargon.
- Use `##` subheadings to break the explanation into short sections (2-4 sentences each). \
Do not write one undifferentiated block of prose.
- Bold (`**term**`) the first use of any key term you introduce, and define it in the \
same sentence.
- Include at least one concrete worked example or a real-world analogy that makes the \
idea tangible -- not just abstract description. Use a fenced code block for the example \
if the concept is technical/code-related.
- If source excerpts are supplied, ground factual claims in them; do not invent facts \
unsupported by general knowledge or the given sources.
- Match depth to the concept's estimated time budget: a 15-minute concept gets a short, \
focused explanation, not padding.

"key_takeaways" -- 2-4 short bullet strings (no markdown bullet characters, just the text) \
summarizing the single most important things to remember. These should let someone who \
skims only this list still walk away with the core idea.

"practice_task" -- Markdown text with a numbered list of 2-4 concrete steps the learner \
can complete alone, right now, with no supervision or extra tools beyond what a beginner \
already has. End with one sentence stating how the learner will know they succeeded \
(a specific, checkable outcome, not "understand the concept better").

"quiz" -- 3-4 multiple-choice questions that test the *explanation just written*, not \
outside trivia. Requirements per question:
- Exactly one option must be unambiguously correct; correct_answer must match one option \
verbatim.
- Write plausible, specific distractors -- wrong answers that reflect a real \
misunderstanding a learner might have, not obviously-silly filler options.
- The explanation field must say *why* the correct answer is right, referencing the \
concept, not just restate the answer.
- Vary what each question tests (recall a definition, apply the idea to a new case, spot \
a common mistake) rather than asking the same fact four ways."""


def build_user_prompt(concept_titles: list[str], concept_descriptions: list[str], source_excerpt: str | None) -> str:
    lines = [f"Concepts for this lesson: {', '.join(concept_titles)}"]
    for title, desc in zip(concept_titles, concept_descriptions):
        lines.append(f"- {title}: {desc}")
    if source_excerpt:
        lines.append(f"\nSupplied source excerpt (ground claims in this where relevant):\n{source_excerpt[:3000]}")
    return "\n".join(lines)
