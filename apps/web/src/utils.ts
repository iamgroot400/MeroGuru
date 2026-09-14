import type { Concept, LessonSummary } from "./api/types";
export function minutes(value?: number) {
  return value != null ? `${value} min` : "Time estimate pending";
}
export function dayKey(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}
export function weekDates(now = new Date()) {
  const monday = new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate() - ((now.getDay() + 6) % 7),
  );
  return Array.from(
    { length: 7 },
    (_, i) =>
      new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + i),
  );
}
export function completedInWeek(lessons: LessonSummary[], now = new Date()) {
  const days = weekDates(now).map(dayKey);
  return lessons.filter(
    (l) => l.completed_at && days.includes(dayKey(new Date(l.completed_at))),
  );
}
export function safeUrl(value: string): string | undefined {
  try {
    const url = new URL(value);
    return ["https:", "http:"].includes(url.protocol) ? url.href : undefined;
  } catch {
    return undefined;
  }
}
export function orderedConcepts(concepts: Concept[]) {
  const result: Concept[] = [],
    visited = new Set<string>(),
    visiting = new Set<string>();
  const byId = new Map(concepts.map((c) => [c.id, c]));
  const visit = (c: Concept) => {
    if (visited.has(c.id)) return;
    if (visiting.has(c.id))
      throw new Error(
        "The roadmap contains a prerequisite cycle. Generate a new plan.",
      );
    visiting.add(c.id);
    for (const id of c.prerequisite_ids || []) {
      const parent = byId.get(id);
      if (parent) visit(parent);
    }
    visiting.delete(c.id);
    visited.add(c.id);
    result.push(c);
  };
  concepts.forEach(visit);
  return result;
}
export function percent(score: number) {
  return Math.round(Math.max(0, Math.min(1, score)) * 100);
}
