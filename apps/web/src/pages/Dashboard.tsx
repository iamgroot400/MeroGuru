import { Link } from "react-router-dom";
import { ArrowUpRight, Plus, Sprout } from "lucide-react";
import { useGoals } from "../context";
import { useAsync } from "../hooks";
import { optional, request, idPath } from "../api/client";
import type { Goal, LessonSummary, Plan } from "../api/types";
import {
  Badge,
  Empty,
  ErrorState,
  LessonLink,
  Loading,
  PageHeading,
  Time,
} from "../components";
import { completedInWeek, dayKey, weekDates } from "../utils";

function CurrentStudy({ goal }: { goal: Goal }) {
  const state = useAsync(
    `study-${goal.id}-${goal.plan_id}-${goal.active_plan_id}`,
    async (signal) => {
      const full = await request<Goal>(`/goals/${idPath(goal.id)}`, { signal });
      const planId = full.active_plan_id || full.plan_id;
      if (!planId) return null;
      const [plan, today] = await Promise.all([
        request<Plan>(`/plans/${idPath(planId)}`, { signal }),
        optional<
          LessonSummary | LessonSummary[] | { lessons: LessonSummary[] }
        >(`/plans/${idPath(planId)}/today`, signal),
      ]);
      return {
        plan,
        today: !today
          ? []
          : Array.isArray(today)
            ? today
            : "lessons" in today
              ? today.lessons
              : [today],
      };
    },
  );
  if (state.loading) return <Loading>Finding today’s lesson…</Loading>;
  if (state.error)
    return <ErrorState message={state.error} retry={state.reload} />;
  if (!state.data)
    return (
      <Empty
        title="Your next step: a learning roadmap"
        action={
          <Link className="button" to={`/goals/${idPath(goal.id)}/roadmap`}>
            Open roadmap
          </Link>
        }
      >
        Generate a plan to turn this goal into manageable lessons.
      </Empty>
    );
  const completed = completedInWeek(state.data.plan.lessons || []);
  const hasCompletionDates = !state.data.plan.lessons.some(
    (l) => l.status === "completed" && !l.completed_at,
  );
  return (
    <div className="dashboard-grid">
      <section className="today-panel">
        <div className="section-heading">
          <h2>Today’s lesson</h2>
          <span className="badge">{goal.title}</span>
        </div>
        {state.data.today.length ? (
          state.data.today.map((lesson) => (
            <div className="today-lesson" key={lesson.id}>
              <Time value={lesson.estimated_minutes} />
              <h3>{lesson.title || "Your next lesson"}</h3>
              <p>One focused session. One step closer to your goal.</p>
              <Link className="button" to={`/lessons/${idPath(lesson.id)}`}>
                {lesson.status === "completed"
                  ? "Review lesson"
                  : "Start learning"}
                <ArrowUpRight size={18} />
              </Link>
            </div>
          ))
        ) : (
          <Empty title="A little breathing room">
            No lesson is scheduled for today. Explore your roadmap or come back
            on your next study day.
          </Empty>
        )}
      </section>
      <section className="week-panel">
        <h2>This week</h2>
        <p className="week-count">
          <strong>{hasCompletionDates ? completed.length : "—"}</strong>{" "}
          {hasCompletionDates
            ? completed.length === 1
              ? "lesson completed"
              : "lessons completed"
            : "Completion dates unavailable"}
        </p>
        <div className="week-days">
          {weekDates().map((date) => {
            const key = dayKey(date);
            const count = completed.filter(
              (l) => dayKey(new Date(l.completed_at!)) === key,
            ).length;
            return (
              <div
                key={key}
                className={key === dayKey(new Date()) ? "is-today" : ""}
              >
                <span>
                  {date
                    .toLocaleDateString(undefined, { weekday: "short" })
                    .slice(0, 1)}
                </span>
                <span
                  className={`day-circle ${count ? "done" : ""}`}
                  aria-label={`${date.toLocaleDateString()}: ${count} lessons completed`}
                >
                  {count ? "✓" : date.getDate()}
                </span>
              </div>
            );
          })}
        </div>
        <p className="muted">
          {hasCompletionDates
            ? "Completed lessons for this goal, Monday through Sunday."
            : "The API has not supplied dates for completed lessons, so a weekly total is not available."}
        </p>
        <Link className="text-link" to={`/goals/${idPath(goal.id)}/progress`}>
          See your progress
        </Link>
      </section>
      {state.data.plan.warnings?.map((warning, i) => (
        <p className="notice full-width" key={i}>
          {warning}
        </p>
      ))}
      <section className="full-width">
        <h2>On your learning path</h2>
        {state.data.plan.lessons?.length ? (
          state.data.plan.lessons
            .filter((l) => l.status !== "completed" && !l.completed_at)
            .slice(0, 3)
            .map((lesson) => <LessonLink key={lesson.id} lesson={lesson} />)
        ) : (
          <p className="muted">Your plan has no lessons yet.</p>
        )}
      </section>
    </div>
  );
}
export function Dashboard() {
  const goals = useGoals();
  const active =
    goals.data?.filter((g) => !g.status || g.status === "active") || [];
  return (
    <>
      <PageHeading
        title="Keep your curiosity going."
        action={
          <Link className="button" to="/goals/new">
            <Plus size={18} />
            New goal
          </Link>
        }
      >
        Small steps add up. Let’s make space for one today.
      </PageHeading>
      {goals.loading ? (
        <Loading />
      ) : goals.error ? (
        <ErrorState message={goals.error} retry={goals.reload} />
      ) : !goals.data?.length ? (
        <section className="welcome">
          <div>
            <Sprout size={38} />
            <h2>What have you always wanted to learn?</h2>
            <p>
              Start with a goal. MeroGuru will help you find a path, build
              understanding, and fit learning into your day.
            </p>
            <Link className="button" to="/goals/new">
              Create your first goal
            </Link>
            <Link className="text-link setup-link" to="/settings">
              Set up your AI provider
            </Link>
          </div>
          <div className="learning-sketch" aria-hidden="true">
            <span>Start with curiosity</span>
            <i />
            <span>Build understanding</span>
            <i />
            <span>Make it your own</span>
          </div>
        </section>
      ) : (
        <>
          {goals.current && (
            <CurrentStudy key={goals.current.id} goal={goals.current} />
          )}
          <section className="goals-section">
            <div className="section-heading">
              <h2>Your active goals</h2>
              <span className="muted">
                {active.length} {active.length === 1 ? "goal" : "goals"}
              </span>
            </div>
            {!active.length ? (
              <Empty title="No active goals">
                Create a new goal when you’re ready for your next chapter.
              </Empty>
            ) : (
              <div className="goals-grid">
                {active.map((goal) => (
                  <article className="goal-card" key={goal.id}>
                    <Badge state={goal.starting_level} />
                    <h3>
                      <Link to={`/goals/${idPath(goal.id)}/roadmap`}>
                        {goal.title}
                      </Link>
                    </h3>
                    <p>{goal.description || "Your personal learning path."}</p>
                    <div className="goal-meta">
                      <Time value={goal.minutes_per_day} />
                      <span>per study day</span>
                    </div>
                    <Link
                      className="text-link"
                      to={`/goals/${idPath(goal.id)}/roadmap`}
                    >
                      Explore roadmap
                    </Link>
                  </article>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </>
  );
}
