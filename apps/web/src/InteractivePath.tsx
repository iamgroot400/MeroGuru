import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Check, BookOpen } from "lucide-react";
import type { Concept, LessonSummary, Mastery } from "./api/types";
import { Badge, Empty, Time } from "./components";
import { isComplete, lessonConcepts, lessonUrl, sortLessons } from "./learning";
import { Recommendation } from "./Recommendation";

export function InteractivePath({
  goalId,
  lessons,
  concepts,
  mastery,
}: {
  goalId: string;
  lessons: LessonSummary[];
  concepts: Concept[];
  mastery: Mastery | null;
}) {
  const ordered = sortLessons(lessons),
    next = ordered.find((l) => !isComplete(l));
  const [selected, setSelected] = useState(next?.id || ordered[0]?.id);
  const lesson = ordered.find((l) => l.id === selected) || next || ordered[0];
  const covers = lesson ? lessonConcepts(lesson, concepts) : [];
  return (
    <>
      <Recommendation
        goalId={goalId}
        lessons={lessons}
        concepts={concepts}
        mastery={mastery}
      />
      <div className="path-layout">
        <section>
          <div className="section-heading">
            <h2>Your learning pathway</h2>
            <span className="muted">
              {ordered.filter(isComplete).length} of {ordered.length} lessons
              complete
            </span>
          </div>
          <p className="muted">
            Select a milestone to explore the lesson. Return to completed
            lessons whenever you need.
          </p>
          {ordered.length ? (
            <ol className="milestone-list">
              {ordered.map((l, i) => (
                <li
                  key={l.id}
                  className={
                    isComplete(l) ? "done" : l.id === next?.id ? "current" : ""
                  }
                >
                  <button
                    className="milestone"
                    aria-pressed={lesson?.id === l.id}
                    onClick={() => setSelected(l.id)}
                  >
                    <span className="milestone-number">
                      {isComplete(l) ? (
                        <Check size={20} />
                      ) : (
                        String(i + 1).padStart(2, "0")
                      )}
                    </span>
                    <span className="milestone-copy">
                      <small>
                        {isComplete(l)
                          ? "Completed"
                          : l.id === next?.id
                            ? "Up next"
                            : "Coming up"}
                      </small>
                      <strong>{l.title}</strong>
                      <Time value={l.estimated_minutes} />
                    </span>
                    <ArrowRight size={18} />
                  </button>
                </li>
              ))}
            </ol>
          ) : (
            <Empty title="Your lessons are being prepared.">
              The concept map is ready. Check again when the plan finishes.
            </Empty>
          )}
        </section>
        {lesson && (
          <aside className="path-preview" aria-label="Selected lesson preview">
            <span className="eyebrow">Lesson preview</span>
            <BookOpen size={30} />
            <h2>{lesson.title}</h2>
            <Time value={lesson.estimated_minutes} />
            <p>
              Learn the idea, try a practice task, check your understanding, and
              reflect on your session.
            </p>
            <h3>What you’ll explore</h3>
            {covers.length ? (
              <ul>
                {covers.map((c) => (
                  <li key={c.id}>{c.title}</li>
                ))}
              </ul>
            ) : (
              <p className="muted">
                Concept details have not been linked to this lesson yet.
              </p>
            )}
            <Link className="button" to={lessonUrl(lesson.id, goalId)}>
              {isComplete(lesson) ? "Revisit lesson" : "Open lesson"}
              <ArrowRight size={17} />
            </Link>
            <small>
              Your progress is saved as you work through the session in this
              tab.
            </small>
          </aside>
        )}
      </div>
      <section className="concept-library">
        <h2>The ideas behind your path</h2>
        <p className="muted">Open a concept to see what it builds on.</p>
        {concepts.map((c) => (
          <details key={c.id}>
            <summary>
              <span>{c.title}</span>
              <Badge
                state={
                  mastery?.concepts.find((m) => m.concept_id === c.id)
                    ?.mastery_state ||
                  c.mastery_state ||
                  "not_started"
                }
              />
            </summary>
            <p>{c.description || "No description supplied."}</p>
            <p className="muted">
              {c.prerequisite_ids.length
                ? "Builds on: " +
                  c.prerequisite_ids
                    .map((id) => concepts.find((x) => x.id === id)?.title || id)
                    .join(", ")
                : "No prerequisites — a starting point."}
            </p>
          </details>
        ))}
      </section>
    </>
  );
}
