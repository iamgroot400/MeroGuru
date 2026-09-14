# Contributing to MeroGuru

Thanks for considering a contribution. MeroGuru is early-stage — see
[docs/IMPLEMENTATION_STATUS.md](docs/IMPLEMENTATION_STATUS.md) before starting work,
so you know what's actually built versus still planned.

## Workflow

1. Open or comment on an issue describing what you want to change, especially for
   anything larger than a small fix — this avoids duplicated or wasted work.
2. Fork and create a focused branch (one topic per branch/PR).
3. Add tests for new backend logic where practical (`apps/api/tests`, `pytest`).
4. Update `docs/IMPLEMENTATION_STATUS.md` if you change what's implemented vs. planned.
5. Open a pull request describing what changed and why.

## Project layout

- `apps/api` — FastAPI backend
- `apps/web` — React frontend
- `packages/ai_providers` — AI provider adapters (OpenAI-compatible, Anthropic, Ollama)
- `packages/connectors` — learning-source connectors (YouTube, manual content)
- `packages/learning_engine` — concept mapping, scheduling, adaptation logic
- `workers` — Celery background tasks

## Code style

- Backend: type-annotated Python, no dead code, comments only where the *why* isn't
  obvious from the code itself.
- Don't add abstractions or config flags for hypothetical future needs — solve the
  problem in front of you.
- Keep the AI provider and connector interfaces vendor-agnostic; new providers or
  connectors implement the existing interface rather than special-casing themselves
  into the learning engine.

## Reporting security issues

Please see [SECURITY.md](SECURITY.md) — do not open a public issue for a security
vulnerability.
