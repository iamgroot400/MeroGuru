import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { ExternalLink } from "lucide-react";
import { idPath, optional, post, request } from "../api/client";
import type { Assessment, Attempt, Lesson, Resource } from "../api/types";
import { useAsync } from "../hooks";
import { Empty, ErrorState, Loading, Markdown, PageHeading, Time } from "../components";
import { percent, safeUrl } from "../utils";
import { normalizeLesson } from "../api/adapters";

function ResourceLink({ resource }: { resource: Resource }) {
  const url = safeUrl(resource.url);
  return url ? (
    <a
      className="resource-link"
      href={url}
      target="_blank"
      rel="noopener noreferrer"
    >
      <span>
        {resource.title || "Learning resource"}
        <small>{new URL(url).hostname} · Opens in a new tab</small>
      </span>
      <ExternalLink size={18} aria-hidden="true" />
    </a>
  ) : (
    <p className="notice">
      {resource.title}: this source has no usable web link.
    </p>
  );
}
function Quiz({ lessonId }: { lessonId: string }) {
  const state = useAsync(`assessment-${lessonId}`, (signal) =>
    optional<Assessment>(
      `/lessons/${idPath(lessonId)}/assessment`,
      signal,
    ).then((a) =>
      a
        ? {
            ...a,
            questions: a.questions.map((q) => ({
              ...q,
              options: q.options || q.options_json,
            })),
          }
        : null,
    ),
  );
  const [answers, setAnswers] = useState<Record<string, string>>({}),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [result, setResult] = useState<Attempt | null>(null);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!state.data) return;
    if (state.data.questions.some((q) => !answers[q.id]?.trim())) {
      setError("Answer every question before checking your understanding.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      setResult(
        await post<Attempt>(`/assessments/${idPath(state.data.id)}/attempts`, {
          answers,
        }),
      );
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Could not submit your answers.",
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="lesson-section">
      <h2>Check your understanding</h2>
      {state.loading ? (
        <Loading>Loading your quiz…</Loading>
      ) : state.error ? (
        <ErrorState message={state.error} retry={state.reload} />
      ) : !state.data?.questions?.length ? (
        <Empty
          title="No quiz is available yet."
          action={
            <button className="secondary" onClick={state.reload}>
              Check again
            </button>
          }
        >
          You can still work through the lesson and practice task.
        </Empty>
      ) : result ? (
        <div className="quiz-result" role="status">
          <h3>
            {result.score == null
              ? "Answers submitted"
              : `You scored ${percent(result.score)}%`}
          </h3>
          <p className="prose">
            {result.feedback ||
              "Your answers have been recorded. Keep practicing to strengthen your understanding."}
          </p>
          {result.explanations &&
            state.data?.questions.map((q) => (
              <div key={q.id}>
                <h3>{q.prompt}</h3>
                <p>
                  {result.per_question?.[q.id] ? "Correct" : "Keep practicing"}
                </p>
                <p className="prose">{result.explanations?.[q.id]}</p>
              </div>
            ))}
          <button
            className="secondary"
            onClick={() => {
              setResult(null);
              setAnswers({});
            }}
          >
            Practice again
          </button>
        </div>
      ) : (
        <form onSubmit={submit}>
          {state.data.questions.map((q, i) => (
            <fieldset className="question" key={q.id}>
              <legend>
                {i + 1}. {q.prompt}
              </legend>
              {q.options?.length ? (
                q.options.map((option, j) => {
                  const value = typeof option === "string" ? option : option.id;
                  const text =
                    typeof option === "string" ? option : option.text;
                  return (
                    <label className="answer" key={j}>
                      <input
                        type="radio"
                        name={`question-${q.id}`}
                        required
                        checked={answers[q.id] === value}
                        disabled={busy}
                        value={value}
                        onChange={() =>
                          setAnswers((old) => ({ ...old, [q.id]: value }))
                        }
                      />
                      {text}
                    </label>
                  );
                })
              ) : (
                <>
                  <label className="sr-only" htmlFor={`answer-${q.id}`}>
                    Your answer to question {i + 1}
                  </label>
                  <textarea
                    id={`answer-${q.id}`}
                    rows={3}
                    required
                    disabled={busy}
                    value={answers[q.id] || ""}
                    onChange={(e) =>
                      setAnswers((old) => ({ ...old, [q.id]: e.target.value }))
                    }
                  />
                </>
              )}
            </fieldset>
          ))}
          {error && <ErrorState message={error} />}
          <button disabled={busy}>
            {busy ? "Checking answers…" : "Check my answers"}
          </button>
        </form>
      )}
    </section>
  );
}
function Feedback({ lessonId }: { lessonId: string }) {
  const [difficulty, setDifficulty] = useState(""),
    [usefulness, setUsefulness] = useState(""),
    [confidence, setConfidence] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [saved, setSaved] = useState(false),
    [timeSpent, setTimeSpent] = useState("");
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await post(`/lessons/${idPath(lessonId)}/feedback`, {
        difficulty:
          Number(difficulty) <= 2
            ? "too_easy"
            : Number(difficulty) === 3
              ? "just_right"
              : "too_difficult",
        usefulness: Number(usefulness),
        confidence: (Number(confidence) - 1) / 4,
        time_spent_minutes: Number(timeSpent),
      });
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save feedback.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="feedback">
      <h2>How did this feel?</h2>
      <p>Your feedback helps the next lesson fit you better.</p>
      {saved ? (
        <p role="status">
          Feedback saved. Thank you for reflecting on your learning.
        </p>
      ) : (
        <form onSubmit={submit}>
          <div className="feedback-grid">
            {[
              {
                id: "difficulty",
                label: "Difficulty",
                value: difficulty,
                set: setDifficulty,
                options: [
                  "Very easy",
                  "Easy",
                  "About right",
                  "Hard",
                  "Very hard",
                ],
              },
              {
                id: "usefulness",
                label: "Usefulness",
                value: usefulness,
                set: setUsefulness,
                options: [
                  "Not useful",
                  "Slightly useful",
                  "Somewhat useful",
                  "Useful",
                  "Very useful",
                ],
              },
              {
                id: "confidence",
                label: "Confidence",
                value: confidence,
                set: setConfidence,
                options: [
                  "Not confident",
                  "A little confident",
                  "Somewhat confident",
                  "Confident",
                  "Very confident",
                ],
              },
            ].map((field) => (
              <div key={field.id}>
                <label htmlFor={field.id}>{field.label}</label>
                <select
                  id={field.id}
                  required
                  value={field.value}
                  disabled={busy}
                  onChange={(e) => field.set(e.target.value)}
                >
                  <option value="">Choose a rating</option>
                  {field.options.map((option, i) => (
                    <option key={option} value={i + 1}>
                      {option}
                    </option>
                  ))}
                </select>
              </div>
            ))}
          </div>
          {error && <ErrorState message={error} />}
          <label htmlFor="time-spent">Time spent (minutes)</label>
          <input
            id="time-spent"
            required
            type="number"
            min={0}
            max={1440}
            step={1}
            value={timeSpent}
            disabled={busy}
            onChange={(e) => setTimeSpent(e.target.value)}
          />
          <div className="button-row">
            <button className="secondary" disabled={busy}>
              {busy ? "Saving…" : "Save feedback"}
            </button>
          </div>
        </form>
      )}
    </section>
  );
}
export function LessonPage() {
  const { lessonId = "" } = useParams();
  return <LessonDetail key={lessonId} lessonId={lessonId} />;
}
function LessonDetail({ lessonId }: { lessonId: string }) {
  const state = useAsync(`lesson-${lessonId}`, (signal) =>
    request<Lesson>(`/lessons/${idPath(lessonId)}`, { signal }),
  );
  const [busy, setBusy] = useState(false),
    [complete, setComplete] = useState(false),
    [error, setError] = useState("");
  if (state.loading) return <Loading>Getting your lesson ready…</Loading>;
  if (state.error)
    return <ErrorState message={state.error} retry={state.reload} />;
  if (!state.data) return <Empty title="This lesson is not available." />;
  const lesson = normalizeLesson(state.data),
    resources = lesson.resources || (lesson.resource ? [lesson.resource] : []);
  const finish = async () => {
    setBusy(true);
    setError("");
    try {
      await post(`/lessons/${idPath(lessonId)}/complete`);
      setComplete(true);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Could not complete your lesson.",
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="lesson-page">
      <Link
        className="text-link"
        to={lesson.goal_id ? `/goals/${idPath(lesson.goal_id)}/roadmap` : "/"}
      >
        Back to your learning path
      </Link>
      <PageHeading
        title={lesson.title || "Your lesson"}
        action={<Time value={lesson.estimated_minutes} />}
      />
      <section className="objective">
        <h2>By the end of this lesson</h2>
        <p>{lesson.objective || "The objective is not available yet."}</p>
      </section>
      <section className="lesson-section">
        <h2>Let’s explore</h2>
        {lesson.explanation ? (
          <Markdown text={lesson.explanation} />
        ) : (
          <p className="muted">An explanation has not been provided yet.</p>
        )}
      </section>
      <section className="lesson-section">
        <h2>Learn from a resource</h2>
        {resources.length ? (
          resources.map((r, i) => <ResourceLink key={i} resource={r} />)
        ) : (
          <p className="muted">
            No resource has been attached to this lesson yet.
          </p>
        )}
      </section>
      <section className="practice">
        <h2>Put it into practice</h2>
        {lesson.practice_task ? (
          <Markdown text={lesson.practice_task} />
        ) : (
          <p className="prose muted">No practice task has been provided yet.</p>
        )}
      </section>
      <Quiz lessonId={lessonId} />
      <section className="lesson-section citations">
        <h2>Sources & further reading</h2>
        {lesson.citations?.length ? (
          lesson.citations.map((r, i) => <ResourceLink key={i} resource={r} />)
        ) : (
          <p className="muted">
            No source citations were supplied for this lesson.
          </p>
        )}
      </section>
      <Feedback lessonId={lessonId} />
      <div className="completion">
        {error && <ErrorState message={error} />}
        <p role="status">
          {complete || lesson.completed_at || lesson.status === "completed"
            ? "Lesson completed. Another step on your path."
            : "Worked through the material? Mark this lesson complete."}
        </p>
        <button
          disabled={
            busy ||
            complete ||
            !!lesson.completed_at ||
            lesson.status === "completed"
          }
          onClick={() => void finish()}
        >
          {busy
            ? "Saving your progress…"
            : complete || lesson.completed_at || lesson.status === "completed"
              ? "Lesson completed"
              : "Complete lesson"}
        </button>
      </div>
    </div>
  );
}
