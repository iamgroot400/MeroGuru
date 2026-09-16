import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Check,
  CheckCircle2,
  ExternalLink,
  Flag,
  LockKeyhole,
  PencilLine,
  Target,
  XCircle,
} from "lucide-react";
import { idPath, optional, post, request } from "../api/client";
import type { Assessment, Attempt, Lesson, Resource } from "../api/types";
import { useAsync } from "../hooks";
import {
  Empty,
  ErrorState,
  Loading,
  Markdown,
  PageHeading,
  Time,
} from "../components";
import { percent, safeUrl } from "../utils";
import { normalizeLesson } from "../api/adapters";

type Draft = {
  step: number;
  learned: boolean;
  practiced: boolean;
  notes: string;
  answers: Record<string, string>;
  passedId?: string;
  feedbackSaved: boolean;
  confidence: string;
};
const fresh: Draft = {
  step: 0,
  learned: false,
  practiced: false,
  notes: "",
  answers: {},
  feedbackSaved: false,
  confidence: "",
};
function readDraft(id: string): Draft {
  try {
    const raw = JSON.parse(
      sessionStorage.getItem("meroguru:lesson:" + id) || "null",
    );
    return raw && typeof raw === "object"
      ? {
          ...fresh,
          ...raw,
          step: Math.max(0, Math.min(3, Number(raw.step) || 0)),
          answers:
            raw.answers && typeof raw.answers === "object" ? raw.answers : {},
        }
      : { ...fresh };
  } catch {
    return { ...fresh };
  }
}
const stages = [
  { name: "Learn", icon: BookOpen, description: "Explore the idea" },
  { name: "Practice", icon: PencilLine, description: "Try it yourself" },
  { name: "Check", icon: Target, description: "Test your understanding" },
  { name: "Reflect", icon: Flag, description: "Save your progress" },
];

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
      <ExternalLink size={18} />
    </a>
  ) : (
    <p className="notice">
      {resource.title}: no usable source link was supplied.
    </p>
  );
}

function AnimatedScore({ target }: { target: number }) {
  const [shown, setShown] = useState(0);
  useEffect(() => {
    let frame: number;
    const start = performance.now();
    const duration = 700;
    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / duration);
      setShown(Math.round(target * (1 - Math.pow(1 - progress, 3))));
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target]);
  return <>{shown}%</>;
}

