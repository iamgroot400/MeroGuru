from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class AssessmentQuestionOut(BaseModel):
    id: UUID
    question_type: str
    prompt: str
    options_json: list
    difficulty: str

    class Config:
        from_attributes = True


class AssessmentOut(BaseModel):
    id: UUID
    assessment_type: str
    passing_score: float
    questions: list[AssessmentQuestionOut]

    class Config:
        from_attributes = True


class AttemptSubmit(BaseModel):
    answers: dict[str, str]  # question_id (str) -> learner answer
    confidence: float = 0.5


class AttemptResult(BaseModel):
    score: float
    passed: bool
    per_question: dict[str, bool]
    explanations: dict[str, str]
