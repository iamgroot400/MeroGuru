import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { LoaderCircle } from "lucide-react";
import { idPath, optional, post, request } from "../api/client";
import type { Concept, Goal, Job, Mastery } from "../api/types";
import { useAsync } from "../hooks";
import { useGoals } from "../context";
import {
  Badge,
  Empty,
  ErrorState,
  Loading,
  MasteryBar,
  PageHeading,
  Time,
} from "../components";
import { orderedConcepts, percent } from "../utils";
import { normalizeConcepts } from "../api/adapters";

function readJob(goalId: string) {
  try {
    return sessionStorage.getItem(`meroguru:job:${goalId}`) || "";
  } catch {
    return "";
  }
}
function storeJob(goalId: string, jobId: string) {
  try {
    if (jobId) sessionStorage.setItem(`meroguru:job:${goalId}`, jobId);
    else sessionStorage.removeItem(`meroguru:job:${goalId}`);
  } catch {
    /* Polling still works without storage. */
  }
}
export function GoalPage({ mode }: { mode: "roadmap" | "progress" }) {
  const { goalId = "" } = useParams();
  return <GoalDetail key={goalId} goalId={goalId} mode={mode} />;
}
function GoalDetail({
  goalId,
  mode,
}: {
  goalId: string;
  mode: "roadmap" | "progress";
}) {
  const path = `/goals/${idPath(goalId)}`,
    location = useLocation(),
    navigate = useNavigate(),
    goals = useGoals();
  const [jobId, setJobId] = useState(() => readJob(goalId)),
    [job, setJob] = useState<Job | null>(null),
    [error, setError] = useState(""),
    [starting, setStarting] = useState(false),
    [pollRevision, setPollRevision] = useState(0);
  const didAutoStart = useRef(false),
    requestInFlight = useRef(false);
  const state = useAsync(path, async (signal) => {
    const goal = await request<Goal>(path, { signal });
    const [map, mastery] = await Promise.all([
      optional<Concept[] | { concepts: Concept[] }>(
        `${path}/concept-map`,
        signal,
      ),
      optional<Mastery | Mastery["concepts"]>(`${path}/mastery`, signal),
    ]);
    return {
      goal,
      concepts: orderedConcepts(normalizeConcepts(map)),
      mastery: Array.isArray(mastery) ? { concepts: mastery } : mastery,
    };
  });
  const reload = state.reload,
    reloadGoals = goals.reload;
  const callbacks = useRef({ reload, reloadGoals });
  callbacks.current = { reload, reloadGoals };
  const start = async () => {
    if (requestInFlight.current) return;
    requestInFlight.current = true;
    setStarting(true);
    setError("");
    try {
      const result = await post<Job>(`${path}/generate-plan`);
      const id = result.job_id || result.id;
      if (!id)
        throw new Error(
          "The API did not return a job ID. Refresh the roadmap before trying again.",
        );
      setJob(result);
      setJobId(id);
      storeJob(goalId, id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start your plan.");
    } finally {
      setStarting(false);
      requestInFlight.current = false;
    }
  };
  useEffect(() => {
    if (location.state?.startGeneration && !didAutoStart.current) {
      didAutoStart.current = true;
      navigate(location.pathname, { replace: true, state: null });
      void start();
    }
    // One automatic POST per newly-created goal, including StrictMode re-renders.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    if (!jobId && state.data?.goal.job_id && !job) {
      setJobId(state.data.goal.job_id);
      storeJob(goalId, state.data.goal.job_id);
    }
  }, [state.data, jobId, job, goalId]);
  useEffect(() => {
    if (!jobId) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const next = await request<Job>(`/jobs/${idPath(jobId)}`, {
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        setJob(next);
        setError("");
        if (next.status === "completed" || next.status === "failed") {
          storeJob(goalId, "");
          setJobId("");
          callbacks.current.reload();
          callbacks.current.reloadGoals();
        } else timer = setTimeout(poll, 2000);
      } catch (e) {
        if (!controller.signal.aborted)
          setError(
            e instanceof Error ? e.message : "Could not check your plan.",
          );
      }
    };
    void poll();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [jobId, goalId, pollRevision]);
  if (state.loading) return <Loading>Opening your {mode}…</Loading>;
  if (state.error)
    return <ErrorState message={state.error} retry={state.reload} />;
  if (!state.data) return null;
  const { goal, concepts, mastery } = state.data;
  const statusFor = (c: Concept) =>
    mastery?.concepts.find((m) => m.concept_id === c.id)?.mastery_state ||
    c.mastery_state ||
    "not_started";
  const mastered = concepts.filter((c) => statusFor(c) === "mastered").length;
  const generating = starting || !!jobId;
  return (
    <>
      <PageHeading
        title={
          mode === "roadmap"
            ? "Your path to understanding."
            : "Look how far you’re getting."
        }
      >
        {goal.title}
      </PageHeading>
      <nav className="tabs" aria-label="Goal views">
        <Link
          aria-current={mode === "roadmap" ? "page" : undefined}
          to={`${path}/roadmap`}
        >
          Roadmap
        </Link>
        <Link
          aria-current={mode === "progress" ? "page" : undefined}
          to={`${path}/progress`}
        >
          Progress
        </Link>
      </nav>
      {generating && (
        <div className="generation" role="status">
          <LoaderCircle className="spinner" />
          <div>
            <h2>
              {job?.status === "running"
                ? "Building a path that fits you…"
                : "Your roadmap is on its way…"}
            </h2>
            <p>
              This usually takes 10–30 seconds. You can keep exploring; this
              page will update when it’s ready.
            </p>
          </div>
        </div>
      )}
      {error && (
        <ErrorState
          message={error}
          retry={
            jobId
              ? () => {
                  setError("");
                  setPollRevision((v) => v + 1);
                }
              : undefined
          }
        />
      )}
      {job?.status === "failed" && (
        <ErrorState
          message="Your plan could not be generated. Check your provider connection in Settings, then try again."
          retry={() => void start()}
        />
      )}
      {!concepts.length ? (
        !generating && (
          <Empty
            title="Every learning journey starts with a path."
            action={
              <button disabled={starting} onClick={() => void start()}>
                Generate roadmap
              </button>
            }
          >
            Your goal is saved. Generate a roadmap to break it into concepts and
            daily lessons.
          </Empty>
        )
      ) : (
        <>
          <div className="progress-summary">
            <MasteryBar mastered={mastered} total={concepts.length} />
            <p>
              {goal.minutes_per_day} minutes per study day
              <br />
              <span className="muted">A pace you chose for yourself.</span>
            </p>
          </div>
          {mode === "roadmap" ? (
            <ol className="roadmap-list">
              {concepts.map((c) => (
                <li key={c.id}>
                  <div className="concept-content">
                    <div className="section-heading">
                      <h2>{c.title}</h2>
                      <Badge state={statusFor(c)} />
                    </div>
                    <p>{c.description}</p>
                    <div className="concept-meta">
                      <Time value={c.estimated_minutes} />
                      <span>
                        {c.prerequisite_ids?.length
                          ? `Builds on: ${c.prerequisite_ids.map((id) => concepts.find((item) => item.id === id)?.title || id).join(", ")}`
                          : "No prerequisites — start here"}
                      </span>
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          ) : (
            <>
              <section>
                <h2>Understanding, concept by concept</h2>
                <div className="mastery-list">
                  {concepts.map((c) => {
                    const record = mastery?.concepts.find(
                      (m) => m.concept_id === c.id,
                    );
                    return (
                      <article key={c.id}>
                        <div className="section-heading">
                          <h3>{c.title}</h3>
                          <Badge state={statusFor(c)} />
                        </div>
                        {record?.mastery_score != null ? (
                          <div className="score-line">
                            <progress
                              aria-label={`${c.title} mastery`}
                              max={100}
                              value={percent(record.mastery_score)}
                            />
                            <span>{percent(record.mastery_score)}%</span>
                          </div>
                        ) : (
                          <p className="muted">
                            No mastery score recorded yet.
                          </p>
                        )}
                      </article>
                    );
                  })}
                </div>
              </section>
              <section className="history">
                <h2>Assessment history</h2>
                {mastery?.assessment_history?.length ? (
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th scope="col">Assessment</th>
                          <th scope="col">Date</th>
                          <th scope="col">Score</th>
                        </tr>
                      </thead>
                      <tbody>
                        {mastery.assessment_history.map((attempt) => (
                          <tr key={attempt.id}>
                            <th scope="row">
                              {attempt.title || "Lesson assessment"}
                            </th>
                            <td>
                              {attempt.created_at
                                ? new Date(
                                    attempt.created_at,
                                  ).toLocaleDateString()
                                : "Not supplied"}
                            </td>
                            <td>
                              {attempt.score == null
                                ? "Awaiting score"
                                : `${percent(attempt.score)}%`}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <Empty title="Your understanding will show up here.">
                    {mastery?.assessment_history
                      ? "Complete a lesson quiz to record your first assessment."
                      : "No assessment history was supplied by the API yet. Your quiz results appear in each lesson."}
                  </Empty>
                )}
              </section>
            </>
          )}
        </>
      )}
    </>
  );
}
