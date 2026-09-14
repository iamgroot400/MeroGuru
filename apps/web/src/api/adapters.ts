import type { Concept, Lesson } from "./types";

export function normalizeConcepts(
  map: Concept[] | { concepts: Concept[] } | null,
): Concept[] {
  const concepts = Array.isArray(map) ? map : map?.concepts || [];
  return concepts.map((c) => ({
    ...c,
    prerequisite_ids:
      c.prerequisite_ids ||
      (c.prerequisite_keys || []).map(
        (key) => concepts.find((p) => p.external_key === key)?.id || key,
      ),
  }));
}
export function normalizeLesson(lesson: Lesson): Lesson {
  const activities = lesson.activities || [];
  return {
    ...lesson,
    explanation:
      lesson.explanation ||
      activities
        .filter((a) => a.activity_type === "explanation")
        .map((a) => a.instructions)
        .join("\n\n"),
    practice_task:
      lesson.practice_task ||
      activities
        .filter((a) => a.activity_type === "practice")
        .map((a) => a.instructions)
        .join("\n\n"),
    resources:
      lesson.resources ||
      (lesson.resource
        ? [lesson.resource]
        : activities
            .filter((a) => a.activity_type === "resource")
            .flatMap((a) => {
              const url = a.instructions.match(/https?:\/\/[^\s<>]+/)?.[0];
              return url ? [{ title: a.title, url }] : [];
            })),
  };
}
