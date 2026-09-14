# Third-party notices

MeroGuru's AGPL-3.0 license covers this repository's own code only. It does not
change the license terms of the following, which you configure or connect to
separately:

## AI models / providers

You bring your own credentials for these; MeroGuru does not bundle or redistribute
any model:

- **Ollama** and any model you pull through it (e.g. Llama, Mistral, Qwen) — each
  model has its own license; check before commercial use.
- **OpenAI API** — subject to [OpenAI's terms of use](https://openai.com/policies/).
- **Anthropic API** — subject to [Anthropic's terms of service](https://www.anthropic.com/legal/consumer-terms).

## Content sources

- **YouTube Data API** — subject to the [YouTube API Services Terms of Service](https://developers.google.com/youtube/terms/api-services-terms-of-service).
  Video content itself remains under each creator's own license/terms.
- **MediaWiki / Wikipedia** content (when the connector is used) is licensed under
  [CC BY-SA](https://creativecommons.org/licenses/by-sa/4.0/); attribution is
  preserved in stored resource metadata.

## Key open-source dependencies

See `apps/api/requirements.txt` and `apps/web/package.json` for the full dependency
list; each is used under its own upstream license (mostly MIT/BSD/Apache-2.0).
Notable ones:

- FastAPI (MIT), SQLAlchemy (MIT), Alembic (MIT), Celery (BSD), Redis (BSD)
- React (MIT), Vite (MIT)
- pgvector (PostgreSQL License)

If you believe an attribution is missing or incorrect, please open an issue.
