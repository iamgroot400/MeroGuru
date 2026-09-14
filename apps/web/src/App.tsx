import { useEffect, useRef } from "react";
import {
  BookOpen,
  ChartNoAxesCombined,
  House,
  Map,
  Plus,
  Settings as SettingsIcon,
  Sprout,
} from "lucide-react";
import {
  Link,
  NavLink,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { useGoals } from "./context";
import { Dashboard } from "./pages/Dashboard";
import { GoalWizard } from "./pages/GoalWizard";
import { Settings } from "./pages/Settings";
import { GoalPage } from "./pages/GoalPage";
import { LessonPage } from "./pages/Lesson";
import { Empty } from "./components";

export function App() {
  const goals = useGoals(),
    location = useLocation(),
    navigate = useNavigate();
  const main = useRef<HTMLElement>(null);
  useEffect(() => {
    main.current?.focus();
    window.scrollTo(0, 0);
  }, [location.pathname]);
  const currentId = location.pathname.match(
    /^\/goals\/([^/]+)\/(roadmap|progress)/,
  )?.[1];
  const selected = currentId
    ? decodeURIComponent(currentId)
    : goals.current?.id;
  const goalPath = selected ? `/goals/${encodeURIComponent(selected)}` : null;
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <aside className="sidebar">
        <Link className="brand" to="/" aria-label="MeroGuru home">
          <span className="brand-icon">
            <BookOpen size={23} />
          </span>
          MeroGuru<span className="brand-dot">.</span>
        </Link>
        <p className="brand-caption">A little learning, every day.</p>
        <nav aria-label="Main navigation">
          <NavLink to="/" end>
            <House size={20} />
            My learning
          </NavLink>
          {goalPath && (
            <>
              <NavLink to={`${goalPath}/roadmap`}>
                <Map size={20} />
                Roadmap
              </NavLink>
              <NavLink to={`${goalPath}/progress`}>
                <ChartNoAxesCombined size={20} />
                Progress
              </NavLink>
            </>
          )}
          <NavLink to="/goals/new">
            <Plus size={20} />
            New learning goal
          </NavLink>
          <NavLink to="/settings">
            <SettingsIcon size={20} />
            Settings
          </NavLink>
        </nav>
        {!!goals.data?.length && (
          <div className="goal-select">
            <label htmlFor="current-goal">Your learning goal</label>
            <select
              id="current-goal"
              value={selected || ""}
              onChange={(e) => {
                goals.select(e.target.value);
                if (currentId)
                  navigate(
                    `/goals/${encodeURIComponent(e.target.value)}/${location.pathname.endsWith("/progress") ? "progress" : "roadmap"}`,
                  );
              }}
            >
              {goals.data.map((goal) => (
                <option key={goal.id} value={goal.id}>
                  {goal.title}
                </option>
              ))}
            </select>
          </div>
        )}
        <div className="sidebar-note">
          <Sprout size={24} />
          <p>Make room for curiosity.</p>
          <small>Your pace. Your path.</small>
        </div>
        <div className="instance-label">
          <span />
          Your personal instance
        </div>
      </aside>
      <div className="main-shell">
        <div className="topbar" role="banner">
          <span>Your learning space</span>
          <span>
            {new Date().toLocaleDateString(undefined, {
              weekday: "short",
              month: "short",
              day: "numeric",
            })}
          </span>
        </div>
        <main id="main" ref={main} tabIndex={-1}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/goals/new" element={<GoalWizard />} />
            <Route path="/settings" element={<Settings />} />
            <Route
              path="/goals/:goalId/roadmap"
              element={<GoalPage mode="roadmap" />}
            />
            <Route
              path="/goals/:goalId/progress"
              element={<GoalPage mode="progress" />}
            />
            <Route path="/lessons/:lessonId" element={<LessonPage />} />
            <Route
              path="*"
              element={
                <Empty
                  title="This page is off the path."
                  action={
                    <Link className="button" to="/">
                      Back to my learning
                    </Link>
                  }
                />
              }
            />
          </Routes>
        </main>
      </div>
    </div>
  );
}
