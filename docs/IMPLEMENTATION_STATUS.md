# Implementation status

Kept honest and current. Updated after each working slice, not aspirationally.

Last updated: 2026-09-14

## Full-stack verification pass (docker compose up --build)

Ran the exact documented quickstart (`cp .env.example .env && docker compose up --build`)
end to end, with the real frontend, to find issues that individual dev-process
testing had missed. Found and fixed four real bugs:

1. **API container crash-looped on boot.** `docker-compose.yml`'s `api` service
   command passed `--app-dir apps/api` to uvicorn on top of the Dockerfile's
   `WORKDIR /app/apps/api`, doubling the path (`No module named 'app'`). Fixed by
   dropping the redundant flag.
2. **Ollama credential silently used the wrong model.** Saving an Ollama connection
   via Settings (no explicit model field in that form) fell back to a hardcoded
   `"llama3.1"` in `packages/ai_providers/registry.py` instead of the deployment's
   configured `OLLAMA_CHAT_MODEL`. Fixed in `credential_service.get_provider_for` to
   use the settings-configured model as the fallback for a user-saved Ollama
   credential.
3. **Saving a real (long) API key crashed the request.** `mask_secret()` produced a
   mask the same length as the input key; `provider_credentials.masked_label` is
   `VARCHAR(20)`, so any real ~40-character key overflowed it
   (`StringDataRightTruncation`) and the whole request failed with a generic
   "Cannot reach the API" in the UI. Fixed `mask_secret()` to always return a
   fixed-width `****xxxx` mask regardless of key length (also avoids leaking key
   length as a side channel). Added a regression test (`tests/test_crypto.py`).
4. **Dashboard's weekly-completion calendar had no data to show.** The frontend
   expects `completed_at` on a lesson; the backend never set one. Added a
   `completed_at` column + migration, and set it in `POST /lessons/{id}/complete`.

All four were caught only because the actual `docker compose up --build` path and
the real frontend were exercised — none surfaced in the unit tests or the earlier
manually-run dev-process testing. This is the value of a real full-stack pass over
piecemeal verification.

Also verified in this pass: goal switching, multi-goal dashboard, roadmap
prerequisite resolution, progress-page mastery percentages across repeated
attempts, lesson completion state, credential save/test/remove (including the
confirmation dialog), and the job failure-and-retry UI path (a real invalid-JSON
failure from a small model was caught and displayed correctly with a working
"Try again" button) — all with zero browser console errors across every page.

## Verified: the full primary learning journey, live, in the browser

On 2026-09-14, the entire MVP loop was exercised end-to-end against a real running
stack (Postgres + Redis via docker compose, a locally-pulled Ollama model
`llama3.2:1b`, the FastAPI backend, and the actual React frontend in a browser):

1. Created a real goal ("Learn Python basics") via the goal API.
2. Generated a real AI concept map (6 concepts, correctly ordered, no cycles).
3. The deterministic scheduler built a real 7-day plan respecting the declared
   30 min/day budget, correctly flagging days where a single concept exceeded budget.
4. Opened the dashboard in a browser — showed the real goal, today's lesson, and the
   weekly plan, all live data from the API.
5. Opened a real generated lesson page — explanation, practice task, and a 3-question
   quiz, all AI-generated content rendered correctly.
6. Answered the quiz in the browser (2 correct, 1 wrong) and submitted — got back a
   real 67% score with per-question correct/incorrect feedback and explanations.
7. Confirmed in the database that this triggered the adaptation pipeline: the
   deterministic floor correctly classified the score into the "50-69%" band, the
   mastery score updated conservatively (0.0 → 0.27, not a full jump), and an
   immutable `learning_events` record was written with the floor's reasoning.

This proves the core product loop is real, not just individually-unit-tested pieces.

### A genuine finding from this test, not a bug

The smallest local model (`llama3.2:1b`, ~1.3GB) reliably produced a valid concept
map, but failed structured-JSON validation for 5 of 6 lesson-content generations
(malformed JSON / control characters) — this is a known limitation of very small
quantized models at strict JSON-schema-constrained output, not a defect in the
validation or fallback code. The fallback path worked exactly as designed: failed
lessons got a clear "explanation unavailable, review the resource directly" message
instead of a crash or fabricated content.

It also surfaced a real, fixed bug: `llama3.1` (properly sized) returned the concept
list as a bare JSON array instead of the requested `{"concepts": [...]}` object —
valid data, wrong top-level shape. `concept_mapping.generate_concept_map` now
normalizes a bare-array response before validating, with a regression test
(`test_bare_array_response_is_normalized_and_accepted`).

