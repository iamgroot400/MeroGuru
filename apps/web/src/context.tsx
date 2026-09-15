import { createContext, useContext, useState, type ReactNode } from "react";
import { request } from "./api/client";
import type { Goal } from "./api/types";
import { useAsync } from "./hooks";

const SELECTED_GOAL_KEY = "meroguru:selectedGoalId";

function readStoredSelection(): string {
  try {
    return sessionStorage.getItem(SELECTED_GOAL_KEY) || "";
  } catch {
    return "";
  }
}
function storeSelection(id: string) {
  try {
    if (id) sessionStorage.setItem(SELECTED_GOAL_KEY, id);
    else sessionStorage.removeItem(SELECTED_GOAL_KEY);
  } catch {
    /* Selection still works for this session without storage. */
  }
}

function useGoalStore() {
  const goals = useAsync("goals", (signal) =>
    request<Goal[]>("/goals", { signal }),
  );
  // Remembered across navigation (and reloads, for this browser tab) so
  // switching to a goal once doesn't get silently reset to the newest one.
  const [selectedId, setSelectedIdState] = useState<string>(readStoredSelection);
  const setSelectedId = (id: string) => {
    storeSelection(id);
    setSelectedIdState(id);
  };
  const current =
    goals.data?.find((g) => g.id === selectedId) ??
    goals.data?.find((g) => !g.status || g.status === "active") ??
    goals.data?.[0];
  return { ...goals, current, select: setSelectedId };
}
const GoalContext = createContext<ReturnType<typeof useGoalStore> | null>(null);
export function GoalProvider({ children }: { children: ReactNode }) {
  const value = useGoalStore();
  return <GoalContext.Provider value={value}>{children}</GoalContext.Provider>;
}
export function useGoals() {
  const value = useContext(GoalContext);
  if (!value) throw new Error("GoalProvider is missing");
  return value;
}
