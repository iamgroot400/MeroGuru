# Lesson generation latency

## Findings (2026-09-17)

The configured default is llama3.1. The host has an RTX 4050 with 6 GB VRAM.
Docker was stopped during inspection, and the host Ollama CLI was unavailable;
no actual inference benchmark or CPU/GPU residency could be measured.

The current critical path is concept map -> every scheduled lesson in sequence
(each includes explanation, practice and quiz) -> final database commit -> UI poll.
The frontend polls every two seconds but reloads the plan only when the job ends.
Thus even the first lesson is hidden until the whole week is ready.

## Implemented

- Honor GenerationRequest.max_tokens through Ollama options.num_predict.
- Pass the JSON schema as Ollama format, keeping application-side validation.
- Keep the model resident for 15 minutes after requests.
- Log load, prompt, total durations, output tokens and generation tokens/second.
- Run Wikipedia/YouTube searches concurrently with lesson inference; retain
  independent connector failure handling and cancel sibling work on LLM failure.
- Add an optional NVIDIA Compose override. No model or runtime was changed.

These changes do not make a freshly generated full lesson instantaneous.
Output limits can expose truncated JSON; validation continues to reject it.

## Enable and measure GPU inference

Start Docker Desktop with WSL2 GPU support, then from the repository root:

```powershell
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
docker compose exec ollama ollama ps
```

Check `ollama ps` during a generation: aim for `100% GPU`. The base Compose
configuration does not request GPU devices. An 8B model plus context/cache may
be tight on this 6 GB GPU; benchmark a smaller quantized model if residency is
partial. Compare lesson quality and schema validity before changing the default.
Do not increase inference concurrency until a single request fits comfortably.
Repeat the same generation workload cold and warm and inspect worker logs.
Do not log prompt text or credentials in performance telemetry.

## Architecture needed for an instant-feeling experience

1. Commit the concept map and lesson outlines immediately after scheduling.
   Expose generation states (pending/generating/ready/failed) separately from
   learning completion status, so incomplete lessons cannot be marked complete.
2. Generate the first lesson as the foreground priority; publish it independently.
   Poll progress without replacing the whole page with a loading screen, or use SSE.
3. Stream the explanation as provisional text; validate the final content before
   enabling practice/quiz/completion. Setting stream=true alone is insufficient:
   the adapter, API and frontend must consume the stream, and partial JSON cannot
   be treated as a valid lesson.
4. Prepare the next lesson while the learner studies the current one. Store ready
   content in the database so ordinary lesson opening needs no inference.
5. Make each lesson job idempotent and resumable. Use an atomic claim/lock and
   transactional writes so retries do not duplicate activities or assessments.
   Prioritize opened lessons over prefetch work; avoid many simultaneous LLM calls.
6. Key any reusable content cache by concepts, learner level, language, model,
   prompt/schema version and source revision. Never mix learner-specific content.

Measure click-to-outline, time-to-first-readable-content, first-lesson-ready,
whole-plan-ready, validation failure rate and quality. Cached/prefetched opening
can target sub-second latency; fresh inference depends on measured hardware speed.

References:
- https://docs.ollama.com/api/chat
- https://docs.ollama.com/capabilities/structured-outputs
- https://docs.ollama.com/faq