**Confirmed with the properly recommended model:** regenerated the same goal with
`llama3.1` (4.9GB, ~15 minutes total on CPU). Result: a genuinely well-ordered
7-concept curriculum (guitar basics → tuning → hand position → chord shapes → chord
progressions → strumming → applying chords to songs) with sensible prerequisites and
time estimates; 6 of 7 lessons generated complete explanations, practice tasks, and
2-3 question quizzes, with one explanation citing a real source ("The Hal Leonard
Guitar Method"). 1 of 7 lessons failed JSON validation and fell back to the safe
placeholder, exactly as designed. **Recommendation confirmed:** `llama3.1` (or a
remote provider) for real use; `llama3.2:1b` only for fast pipeline smoke-testing.

## Verified working (tested against a real Postgres + Redis via docker compose)

| Capability | Status |
| --- | --- |
| Docker Compose stack definition (web, api, worker, postgres, redis, ollama) | Implemented |
| Database schema + Alembic migration | Implemented and applied against live Postgres; autogenerated from SQLAlchemy models, 17 tables created successfully |
| `POST /api/v1/goals`, `GET /api/v1/goals` | Implemented and verified live (created and listed a real goal via curl) |
| `GET /health/live`, `GET /health/ready` | Implemented and verified live (readiness checks the real DB connection) |
| `GET /api/v1/credentials` | Implemented and verified live |
| AI provider abstraction (OpenAI-compatible, Anthropic, Ollama adapters) | Implemented, unit-testable; end-to-end call pending a configured provider |
| Concept-graph generation + cycle detection | Implemented (`packages/learning_engine/concept_mapping.py`); cycle rejection is a hard validation, not a warning |
| Deterministic scheduler (time-budget-respecting) | Implemented (`packages/learning_engine/planning.py`) |
| Adaptation floor/ceiling design (deterministic rules + AI suggestion + verdict) | Implemented (`packages/learning_engine/adaptation/`) |
| YouTube connector (official Data API, metadata-only) | Implemented; requires a YouTube API key to exercise live |
| MediaWiki/Wikipedia connector (openly licensed, full-text) | Implemented and wired into plan generation; verified with mocked HTTP tests |
| Resource ranking across pooled YouTube + MediaWiki candidates | Implemented (`resource_selection.py`), explainable score components stored per resource |
| Manual/user-provided resource endpoint | Implemented and verified live (`POST /api/v1/resources/manual`) |
| Credential encryption at rest (Fernet, masked display) | Implemented |
| Celery worker + `generate_plan_task` | Implemented; not yet exercised against a real AI provider in this environment |

## Resource discovery and ranking (added 2026-09-14)

- **Resource ranking is now real**, not "take the first search result." A new
  `packages/learning_engine/resource_selection.py` scores every candidate using the
  formula in `validation.py` (relevance via keyword overlap, duration match against
  the concept's time budget, embeddability/license/language signals) and the
  best-scoring candidate is persisted, with its score and component breakdown stored
  in `Resource.metadata_json` for explainability. Covered by
  `tests/test_resource_selection.py` (4 tests: empty-candidates, relevance ranking,
  embeddability penalty, duration mismatch penalty).
- **MediaWiki/Wikipedia connector implemented** (`packages/connectors/mediawiki.py`),
  using the official Action API. Unlike YouTube, MediaWiki content is openly licensed
  (CC BY-SA), so this connector may fetch full article text via
  `fetch_permitted_content`, not just metadata. Wired into `plan_service.py`
  alongside YouTube — candidates from both connectors are pooled and ranked together
  per lesson, so a lesson can now surface a Wikipedia article when it scores higher
  than the available videos. Covered by `tests/test_mediawiki.py` (2 tests, mocked
  HTTP).
- **Manual/user-provided resource endpoint implemented**: `POST /api/v1/resources/manual`
  and `GET /api/v1/resources/{id}`. Lets a learner attach a URL or paste their own
  notes/transcript against a specific concept, with an explicit `content_access`
  classification (`user-provided-transcript`, `creator-authorized-transcript`, or
  `openly-licensed`) — a transcript-mode submission is rejected by schema validation
  if no text is provided. Persists a `SourceDocument` (with a real SHA-256 content
  hash and permission basis) and a `SourceChunk`. Verified live against the running
  stack: successful creation, rejection of missing text, and correct DB rows
  confirmed by direct query. Not yet covered by an automated test — there's no
  DB-backed test fixture in this repo yet (see below).

## Not yet verified end-to-end

- **Automated DB-integration tests.** All 26 backend tests are pure unit tests against
  `packages/` logic (pytest, no database). Nothing in `apps/api` — routes, services,
  migrations — has an automated test against a real (or in-memory) database yet;
  verification of that layer so far has been live manual exercise of the running
  Docker stack (curl + direct SQL checks), documented above and in the full-stack
  verification section. Adding a test-database fixture (e.g. a throwaway Postgres
  schema per test session) is the next highest-value testing gap to close.
- Embeddings / pgvector semantic search — schema has `source_chunks`; no embedding
  generation or retrieval pipeline implemented yet. The manual-resource endpoint
  stores pasted text as a single unembedded chunk in the meantime.
- Chunking of long source documents — currently stores one `SourceChunk` per
  document regardless of length; splitting into multiple retrievable chunks is
  deferred until the embeddings pipeline exists (no point chunking text nothing can
  search over yet).
- GitHub issue/PR templates — see `.github/` (added alongside this update).

## Known simplifications versus the original plan.md

- No user accounts / authentication — deliberate, per product decision: this is a
  single-user, self-hosted app.
- The adaptation estimator's confidence/support suggestions are logged into
  `learning_events` (`additional_support`, `adaptation_source`) but not yet surfaced
  in a lesson's activities — the frontend has nothing to render them yet.
- Resource credibility, level-match, and practical-value scores in
  `resource_selection.py` are fixed baseline constants (0.6, 0.6, 0.5) rather than
  computed signals — plan.md 13.3 lists richer credibility signals (institutional
  source, community reports, admin approval) that aren't implemented yet. The
  scoring formula and its weights are real and wired in; several of its inputs are
  still placeholders.

## Commands used to verify what's marked "Implemented and verified live"

```bash
docker compose up --build
cd apps/api && alembic revision --autogenerate -m "..."
alembic upgrade head   # if not already applied by the api container's entrypoint
curl -X POST http://localhost:8000/api/v1/goals -H "Content-Type: application/json" -d '{...}'
curl http://localhost:8000/api/v1/goals
curl http://localhost:8000/health/ready
curl -X POST http://localhost:8000/api/v1/resources/manual -H "Content-Type: application/json" -d '{...}'
cd apps/api && pytest tests/ -q     # 26 passed
cd apps/web && npm run test && npm run build
```
