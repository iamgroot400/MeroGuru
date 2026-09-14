import { describe, expect, it } from "vitest";
import {
  completedInWeek,
  orderedConcepts,
  safeUrl,
  weekDates,
  dayKey,
} from "./utils";
describe("learning data", () => {
  it("orders prerequisites before dependent concepts", () => {
    expect(
      orderedConcepts([
        { id: "b", title: "B", prerequisite_ids: ["a"] },
        { id: "a", title: "A", prerequisite_ids: [] },
      ]).map((c) => c.id),
    ).toEqual(["a", "b"]);
  });
  it("rejects cycles instead of hanging", () => {
    expect(() =>
      orderedConcepts([
        { id: "a", title: "A", prerequisite_ids: ["b"] },
        { id: "b", title: "B", prerequisite_ids: ["a"] },
      ]),
    ).toThrow("cycle");
  });
  it("uses Monday through Sunday and actual completion dates", () => {
    const now = new Date(2026, 8, 16, 12);
    expect(weekDates(now).map(dayKey)).toEqual([
      "2026-09-14",
      "2026-09-15",
      "2026-09-16",
      "2026-09-17",
      "2026-09-18",
      "2026-09-19",
      "2026-09-20",
    ]);
    expect(
      completedInWeek(
        [
          {
            id: "a",
            title: "A",
            completed_at: new Date(2026, 8, 15).toISOString(),
          },
          { id: "b", title: "B", status: "completed" },
          {
            id: "c",
            title: "C",
            completed_at: new Date(2026, 8, 13).toISOString(),
          },
        ],
        now,
      ).map((l) => l.id),
    ).toEqual(["a"]);
  });
  it("blocks executable resource URLs", () => {
    expect(safeUrl("javascript:alert(1)")).toBeUndefined();
    expect(safeUrl("data:text/html,test")).toBeUndefined();
    expect(safeUrl("https://example.org")).toBe("https://example.org/");
  });
});
