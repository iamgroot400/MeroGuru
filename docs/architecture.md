# Architecture

## Components

- **apps/web** — React + Vite frontend. No accounts/login: single-user, self-hosted.
- **apps/api** — the **orchestrator**. FastAPI backend that owns validation,
  persistence (the only service with a database), and background job creation. Talks
  to `apps/brain` over HTTP for adaptation and analytics rather than running that
  logic in-process.
- **apps/brain** — the **brain**. A separate, stateless FastAPI service (no database
  of its own) that owns the adaptation engine and learner-data processing:
  `POST /brain/v1/adapt` (floor + AI estimator + verdict, per quiz attempt) and
  `POST /brain/v1/analytics` (raw `learning_events` → chart-ready time series). The
  orchestrator passes it exactly the context each call needs (event history, the
  resolved AI provider config) and persists whatever comes back. Split out so the
  adaptation/analytics workload scales and fails independently of the
  request/routing layer — a slow or crashed AI call in `/adapt` can't take down goal
  CRUD or plan generation, and vice versa.
- **workers/** — Celery worker running slow/retryable jobs (plan generation).
- **packages/ai_providers** — Provider-agnostic interface (`AIProvider`) with adapters
  for OpenAI-compatible endpoints (including Groq), Anthropic, and local Ollama. The
  rest of the app never imports a vendor SDK directly. Both `apps/api` (to build a
  live provider for plan/lesson generation) and `apps/brain` (to build one for the
  adaptation estimator) depend on this package; a provider is never passed between
  the two services as a live object, only as a serialized config
  (`credential_service.get_active_ai_provider_config`).
- **packages/connectors** — Learning-source connectors (YouTube, MediaWiki,
  manual/user-provided content), each implementing the same `LearningSourceConnector`
  interface.
- **packages/learning_engine** — Deterministic domain logic: concept-graph generation
  (AI-assisted, cycle-validated), scheduling, resource ranking, and adaptation
  (`adaptation/`, `analytics.py`) — shared by both services so there is one
  implementation of each, not a copy living in each service.

## Orchestrator/brain split: resilience, and taking the AI call off the request path

`apps/api` never assumes brain is reachable, and — more importantly for perceived
speed — grading a quiz never *waits* on brain or on Ollama at all.

Splitting adaptation into its own service does not make Ollama's inference faster;
Ollama's token-generation speed is bound by the model and the hardware, not by which
process calls it. The actual latency fix is architectural: `POST
/assessments/{id}/attempts` (`assessments.py` → `mastery_service.record_attempt_and_update_mastery`)
computes the deterministic floor and updates `mastery_records` using pure,
in-process Python — zero network calls — and returns to the learner immediately.
The AI estimator's optional supplementary suggestion (an extra worked example, a
different resource format, an inserted review session) is enqueued as a Celery task
(`enrich_adaptation_task` in `workers/tasks.py`) that calls the brain service
*after* the response has already gone out, and patches the `additional_support` /
`adaptation_source` fields onto the already-written `learning_events` row once it
finishes. The floor's mastery score/state are never revised by this — by design,
the AI can only ever add supplementary support, never change the required outcome,
so there's nothing to reconcile if enrichment fails or never runs.

`goals.get_analytics` (a GET, not on any critical write path) still calls brain
synchronously with a local fallback on failure, since it does no AI work at all —
it's just reshaping the `learning_events` log into chart series — so the fallback
there is about brain availability, not latency.

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
7. Quiz results are graded in the orchestrator, which then calls the brain service's
   `/brain/v1/adapt` (see above) with the event history and resolved provider config;
   the response updates `mastery_records` and is logged as an immutable
   `learning_events` entry for every change.

## Why no accounts

MeroGuru is designed for one person to self-host their own instance. This removes an
entire class of complexity (auth, session security, cross-user authorization tests)
that a personal deployment doesn't need. If multi-user support becomes a real need
later, it's a deliberate, scoped addition — not a retrofit assumed from day one.
