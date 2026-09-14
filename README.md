# MeroGuru

An open-source, self-hosted adaptive learning platform. Tell it what you want to learn,
how much time you have, and what you already know — it builds a day-by-day plan, finds
resources, tests your understanding, and reshapes your plan based on how you actually do.

Single-user by design: run your own instance, bring your own AI provider key (or use
the bundled local model), and keep your learning data on your own machine.

## Status

This is an early, actively-built MVP. See [docs/IMPLEMENTATION_STATUS.md](docs/IMPLEMENTATION_STATUS.md)
for exactly what works today versus what's still in progress — that document is kept
honest and up to date rather than aspirational.

## Quickstart

Requirements: Docker Desktop (or Docker Engine + Compose) running on your machine.

```bash
git clone <this-repo-url>
cd MeroGuru
cp .env.example .env
docker compose up --build
```

Then open **http://localhost:3000**.

- The API runs at `http://localhost:8000` (interactive docs at `/docs`).
- A local Ollama model is used by default — no paid API key required. On first run,
  pull a model into the Ollama container:
  ```bash
  docker compose exec ollama ollama pull llama3.1
  ```
  `llama3.1` (8B) reliably produces valid lesson content. Smaller models like
  `llama3.2:1b` are fast but frequently fail structured JSON generation for lesson
  content (the app falls back gracefully rather than crashing, but quality suffers) —
  fine for a quick smoke test of the pipeline, not recommended for real use.
- To use a stronger remote model instead, go to **Settings** in the app and add your
  own OpenAI or Anthropic API key. Your key is encrypted at rest and never displayed
  again in full (only the last 4 characters are shown once saved).
- To get YouTube video recommendations in your lessons, add a YouTube Data API key
  in Settings (free from the [Google Cloud Console](https://console.cloud.google.com/)).

## How it works

1. **Create a goal** — what you want to learn, your starting level, how much time you
   have per day, and which days you study.
2. **MeroGuru generates a roadmap** — your configured AI model breaks the goal into an
   ordered set of concepts with prerequisites, which a deterministic scheduler fits
   into a day-by-day plan that never silently exceeds your declared time budget.
3. **Daily lessons** — each lesson has an explanation, a linked resource (YouTube
   video, when available), a practice task, and a short quiz.
4. **Adaptive replanning** — your quiz scores drive concept mastery tracking. A fixed,
   auditable rule set (not just an AI's opinion) decides when you need easier content,
   more review, or you're ready to advance — the AI can only *add* supplementary
   support on top of those rules, never remove a required prerequisite. See
   [docs/architecture.md](docs/architecture.md) for the full design.

## Content and licensing policy

MeroGuru does not scrape or download YouTube captions/audio/video. YouTube integration
uses only the official Data API for discovery and metadata; videos are embedded and
watched directly on YouTube. Transcript-based lesson generation only uses text you
paste in yourself (your own notes, or a transcript you have the right to use) — never
an unauthorized scrape. See [docs/content-policy.md](docs/content-policy.md).

## Development

```bash
cd apps/api && pip install -r requirements.txt   # backend
cd apps/web && npm install                        # frontend
```

Backend tests: `pytest` (from `apps/api`). Migrations: `alembic upgrade head`.

## License

AGPL-3.0 — see [LICENSE](LICENSE). This covers the MeroGuru application code only;
it does not change the license of any AI model, third-party content, or library you
configure or link to. See [LICENSE](LICENSE) for details.
