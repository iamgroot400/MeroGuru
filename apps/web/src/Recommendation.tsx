import { Link } from "react-router-dom";
import { Compass, ArrowUpRight } from "lucide-react";
import type { Concept, LessonSummary, Mastery } from "./api/types";
import { lessonUrl, nextStep } from "./learning";
import { Time } from "./components";

export function Recommendation({
  goalId,
  lessons,
  concepts,
  mastery,
}: {
  goalId: string;
  lessons: LessonSummary[];
  concepts: Concept[];
  mastery?: Mastery | null;
}) {
  const next = nextStep(lessons, concepts, mastery);
  if (!next)
    return (
      <aside className="learning-guide" aria-label="Recommended next step">
        <Compass size={25} />
        <div>
          <h2>
            {lessons.length
              ? "You’ve reached the end of this plan."
              : "Your next step will appear here."}
          </h2>
          <p>
            {lessons.length
              ? "Revisit a concept or create a new goal when you’re ready."
              : "Generate your roadmap to begin."}
          </p>
        </div>
      </aside>
    );
  return (
    <aside
      className={`learning-guide ${next.kind}`}
      aria-label="Recommended next step"
    >
      <Compass size={25} aria-hidden="true" />
      <div>
        <span className="guide-label">Recommended next step</span>
        <h2>{next.title}</h2>
        <p>{next.reason}</p>
        <details>
          <summary>Why this recommendation?</summary>
          <p>
            {next.kind === "review"
              ? "Your stored mastery state indicates that this concept needs review. This recommendation uses that evidence; it is not a prediction of your future score."
              : "Your plan’s sequence and recorded lesson completions determine this suggestion. More assessment evidence will help identify topics to revisit."}
          </p>
        </details>
        <Link className="button" to={lessonUrl(next.lesson.id, goalId)}>
          {next.kind === "review" ? "Review this lesson" : "Continue learning"}
          <ArrowUpRight size={18} />
        </Link>
        <Time value={next.lesson.estimated_minutes} />
      </div>
    </aside>
  );
}