export function LessonPage() {
  const { lessonId = "" } = useParams();
  return <LessonSession key={lessonId} lessonId={lessonId} />;
}
function LessonSession({ lessonId }: { lessonId: string }) {
  const [search] = useSearchParams();
  const state = useAsync("lesson-" + lessonId, (signal) =>
    request<Lesson>(`/lessons/${idPath(lessonId)}`, { signal }).then(
      normalizeLesson,
    ),
  );
  const assessment = useAsync("quiz-" + lessonId, (signal) =>
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
  const [draft, setDraft] = useState<Draft>(() => readDraft(lessonId));
  const [question, setQuestion] = useState(0),
    [result, setResult] = useState<Attempt | null>(null),
    [busy, setBusy] = useState(""),
    [error, setError] = useState(""),
    [finished, setFinished] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  const patch = (value: Partial<Draft>) =>
    setDraft((d) => ({ ...d, ...value }));
  useEffect(() => {
    try {
      sessionStorage.setItem(
        "meroguru:lesson:" + lessonId,
        JSON.stringify(draft),
      );
    } catch {
      /* Session remains usable when storage is unavailable. */
    }
  }, [draft, lessonId]);
  useEffect(() => {
    heading.current?.focus();
  }, [draft.step, question]);
  const lesson = state.data;
  const completed =
    finished || !!lesson?.completed_at || lesson?.status === "completed";
  const passed = !!assessment.data && draft.passedId === assessment.data.id;
  const unlocked = completed
    ? 3
    : passed
      ? 3
      : draft.practiced
        ? 2
        : draft.learned
          ? 1
          : 0;
  const step = Math.min(draft.step, unlocked);
  const goalId = lesson?.goal_id || search.get("goal") || undefined;
  const back = goalId ? `/goals/${idPath(goalId)}/roadmap` : "/";
  const go = (index: number) => {
    patch({ step: index });
    setError("");
  };
  const quiz = assessment.data;
  const q = quiz?.questions[question];
  const submitQuiz = async (e: FormEvent) => {
    e.preventDefault();
    if (!quiz) return;
    if (
      quiz.questions.some((item) => !draft.answers[item.id]?.trim()) ||
      !draft.confidence
    ) {
      setError(
        "Answer each question and choose your confidence before submitting.",
      );
      return;
    }
    setBusy("quiz");
    setError("");
    try {
      const attempt = await post<Attempt>(
        `/assessments/${idPath(quiz.id)}/attempts`,
        { answers: draft.answers, confidence: Number(draft.confidence) },
      );
      setResult(attempt);
      const success =
        attempt.passed ??
        (attempt.score != null && attempt.score >= (quiz.passing_score ?? 0.7));
      patch({ passedId: success ? quiz.id : undefined });
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Your answers could not be saved.",
      );
    } finally {
      setBusy("");
    }
  };
  const finish = async () => {
    if (!passed || !draft.feedbackSaved || !draft.learned || !draft.practiced)
      return;
    setBusy("complete");
    setError("");
    try {
      await post(`/lessons/${idPath(lessonId)}/complete`);
      setFinished(true);
      try {
        sessionStorage.removeItem("meroguru:lesson:" + lessonId);
      } catch {}
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Your progress could not be saved.",
      );
    } finally {
      setBusy("");
    }
  };
  if (state.loading) return <Loading>Preparing your learning session…</Loading>;
  if (state.error)
    return <ErrorState message={state.error} retry={state.reload} />;
  if (!lesson) return <Empty title="This lesson is not available." />;
  const resources = lesson.resources || [];
  const stageDone = [
    draft.learned,
    draft.practiced,
    passed,
    draft.feedbackSaved,
  ];
  return (
    <div className="guided-session">
      <Link className="text-link" to={back}>
        <ArrowLeft size={16} />
        Back to your roadmap
      </Link>
      <PageHeading
        title={lesson.title || "Your lesson"}
        action={<Time value={lesson.estimated_minutes} />}
      >
        One idea at a time. Build understanding through doing.
      </PageHeading>
      {completed && (
        <div className="session-success" role="status">
          <CheckCircle2 size={25} />
          <div>
            <strong>Lesson completed</strong>
            <p>You can revisit the material or return to your roadmap.</p>
          </div>
          <Link className="button secondary" to={back}>
            View roadmap
          </Link>
        </div>
      )}
      <div className="study-layout">
        <aside className="session-outline" aria-label="Lesson progress">
          <h2>Your session</h2>
          <ol>
            {stages.map((stage, i) => {
              const Icon = stage.icon;
              return (
                <li key={stage.name}>
                  <button
                    className={`stage-button ${step === i ? "selected" : ""}`}
                    aria-current={step === i ? "step" : undefined}
                    disabled={i > unlocked || !!busy}
                    onClick={() => go(i)}
                  >
                    <span className="stage-icon">
                      {stageDone[i] || completed ? (
                        <Check size={18} />
                      ) : i > unlocked ? (
                        <LockKeyhole size={16} />
                      ) : (
                        <Icon size={18} />
                      )}
                    </span>
                    <span>
                      <strong>{stage.name}</strong>
                      <small>{stage.description}</small>
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>
          <progress
            max={4}
            value={completed ? 4 : stageDone.filter(Boolean).length}
            aria-label="Lesson activities completed"
          />
          <p>
            {completed ? 4 : stageDone.filter(Boolean).length} of 4 activities
            complete
          </p>
          <div className="session-objective">
            <Target size={19} />
            <h3>Your objective</h3>
            <p>{lesson.objective || "No objective has been supplied yet."}</p>
          </div>
        </aside>
        <div className="session-workspace">
          <div className="session-section-heading">
            <span>Step {step + 1} of 4</span>
            <h2 tabIndex={-1} ref={heading}>
              {
                [
                  "Let’s explore the idea.",
                  "Make the idea your own.",
                  "Check your understanding.",
                  "Reflect on your session.",
                ][step]
              }
            </h2>
          </div>
          {error && <ErrorState message={error} />}
          {step === 0 && (
            <>
              <div className="study-content">
                {lesson.explanation ? (
                  <Markdown text={lesson.explanation} />
                ) : (
                  <Empty
                    title="The explanation is not ready."
                    action={<button onClick={state.reload}>Check again</button>}
                  />
                )}
              </div>
              {resources.length > 0 && (
                <section className="study-resources">
                  <h3>Go a little deeper</h3>
                  {resources.map((r, i) => (
                    <ResourceLink key={i} resource={r} />
                  ))}
                </section>
              )}
              <details className="source-disclosure">
                <summary>
                  Sources & further reading ({lesson.citations?.length || 0})
                </summary>
                {lesson.citations?.length ? (
                  lesson.citations.map((r, i) => (
                    <ResourceLink key={i} resource={r} />
                  ))
                ) : (
                  <p>No source citations were supplied for this lesson.</p>
                )}
              </details>
              <div className="session-footer">
                <p>Ready to try this yourself?</p>
                <button
                  disabled={!lesson.explanation}
                  onClick={() => {
                    patch({ learned: true, step: 1 });
                  }}
                >
                  Continue to practice
                  <ArrowRight size={17} />
                </button>
              </div>
            </>
          )}
          {step === 1 && (
            <>
              <section className="practice-brief">
                <PencilLine size={24} />
                <h3>Your practice task</h3>
                {lesson.practice_task ? (
                  <Markdown text={lesson.practice_task} />
                ) : (
                  <p>
                    No practice task was supplied. Write down how you would
                    apply the lesson.
                  </p>
                )}
              </section>
              <label htmlFor="practice-notes">Your working notes</label>
              <textarea
                id="practice-notes"
                rows={7}
                value={draft.notes}
                onChange={(e) => patch({ notes: e.target.value })}
                placeholder="Try the task, explain the idea in your own words, or note where you got stuck."
              />
              <p className="field-help">
                Notes stay in this browser tab. They are not graded or sent to
                the AI.
              </p>
              <label className="task-check">
                <input
                  type="checkbox"
                  checked={draft.practiced}
                  onChange={(e) => patch({ practiced: e.target.checked })}
                />
                I’ve attempted the practice task.
              </label>
              <div className="session-footer">
                <button className="secondary" onClick={() => go(0)}>
                  Back to explanation
                </button>
                <button disabled={!draft.practiced} onClick={() => go(2)}>
                  Continue to quiz
                  <ArrowRight size={17} />
                </button>
              </div>
            </>
          )}
          {step === 2 &&
            (assessment.loading ? (
              <Loading>Preparing your questions…</Loading>
            ) : assessment.error ? (
              <ErrorState
                message={assessment.error}
                retry={assessment.reload}
              />
            ) : !quiz?.questions.length ? (
              <Empty
                title="Your quiz isn’t available yet."
                action={
                  <button className="secondary" onClick={assessment.reload}>
                    Check again
                  </button>
                }
              >
                Your reading and practice are saved in this tab. A quiz is
                required to finish this session.
              </Empty>
            ) : result ? (
              <section
                className={`quiz-outcome ${passed ? "passed celebrate" : "review"}`}
              >
                <span className="outcome-score">
                  {result.score == null ? (
                    "Submitted"
                  ) : (
                    <AnimatedScore target={percent(result.score)} />
                  )}
                </span>
                <h3>
                  {passed
                    ? "You’re ready to reflect."
                    : "Let’s give this another look."}
                </h3>
                <p>
                  {passed
                    ? "Your answers met this quiz’s passing score. Mastery builds through evidence over time."
                    : `Review the explanations below, then try again. This quiz requires ${percent(quiz.passing_score ?? 0.7)}% to continue.`}
                </p>
                <div className="answer-review">
                  {quiz.questions.map((item, i) => {
                    const correct = !!result.per_question?.[item.id];
                    return (
                      <article
                        key={item.id}
                        className="review-reveal"
                        style={{ animationDelay: `${i * 80}ms` }}
                      >
                        <span
                          className={
                            correct ? "answer-status correct" : "answer-status"
                          }
                        >
                          {correct ? (
                            <CheckCircle2 size={14} />
                          ) : (
                            <XCircle size={14} />
                          )}
                          {correct ? "Correct" : "Review"}
                        </span>
                        <h4>
                          {i + 1}. {item.prompt}
                        </h4>
                        <p>Your answer: {draft.answers[item.id]}</p>
                        {result.explanations?.[item.id] && (
                          <Markdown text={result.explanations[item.id]} />
                        )}
                      </article>
                    );
                  })}
                </div>
                <div className="session-footer">
                  <button className="secondary" onClick={() => go(0)}>
                    Revisit explanation
                  </button>
                  {passed ? (
                    <button onClick={() => go(3)}>
                      Continue to reflection
                      <ArrowRight size={17} />
                    </button>
                  ) : (
                    <button
                      onClick={() => {
                        setResult(null);
                        setQuestion(0);
                        patch({ answers: {}, confidence: "" });
                      }}
                    >
                      Try the quiz again
                    </button>
                  )}
                </div>
              </section>
            ) : passed ? (
              <div className="quiz-outcome passed">
                <CheckCircle2 />
                <h3>This quiz is complete.</h3>
                <p>Your passing result is saved for this session.</p>
                <button onClick={() => go(3)}>Continue to reflection</button>
              </div>
            ) : (
              <form onSubmit={submitQuiz}>
                <div
                  className="quiz-progress-bar"
                  role="progressbar"
                  aria-valuemin={0}
                  aria-valuemax={quiz.questions.length}
                  aria-valuenow={
                    quiz.questions.filter((item) => draft.answers[item.id])
                      .length
                  }
                >
                  <span
                    style={{
                      width: `${(quiz.questions.filter((item) => draft.answers[item.id]).length / quiz.questions.length) * 100}%`,
                    }}
                  />
                </div>
                <div className="question-track" aria-label="Quiz questions">
                  {quiz.questions.map((item, i) => (
                    <button
                      key={item.id}
                      type="button"
                      className={
                        question === i
                          ? "current"
                          : draft.answers[item.id]
                            ? "answered"
                            : ""
                      }
                      aria-label={`Question ${i + 1}${draft.answers[item.id] ? ", answered" : ""}`}
                      aria-current={question === i ? "step" : undefined}
                      onClick={() => {
                        setQuestion(i);
                        setError("");
                      }}
                      disabled={!!busy}
                    >
                      {draft.answers[item.id] && question !== i ? (
                        <Check size={16} />
                      ) : (
                        i + 1
                      )}
                    </button>
                  ))}
                </div>
                {q && (
                  <fieldset className="guided-question question-enter" key={q.id}>
                    <legend>
                      {question + 1}. {q.prompt}
                    </legend>
                    {q.options?.length ? (
                      q.options.map((option, i) => {
                        const value =
                          typeof option === "string" ? option : option.id;
                        const text =
                          typeof option === "string" ? option : option.text;
                        const selected = draft.answers[q.id] === value;
                        return (
                          <label
                            className={`answer answer-option${selected ? " selected" : ""}`}
                            key={i}
                          >
                            <input
                              type="radio"
                              name={q.id}
                              checked={selected}
                              disabled={!!busy}
                              onChange={() =>
                                patch({
                                  answers: { ...draft.answers, [q.id]: value },
                                })
                              }
                            />
                            <span className="option-letter" aria-hidden="true">
                              {selected ? (
                                <Check size={16} />
                              ) : (
                                String.fromCharCode(65 + i)
                              )}
                            </span>
                            <span>{text}</span>
                          </label>
                        );
                      })
                    ) : (
                      <>
                        <label htmlFor="short-answer">Your answer</label>
                        <textarea
                          id="short-answer"
                          rows={4}
                          value={draft.answers[q.id] || ""}
                          disabled={!!busy}
                          onChange={(e) =>
                            patch({
                              answers: {
                                ...draft.answers,
                                [q.id]: e.target.value,
                              },
                            })
                          }
                        />
                      </>
                    )}
                  </fieldset>
                )}
                {question === quiz.questions.length - 1 && (
                  <div className="quiz-confidence">
                    <label htmlFor="quiz-confidence">
                      How confident are you in your answers?
                    </label>
                    <select
                      id="quiz-confidence"
                      value={draft.confidence}
                      disabled={!!busy}
                      onChange={(e) => patch({ confidence: e.target.value })}
                    >
                      <option value="">Choose your confidence</option>
                      <option value="0.25">Still unsure</option>
                      <option value="0.5">Somewhat confident</option>
                      <option value="0.75">Confident</option>
                      <option value="1">Very confident</option>
                    </select>
                    <p className="field-help">
                      There’s no right confidence level. An honest answer helps
                      put your result in context.
                    </p>
                  </div>
                )}
                <div className="session-footer">
                  <button
                    className="secondary"
                    type="button"
                    disabled={!!busy}
                    onClick={() =>
                      question ? setQuestion(question - 1) : go(1)
                    }
                  >
                    {question ? "Previous question" : "Back to practice"}
                  </button>
                  {question < quiz.questions.length - 1 ? (
                    <button
                      type="button"
                      disabled={!q || !draft.answers[q.id]?.trim() || !!busy}
                      onClick={() => setQuestion(question + 1)}
                    >
                      Next question
                      <ArrowRight size={17} />
                    </button>
                  ) : (
                    <button
                      disabled={
                        !!busy ||
                        !draft.confidence ||
                        quiz.questions.some(
                          (item) => !draft.answers[item.id]?.trim(),
                        )
                      }
                    >
                      {busy === "quiz"
                        ? "Checking answers…"
                        : "Check my answers"}
                    </button>
                  )}
                </div>
              </form>
            ))}
          {step === 3 && (
            <>
              <Reflection
                lessonId={lessonId}
                saved={draft.feedbackSaved}
                onSaved={() => patch({ feedbackSaved: true })}
              />
              <div className="completion-guide">
                <h3>What happens next?</h3>
                <p>
                  Your quiz result updates your learning history. Additional AI
                  support may be analyzed in the background. Your roadmap shows
                  your next available lesson and any concepts to revisit.
                </p>
              </div>
              <div className="session-footer">
                <Link className="text-link" to={back}>
                  Return to roadmap
                </Link>
                <button
                  disabled={
                    !!busy ||
                    completed ||
                    !passed ||
                    !draft.feedbackSaved ||
                    !draft.learned ||
                    !draft.practiced
                  }
                  onClick={() => void finish()}
                >
                  {completed
                    ? "Lesson completed"
                    : busy === "complete"
                      ? "Saving progress…"
                      : "Complete lesson"}
                  <CheckCircle2 size={18} />
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
function Reflection({
  lessonId,
  saved,
  onSaved,
}: {
  lessonId: string;
  saved: boolean;
  onSaved: () => void;
}) {
  const [difficulty, setDifficulty] = useState(""),
    [usefulness, setUsefulness] = useState(""),
    [confidence, setConfidence] = useState(""),
    [minutes, setMinutes] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await post(`/lessons/${idPath(lessonId)}/feedback`, {
        difficulty,
        usefulness: Number(usefulness),
        confidence: Number(confidence),
        time_spent_minutes: Number(minutes),
      });
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Feedback could not be saved.");
    } finally {
      setBusy(false);
    }
  };
  return saved ? (
    <div className="reflection-saved" role="status">
      <CheckCircle2 size={28} />
      <h3>Your reflection is saved.</h3>
      <p>
        You’ve worked through the session. Save its completion to update your
        roadmap.
      </p>
    </div>
  ) : (
    <form onSubmit={submit}>
      <p>
        Notice what clicked and what took effort. Your reflection becomes part
        of your learning history.
      </p>
      <fieldset>
        <legend>How did this lesson feel?</legend>
        <div className="reflection-options">
          {[
            ["too_easy", "Too easy"],
            ["just_right", "About right"],
            ["too_difficult", "Challenging"],
          ].map(([value, label]) => (
            <label className="choice" key={value}>
              <input
                type="radio"
                name="difficulty"
                required
                checked={difficulty === value}
                disabled={busy}
                onChange={() => setDifficulty(value)}
              />
              {label}
            </label>
          ))}
        </div>
      </fieldset>
      <div className="form-grid">
        <div>
          <label htmlFor="usefulness">How useful was it?</label>
          <select
            id="usefulness"
            required
            value={usefulness}
            disabled={busy}
            onChange={(e) => setUsefulness(e.target.value)}
          >
            <option value="">Choose usefulness</option>
            {[
              "Not useful",
              "Slightly useful",
              "Somewhat useful",
              "Useful",
              "Very useful",
            ].map((s, i) => (
              <option key={s} value={i + 1}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="reflection-confidence">
            Confidence after practice
          </label>
          <select
            id="reflection-confidence"
            required
            value={confidence}
            disabled={busy}
            onChange={(e) => setConfidence(e.target.value)}
          >
            <option value="">Choose confidence</option>
            <option value="0.25">Still unsure</option>
            <option value="0.5">Somewhat confident</option>
            <option value="0.75">Confident</option>
            <option value="1">Very confident</option>
          </select>
        </div>
      </div>
      <label htmlFor="time-spent">Time spent (minutes)</label>
      <input
        id="time-spent"
        type="number"
        min={1}
        max={1440}
        step={1}
        required
        value={minutes}
        disabled={busy}
        onChange={(e) => setMinutes(e.target.value)}
      />
      {error && <ErrorState message={error} />}
      <div className="button-row">
        <button className="secondary" disabled={busy}>
          {busy ? "Saving…" : "Save reflection"}
        </button>
      </div>
    </form>
  );
}
