import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { post } from "../api/client";
import type { Goal, GoalInput } from "../api/types";
import { useGoals } from "../context";
import { ErrorState, PageHeading } from "../components";
import { dayKey } from "../utils";

const days = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];
const steps = ["Your goal", "Your rhythm", "Review"];
export function GoalWizard() {
  const [step, setStep] = useState(0),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [draft, setDraft] = useState<GoalInput>({
    title: "",
    description: "",
    starting_level: "beginner",
    target_date: "",
    minutes_per_day: 25,
    study_days: [0, 1, 2, 3, 4],
    preferred_formats: ["mixed"],
  });
  const heading = useRef<HTMLHeadingElement>(null),
    navigate = useNavigate(),
    goals = useGoals();
  useEffect(() => {
    heading.current?.focus();
  }, [step]);
  const update = <K extends keyof GoalInput>(key: K, value: GoalInput[K]) =>
    setDraft((old) => ({ ...old, [key]: value }));
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    if (step === 0 && !draft.title.trim()) {
      setError("Give your learning goal a title.");
      return;
    }
    if (
      step === 1 &&
      (!draft.study_days.length || !draft.preferred_formats.length)
    ) {
      setError("Choose at least one study day and one learning format.");
      return;
    }
    if (step < 2) {
      setStep(step + 1);
      return;
    }
    setBusy(true);
    try {
      const goal = await post<Goal>("/goals", {
        ...draft,
        title: draft.title.trim(),
        description: draft.description.trim(),
      });
      goals.select(goal.id);
      goals.reload();
      navigate(`/goals/${encodeURIComponent(goal.id)}/roadmap`, {
        state: { startGeneration: true },
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save your goal.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="narrow">
      <PageHeading title="Make room for something new.">
        A plan works best when it fits your life.
      </PageHeading>
      <ol className="wizard-steps" aria-label="Goal setup progress">
        {steps.map((label, i) => (
          <li
            key={label}
            aria-current={i === step ? "step" : undefined}
            className={i <= step ? "reached" : ""}
          >
            <span>{i < step ? "✓" : i + 1}</span>
            {label}
          </li>
        ))}
      </ol>
      <form className="form-panel" onSubmit={submit}>
        <h2 ref={heading} tabIndex={-1}>
          {steps[step]}
        </h2>
        {step === 0 && (
          <>
            <label htmlFor="title">What would you like to learn?</label>
            <input
              id="title"
              required
              minLength={3}
              maxLength={200}
              value={draft.title}
              placeholder="e.g. Build my first Python project"
              onChange={(e) => update("title", e.target.value)}
            />
            <label htmlFor="description">
              What would you like to be able to do?
            </label>
            <textarea
              id="description"
              rows={4}
              maxLength={5000}
              value={draft.description}
              placeholder="Tell us what matters to you and what you already know."
              onChange={(e) => update("description", e.target.value)}
            />
            <label htmlFor="level">Where are you starting?</label>
            <select
              id="level"
              value={draft.starting_level}
              onChange={(e) => update("starting_level", e.target.value)}
            >
              <option value="beginner">Beginner — I’m starting fresh</option>
              <option value="intermediate">
                Intermediate — I know the basics
              </option>
              <option value="advanced">Advanced — I want to go deeper</option>
            </select>
          </>
        )}
        {step === 1 && (
          <>
            <div className="form-grid">
              <div>
                <label htmlFor="target-date">Target date</label>
                <input
                  type="date"
                  id="target-date"
                  required
                  min={dayKey(new Date())}
                  value={draft.target_date}
                  onChange={(e) => update("target_date", e.target.value)}
                />
              </div>
              <div>
                <label htmlFor="minutes">Minutes per study day</label>
                <input
                  id="minutes"
                  type="number"
                  required
                  min={5}
                  max={480}
                  step={1}
                  value={draft.minutes_per_day}
                  onChange={(e) =>
                    update("minutes_per_day", Number(e.target.value))
                  }
                />
              </div>
            </div>
            <fieldset>
              <legend>Which days work for you?</legend>
              <div className="choices">
                {days.map((day, i) => (
                  <label className="choice" key={day}>
                    <input
                      type="checkbox"
                      checked={draft.study_days.includes(i)}
                      onChange={(e) =>
                        update(
                          "study_days",
                          e.target.checked
                            ? [...draft.study_days, i].sort()
                            : draft.study_days.filter((d) => d !== i),
                        )
                      }
                    />
                    {day}
                  </label>
                ))}
              </div>
            </fieldset>
            <fieldset>
              <legend>How do you like to learn?</legend>
              <div className="choices">
                {["video", "reading", "practice", "mixed"].map((format) => (
                  <label className="choice" key={format}>
                    <input
                      type="checkbox"
                      checked={draft.preferred_formats.includes(format)}
                      onChange={(e) =>
                        update(
                          "preferred_formats",
                          e.target.checked
                            ? format === "mixed"
                              ? ["mixed"]
                              : [
                                  ...draft.preferred_formats.filter(
                                    (f) => f !== "mixed",
                                  ),
                                  format,
                                ]
                            : draft.preferred_formats.filter(
                                (f) => f !== format,
                              ),
                        )
                      }
                    />
                    {format === "mixed"
                      ? "A mix of everything"
                      : format[0].toUpperCase() + format.slice(1)}
                  </label>
                ))}
              </div>
            </fieldset>
          </>
        )}
        {step === 2 && (
          <>
            <h3>{draft.title}</h3>
            <p className="prose">
              {draft.description || "No extra details added."}
            </p>
            <dl className="review-list">
              <dt>Starting point</dt>
              <dd>{draft.starting_level}</dd>
              <dt>Target date</dt>
              <dd>{draft.target_date}</dd>
              <dt>Daily commitment</dt>
              <dd>{draft.minutes_per_day} minutes</dd>
              <dt>Study days</dt>
              <dd>{draft.study_days.map((d) => days[d]).join(", ")}</dd>
              <dt>Learning formats</dt>
              <dd>{draft.preferred_formats.join(", ")}</dd>
            </dl>
            <p className="notice">
              We’ll save your goal and prepare your roadmap. This usually takes
              10–30 seconds. Connect an AI provider in{" "}
              <Link to="/settings">Settings</Link> if you haven’t already.
            </p>
          </>
        )}
        {error && <ErrorState message={error} />}
        <div className="form-actions">
          {step > 0 ? (
            <button
              className="secondary"
              type="button"
              disabled={busy}
              onClick={() => {
                setError("");
                setStep(step - 1);
              }}
            >
              Back
            </button>
          ) : (
            <Link className="text-link" to="/">
              Cancel
            </Link>
          )}
          <button disabled={busy}>
            {busy
              ? "Saving your goal…"
              : step === 2
                ? "Create learning plan"
                : "Continue"}
          </button>
        </div>
      </form>
    </div>
  );
}
