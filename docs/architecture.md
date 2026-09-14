# Architecture

## Components

- **apps/web** — React + Vite frontend. No accounts/login: single-user, self-hosted.
- **apps/api** — FastAPI backend. Owns validation, persistence, and background job
  creation. Contains no business logic itself — it calls into `packages/`.
- **workers/** — Celery worker running slow/retryable jobs (plan generation).
- **packages/ai_providers** — Provider-agnostic interface (`AIProvider`) with adapters
  for OpenAI-compatible endpoints, Anthropic, and local Ollama. The rest of the app
  never imports a vendor SDK directly.
- **packages/connectors** — Learning-source connectors (YouTube, manual/user-provided
  content), each implementing the same `LearningSourceConnector` interface.
- **packages/learning_engine** — Deterministic domain logic: concept-graph generation
  (AI-assisted, cycle-validated), scheduling, resource ranking, and adaptation.

## The adaptation model: a deterministic floor, an AI ceiling

Learner performance drives two independent judgments that are then combined, not
left to the AI alone:

1. **`adaptation/deterministic_rules.py`** — a fixed, versioned rule table (below 50%
   score → easier explanation, 85%+ → advance, two strong attempts on separate days →
   allow mastered, etc.). This is the *floor*: the minimum required response, and it
   never changes based on what an AI model thinks.
2. **`adaptation/estimator.py`** — the AI may propose *additional* support (an extra
   worked example, a different resource format, an inserted review session) — but it
   is structurally forbidden from removing a required prerequisite or lowering the
   target mastery bar. If it tries, `verdict.py` rejects the suggestion and falls back
   to the floor alone.
3. **`adaptation/verdict.py`** — combines the two: the floor's required actions always
   apply; the AI's suggestion can only add on top, and only above a confidence
   threshold. Below that threshold (or on disagreement with the floor), the floor wins
   outright.

This mirrors a common pattern in safety-critical monitoring systems: rules set a
guaranteed minimum, a model can escalate additional care, but it can never talk the
system down from what the rules require.

## Data flow: goal → plan

1. `POST /goals` stores the learner's goal, level, deadline, and time budget.
2. `POST /goals/{id}/generate-plan` creates a `BackgroundJob` and enqueues a Celery task.
3. The worker calls `learning_engine.concept_mapping` with the user's configured AI
   provider to produce an ordered, acyclic concept graph (cycle detection is a hard
   validation step, not a suggestion).
4. `learning_engine.planning` deterministically schedules concepts into daily lessons
   that respect `minutes_per_day` — the AI never controls the time math directly.
5. For each lesson, the AI generates an explanation, practice task, and quiz
   (`prompts/lesson.py`), validated against a JSON schema before being persisted.
6. If a YouTube API key is configured, the concept's primary resource is looked up via
   the official Data API (metadata only).
7. Quiz results feed back into `adaptation/` (see above), updating `mastery_records`
   and logging an immutable `learning_events` entry for every change.

## Why no accounts

MeroGuru is designed for one person to self-host their own instance. This removes an
entire class of complexity (auth, session security, cross-user authorization tests)
that a personal deployment doesn't need. If multi-user support becomes a real need
later, it's a deliberate, scoped addition — not a retrofit assumed from day one.
