from __future__ import annotations

import jsonschema
import pytest

from prompts.lesson import LESSON_CONTENT_SCHEMA, build_user_prompt

VALID_SAMPLE = {
    "explanation": "## What it is\nA **variable** stores a value under a name so it can be reused.\n\n## Example\n```python\nx = 1\n```",
    "key_takeaways": ["Variables store values", "Names should be descriptive"],
    "practice_task": "1. Create a variable.\n2. Print it.\n\nYou're done when it prints without error.",
    "quiz": [
        {"prompt": "What is a variable?", "options": ["A stored value", "A loop", "A function"], "correct_answer": "A stored value", "explanation": "Because it names a stored value."},
        {"prompt": "Which is valid?", "options": ["x = 1", "1 = x", "= x 1"], "correct_answer": "x = 1", "explanation": "Assignment target must be on the left."},
        {"prompt": "What prints x?", "options": ["print(x)", "echo x", "show(x)"], "correct_answer": "print(x)", "explanation": "print() is the built-in output function."},
    ],
}


def test_valid_sample_matches_schema():
    jsonschema.validate(VALID_SAMPLE, LESSON_CONTENT_SCHEMA)


def test_missing_key_takeaways_is_rejected():
    bad = {k: v for k, v in VALID_SAMPLE.items() if k != "key_takeaways"}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, LESSON_CONTENT_SCHEMA)


def test_too_few_quiz_questions_is_rejected():
    bad = {**VALID_SAMPLE, "quiz": VALID_SAMPLE["quiz"][:2]}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, LESSON_CONTENT_SCHEMA)


def test_build_user_prompt_includes_source_excerpt_when_given():
    prompt = build_user_prompt(["Variables"], ["Named storage"], "Some source text")
    assert "Variables" in prompt
    assert "Some source text" in prompt


def test_build_user_prompt_omits_excerpt_section_when_none():
    prompt = build_user_prompt(["Variables"], ["Named storage"], None)
    assert "Supplied source excerpt" not in prompt
