import { useMemo, useState, type ReactNode } from "react";
import { BookOpen, Clock3, LoaderCircle, Monitor, Moon, Sprout, Sun } from "lucide-react";
import { Link } from "react-router-dom";
import DOMPurify from "dompurify";
import { marked } from "marked";
import type { LessonSummary } from "./api/types";
import { minutes } from "./utils";

type ThemeChoice = "light" | "dark" | "system";
const THEME_KEY = "meroguru:theme";

function applyTheme(choice: ThemeChoice) {
  const root = document.documentElement;
  if (choice === "system") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", choice);
}
function readStoredTheme(): ThemeChoice {
  try {
    const value = localStorage.getItem(THEME_KEY);
    if (value === "light" || value === "dark" || value === "system") return value;
  } catch {
    /* Falls back to system theme for this session. */
  }
  return "system";
}
export function ThemeToggle() {
  const [theme, setTheme] = useState<ThemeChoice>(() => {
    const initial = readStoredTheme();
    applyTheme(initial);
    return initial;
  });
  const cycle = () => {
    const next: ThemeChoice = theme === "system" ? "light" : theme === "light" ? "dark" : "system";
    setTheme(next);
    applyTheme(next);
    try {
      localStorage.setItem(THEME_KEY, next);
    } catch {
      /* Choice still applies for this session without storage. */
    }
  };
  const Icon = theme === "light" ? Sun : theme === "dark" ? Moon : Monitor;
  const label = theme === "light" ? "Light" : theme === "dark" ? "Dark" : "System";
  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={cycle}
      aria-label={`Theme: ${label}. Click to switch.`}
    >
      <Icon size={17} aria-hidden="true" />
      <span>{label}</span>
    </button>
  );
}

marked.setOptions({ breaks: true });

// AI-generated lesson content is Markdown; render it as real structure (headings,
// bold, code blocks, lists) rather than a flat text block. Sanitized because the
// text ultimately comes from a model response, not a hardcoded template.
export function Markdown({ text }: { text: string }) {
  const html = useMemo(() => {
    const parsed = marked.parse(text || "", { async: false }) as string;
    return DOMPurify.sanitize(parsed);
  }, [text]);
  return <div className="prose markdown" dangerouslySetInnerHTML={{ __html: html }} />;
}

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
  const tone =
    state === "mastered" || state === "completed"
      ? "success"
      : state === "up_next"
        ? "accent"
        : "";
  return <span className={`badge ${tone}`}>{state.replaceAll("_", " ")}</span>;
}
