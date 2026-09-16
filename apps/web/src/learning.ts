import type { Concept, LessonSummary, Mastery } from "./api/types";

export const isComplete = (lesson: LessonSummary) =>
  !!lesson.completed_at || lesson.status === "completed";
export const lessonUrl = (lessonId: string, goalId?: string) =>
  `/lessons/${encodeURIComponent(lessonId)}${goalId ? "?goal=" + encodeURIComponent(goalId) : ""}`;
export function sortLessons(lessons: LessonSummary[]) {
  return [...lessons].sort(
    (a, b) =>
      (a.sequence_number ?? 0) - (b.sequence_number ?? 0) ||
      (a.scheduled_date || "").localeCompare(b.scheduled_date || ""),
  );
}
export function lessonConcepts(lesson: LessonSummary, concepts: Concept[]) {
  return concepts.filter((c) =>
    (lesson.concept_ids || []).some(
      (key) => key === c.id || key === c.external_key,
    ),
  );
}
export function nextStep(
  lessons: LessonSummary[],
  concepts: Concept[],
  mastery: Mastery | null | undefined,
) {
  const ordered = sortLessons(lessons);
  const review = (mastery?.concepts || [])
    .filter((c) => c.mastery_state === "needs_review")
    .sort((a, b) => (a.mastery_score ?? 0) - (b.mastery_score ?? 0));
  for (const record of review) {
    const concept = concepts.find((c) => c.id === record.concept_id);
    const lesson = ordered.find((l) =>
      lessonConcepts(l, concepts).some((c) => c.id === record.concept_id),
    );
    if (lesson)
      return {
        lesson,
        kind: "review" as const,
        title: "A little review will help.",
        reason: `${concept?.title || "This concept"} is marked for review in your learning history. Revisit the explanation and practice before moving on.`,
      };
  }
  const lesson = ordered.find((l) => !isComplete(l));
  if (lesson)
    return {
      lesson,
      kind: "continue" as const,
      title: "Your next small step.",
      reason:
        "This is the first unfinished lesson in your current plan. Work through its activities, then check your understanding.",
    };
  return null;
}
