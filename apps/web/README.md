# MeroGuru web

Single-user React + TypeScript + Vite frontend. There is no login, user context, token storage, authentication header, or browser cookie transmission. All application files are contained in this directory.

## Run

```sh
npm ci
npm run dev
```

Open http://localhost:3000. Set `VITE_API_BASE_URL` in `.env.local` when your API is elsewhere; the default is `http://localhost:8000`. Both an origin and an origin ending in `/api/v1` are accepted. Vite environment variables are public configuration; never place provider keys in them.

The existing repository Docker Compose web service can build this directory. From the repository root, run `docker compose up --build web`. API CORS must allow the web origin. The API URL is resolved by the browser, so use a browser-accessible hostname rather than the Docker service name.

The included Dockerfile serves the client through Vite, matching the repository's local Docker setup. `npm run build` creates a static production bundle in `dist/`; a production static server needs SPA fallback to `index.html` for deep links. Fonts are bundled locally, with system fallbacks; no Google Fonts connection is required.

## Verify

```sh
npm run build
npm test
npm run test:e2e
```

Browser tests currently use installed Microsoft Edge. For another machine, change the Playwright `channel` to an installed Chromium browser, or remove `channel` and run `npx playwright install chromium`. Test fixtures exist only in `tests/`; application pages never substitute invented learning data. The browser suite covers 400px layout, accessibility, goal creation, prerequisite ordering, quiz submission, feedback, credentials and errors. Screenshots are written to `test-results/`.

## API integration

`src/api/client.ts` wraps fetch, adds JSON headers, omits cookies, times out requests, and supports cancellation. It never attaches auth headers or redirects to login. Arbitrary server error text is intentionally not shown, because provider errors can echo API keys. `src/api/types.ts` describes the response contract and `src/api/adapters.ts` handles the existing backend's alternate shapes.

The frontend accepts the current backend's array concept map with `external_key` / `prerequisite_keys`, array mastery records, lesson `activities`, quiz `options_json`, credential `validation_status`, and test result `{ok}`. It also accepts the brief's `validated` credential field. Feedback is aligned to the backend: difficulty is `too_easy`, `just_right`, or `too_difficult`; usefulness is 1–5; confidence is 0–1; and the actual user-entered `time_spent_minutes` is included. Study days use Monday = 0 through Sunday = 6. Scores use 0–1.

### Backend fields still needed

The API files present when this frontend was built do not expose enough data for every requested view. The frontend implements these views and their empty/unavailable states, and automatically uses the following fields when the backend provides them:

- **Plan discovery:** `GET /goals/{id}` must include `plan_id` or `active_plan_id`. Neither the goal nor job endpoint currently returns a plan ID. Without it, the client cannot call the supplied `/plans/{id}` or `/plans/{id}/today` endpoints; it shows the roadmap entry instead. Ideally also return `job_id` for an unfinished generation job, so polling can resume across devices. The client remembers a newly started job ID in session storage and resumes it after refresh.
- **Weekly completion dates:** plan lesson summaries must include `completed_at` (ISO timestamp or null). The existing lesson model exposes only `status`. The client never treats a scheduled date as a completion date; it displays “Completion dates unavailable” if completed lessons lack timestamps.
- **Assessment history:** `GET /goals/{id}/mastery` can return `{concepts: [...records], assessment_history: [...attempts]}`. History entries need `id`, optional `title`, `created_at`, and `score` (0–1). The current array response supports concept mastery but has no historical attempts. The UI explicitly reports that history was not supplied; newly submitted quiz results are shown in the lesson.
- **Citations:** lesson responses can include `citations: [{title, url}]` and `resources: [{title, url}]`. Current activity instructions are displayed, and resource URLs in them are linked. No citations are invented when the backend omits them. A `goal_id` on each lesson also enables its direct roadmap return link.

No backend files have been modified by this frontend implementation.

## Credential behavior

Credentials are sent directly to this instance's API and held only in the editing input until the save succeeds or is cancelled. Saved labels show at most the last four characters. Keys are never written to local or session storage, URLs, logs, or analytics. Raw API responses containing secrets are never rendered. The browser must still transmit the key once to save it; the “never shown again” guarantee concerns the saved UI.

The current POST endpoint creates a new credential instead of updating one. Replace first creates the new credential, then deletes the old one. If creation fails the old credential is untouched. If deletion fails, the page keeps a clear cleanup retry. Every returned credential is shown, so older duplicates remain removable. Saving an AI credential activates that provider according to the current backend behavior; the active provider is labelled.

Ollama's base URL defaults to `http://ollama:11434` for this repository's Compose service. Its optional key sends the non-secret value `ollama` when empty because the existing API requires a nonempty string but discards the key for this provider.

## File map

- `src/App.tsx`: responsive application frame and routes.
- `src/context.tsx`: goal list and current-goal context.
- `src/pages/`: Dashboard, GoalWizard, Settings, Roadmap/Progress, Lesson.
- `src/components.tsx`: shared loading, error, empty, progress and lesson components.
- `src/hooks.ts`: abortable loading with stale-request protection and retry.
- `src/styles.css`: local typography, solid colors, visible focus, mobile layout and reduced motion.
- `SOURCE_BUNDLE.md`: complete authored source files collected in one document for copying.
