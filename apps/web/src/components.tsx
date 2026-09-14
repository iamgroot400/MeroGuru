import type { ReactNode } from "react";
import { BookOpen, Clock3, LoaderCircle, Sprout } from "lucide-react";
import { Link } from "react-router-dom";
import type { LessonSummary } from "./api/types";
import { minutes } from "./utils";

export function Loading({
  children = "Opening your learning space…",
}: {
  children?: ReactNode;
}) {
  return (
    <div className="state" role="status">
      <LoaderCircle className="spinner" size={26} />
      <p>{children}</p>
    </div>
  );
}
export function ErrorState({
  message,
  retry,
}: {
  message: string;
  retry?: () => void;
}) {
  return (
    <div className="error" role="alert">
      <p>{message}</p>
      {retry && (
        <button className="secondary" onClick={retry}>
          Try again
        </button>
      )}
    </div>
  );
}
export function Empty({
  title,
  children,
  action,
}: {
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <Sprout size={32} aria-hidden="true" />
      <h3>{title}</h3>
      <p>{children}</p>
      {action}
    </div>
  );
}
export function PageHeading({
  title,
  children,
  action,
}: {
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <header className="page-heading">
      <div>
        <h1>{title}</h1>
        {children && <p>{children}</p>}
      </div>
      {action}
    </header>
  );
}
export function Time({ value }: { value?: number }) {
  return (
    <span className="time">
      <Clock3 size={16} aria-hidden="true" />
      {minutes(value)}
    </span>
  );
}
export function LessonLink({ lesson }: { lesson: LessonSummary }) {
  return (
    <Link
      className="lesson-link"
      to={`/lessons/${encodeURIComponent(lesson.id)}`}
    >
      <BookOpen size={22} aria-hidden="true" />
      <span>
        <strong>{lesson.title || "Your next lesson"}</strong>
        <Time value={lesson.estimated_minutes} />
      </span>
      <span className="text-link">Open lesson</span>
    </Link>
  );
}
export function MasteryBar({
  mastered,
  total,
}: {
  mastered: number;
  total: number;
}) {
  return (
    <div className="mastery">
      <p>
        <strong>
          {mastered} of {total}
        </strong>{" "}
        concepts mastered
      </p>
      <progress
        aria-label={`${mastered} of ${total} concepts mastered`}
        value={mastered}
        max={Math.max(total, 1)}
      />
    </div>
  );
}
export function Badge({ state = "not_started" }: { state?: string }) {
  return (
    <span
      className={`badge ${state === "mastered" || state === "completed" ? "success" : ""}`}
    >
      {state.replaceAll("_", " ")}
    </span>
  );
}
