import { createContext, useContext, useState, type ReactNode } from "react";
import { request } from "./api/client";
import type { Goal } from "./api/types";
import { useAsync } from "./hooks";

function useGoalStore() {
  const goals = useAsync("goals", (signal) =>
    request<Goal[]>("/goals", { signal }),
  );
  const [selectedId, setSelectedId] = useState<string>("");
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
