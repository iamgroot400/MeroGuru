import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const goal = {
  id: "goal-1",
  title: "Understand the night sky",
  description:
    "Learn to recognise constellations and understand how stars evolve.",
  starting_level: "beginner",
  minutes_per_day: 25,
  study_days: [0, 2, 4],
  preferred_formats: ["mixed"],
  target_date: "2027-02-01",
  status: "active",
  plan_id: "plan-1",
};
const lesson = {
  id: "lesson-1",
  goal_id: "goal-1",
  title: "Finding your way around the night sky",
  estimated_minutes: 25,
  status: "pending",
  objective: "Identify the North Star and use it to orient yourself.",
  activities: [
    {
      activity_type: "explanation",
      title: "Explanation",
      instructions:
        "Polaris sits close to the north celestial pole. Its position makes it a useful guide for observers in the Northern Hemisphere.",
    },
    {
      activity_type: "practice",
      title: "Practice",
      instructions:
        "Draw the Big Dipper and trace a line from its pointer stars to Polaris.",
    },
    {
      activity_type: "resource",
      title: "NASA: the night sky",
      instructions: "Watch: https://science.nasa.gov/skywatching/",
    },
  ],
  citations: [
    { title: "NASA Skywatching", url: "https://science.nasa.gov/skywatching/" },
  ],
};
async function mock(page: Page, empty = false) {
  const calls: { path: string; method: string; body: unknown }[] = [];
  let credentials = [
    {
      id: "key-1",
      provider: "openai",
      masked_label: "•••• 1234",
      validation_status: "ok",
      is_active_provider: true,
    },
  ];
  await page.route("**/api/v1/**", async (route) => {
    const req = route.request(),
      path = new URL(req.url()).pathname.replace("/api/v1", "");
    expect(req.headers().authorization).toBeUndefined();
    let body: unknown;
    try {
      body = req.postDataJSON();
    } catch {
      body = undefined;
    }
    calls.push({ path, method: req.method(), body });
    let data: unknown = null,
      status = 200;
    if (path === "/goals")
      data = req.method() === "POST" ? goal : empty ? [] : [goal];
    else if (path === "/goals/goal-1") data = goal;
    else if (path.endsWith("/generate-plan")) data = { job_id: "job-1" };
    else if (path === "/jobs/job-1") data = { status: "completed" };
    else if (path.endsWith("/concept-map"))
      data = [
        {
          id: "c2",
          external_key: "stars",
          title: "How stars evolve",
          description: "From a cloud of gas to a stellar remnant.",
          prerequisite_keys: ["sky"],
          estimated_minutes: 30,
        },
        {
          id: "c1",
          external_key: "sky",
          title: "Reading the night sky",
          description: "Find your bearings above the horizon.",
          prerequisite_keys: [],
          estimated_minutes: 25,
        },
      ];
    else if (path.endsWith("/mastery"))
      data = {
        concepts: [
          { concept_id: "c1", mastery_state: "mastered", mastery_score: 0.92 },
          {
            concept_id: "c2",
            mastery_state: "practicing",
            mastery_score: 0.35,
          },
        ],
        assessment_history: [
          {
            id: "attempt-1",
            title: "Reading the sky",
            score: 0.8,
            created_at: "2026-09-14T09:00:00Z",
          },
        ],
      };
    else if (path === "/plans/plan-1")
      data = { id: "plan-1", lessons: [lesson] };
    else if (path === "/plans/plan-1/today") data = lesson;
    else if (path === "/lessons/lesson-1") data = lesson;
    else if (path.endsWith("/assessment"))
      data = {
        id: "assessment-1",
        questions: [
          {
            id: "q1",
            prompt: "Which star helps you find north?",
            options_json: ["Polaris", "Sirius"],
          },
        ],
      };
    else if (path.endsWith("/attempts"))
      data = {
        score: 1,
        per_question: { q1: true },
        explanations: { q1: "Polaris is close to the north celestial pole." },
      };
    else if (path.endsWith("/complete"))
      data = { ...lesson, status: "completed" };
    else if (path.endsWith("/feedback")) status = 204;
    else if (path === "/credentials") {
      if (req.method() === "POST") {
        credentials.push({
          id: "key-2",
          provider: "openai",
          masked_label: "•••• 9876",
          validation_status: "untested",
          is_active_provider: true,
        });
        data = credentials.at(-1);
      } else data = credentials;
    } else if (path.endsWith("/test")) data = { ok: true };
    else if (path.startsWith("/credentials/") && req.method() === "DELETE") {
      credentials = credentials.filter((c) => c.id !== path.split("/").at(-1));
      status = 204;
    } else status = 404;
    await route.fulfill({
      status,
      contentType: "application/json",
      ...(status === 204 ? {} : { body: JSON.stringify(data) }),
    });
  });
  return calls;
}
test("dashboard, roadmap and progress show API data at 400px", async ({
  page,
}) => {
  await mock(page);
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Today’s lesson" }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/dashboard-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 400, height: 900 });
  await expect(
    page.getByRole("link", { name: "Start learning" }),
  ).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(400);
  await page.screenshot({
    path: "test-results/dashboard-mobile.png",
    fullPage: true,
  });
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.getByRole("link", { name: "Roadmap", exact: true }).click();
  await expect(page.getByText("concepts mastered")).toContainText("1 of 2");
  await expect(page.locator(".roadmap-list h2").first()).toHaveText(
    "Reading the night sky",
  );
  await page
    .getByRole("link", { name: "Progress", exact: true })
    .last()
    .click();
  await expect(page.getByRole("cell", { name: "80%" })).toBeVisible();
});
test("goal wizard validates, saves exact preferences and polls the job", async ({
  page,
}) => {
  const calls = await mock(page, true);
  await page.goto("/");
  await page.getByRole("link", { name: "Create your first goal" }).click();
  await page
    .getByLabel("What would you like to learn?")
    .fill("Understand the night sky");
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByLabel("Target date").fill("2027-02-01");
  await page.getByLabel("Minutes per study day").fill("20");
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Create learning plan" }).click();
  await expect(page.getByText("1 of 2")).toBeVisible();
  await expect
    .poll(() => calls.filter((c) => c.path.endsWith("/generate-plan")).length)
    .toBe(1);
  expect(
    calls.find((c) => c.path === "/goals" && c.method === "POST")?.body,
  ).toMatchObject({
    minutes_per_day: 20,
    study_days: [0, 1, 2, 3, 4],
    preferred_formats: ["mixed"],
  });
});
test("lesson supports backend activities, quiz, feedback and completion", async ({
  page,
}) => {
  const calls = await mock(page);
  await page.goto("/lessons/lesson-1");
  await expect(
    page.getByText("Polaris sits close", { exact: false }),
  ).toBeVisible();
  await page.getByLabel("Polaris", { exact: true }).check();
  await page.getByRole("button", { name: "Check my answers" }).click();
  await expect(page.getByText("You scored 100%")).toBeVisible();
  await page.getByLabel("Difficulty", { exact: true }).selectOption("3");
  await page.getByLabel("Usefulness", { exact: true }).selectOption("4");
  await page.getByLabel("Confidence", { exact: true }).selectOption("4");
  await page.getByLabel("Time spent (minutes)").fill("23");
  await page.getByRole("button", { name: "Save feedback" }).click();
  await expect(
    page.getByText("Feedback saved.", { exact: false }),
  ).toBeVisible();
  expect(calls.find((c) => c.path.endsWith("/feedback"))?.body).toEqual({
    difficulty: "just_right",
    usefulness: 4,
    confidence: 0.75,
    time_spent_minutes: 23,
  });
  await page
    .getByRole("button", { name: "Complete lesson", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Lesson completed", exact: true }),
  ).toBeDisabled();
});
test("credentials stay masked and replacement removes old key only after save", async ({
  page,
}) => {
  const calls = await mock(page);
  await page.goto("/settings");
  await page
    .getByRole("button", { name: "Test connection", exact: true })
    .click();
  await expect(page.getByText("Connection successful.")).toBeVisible();
  await page.getByRole("button", { name: "Replace", exact: true }).click();
  await page.getByLabel("New API key").fill("private-never-display-9876");
  await page.getByRole("button", { name: "Save replacement" }).click();
  await expect(page.getByText("•••• 9876", { exact: true })).toBeVisible();
  await expect(page.getByText("private-never-display-9876")).toHaveCount(0);
  expect(
    calls.findIndex((c) => c.path === "/credentials" && c.method === "POST"),
  ).toBeLessThan(
    calls.findIndex(
      (c) => c.path === "/credentials/key-1" && c.method === "DELETE",
    ),
  );
  await page.getByRole("button", { name: "Remove", exact: true }).click();
  await page
    .getByRole("button", { name: "Remove connection", exact: true })
    .click();
  await expect(page.getByText("•••• 9876")).toHaveCount(0);
});
test("API failure can be retried and navigation works from the keyboard", async ({
  page,
}) => {
  await mock(page);
  await page.route("**/api/v1/goals", (route) =>
    route.fulfill({ status: 500, body: "error" }),
  );
  await page.goto("/");
  await expect(page.getByRole("alert")).toBeVisible();
  await page.getByRole("link", { name: "Skip to content" }).focus();
  await expect(
    page.getByRole("link", { name: "Skip to content" }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("main")).toBeFocused();
  await page.unroute("**/api/v1/goals");
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(
    page.getByRole("heading", { name: "Today’s lesson" }),
  ).toBeVisible();
});

test("roadmap resumes queued jobs after refresh and recovers from a failed job", async ({
  page,
}) => {
  await mock(page);
  await page.addInitScript(() =>
    sessionStorage.setItem("meroguru:job:goal-1", "job-1"),
  );
  let failed = false;
  await page.route("**/api/v1/jobs/job-1", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: failed ? "failed" : "running" }),
    }),
  );
  await page.goto("/goals/goal-1/roadmap");
  await expect(
    page.getByRole("heading", { name: "Building a path that fits you…" }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Building a path that fits you…" }),
  ).toBeVisible();
  failed = true;
  await expect(page.getByRole("alert")).toContainText(
    "Your plan could not be generated",
  );
  expect(
    await page.evaluate(() => sessionStorage.getItem("meroguru:job:goal-1")),
  ).toBeNull();
  await page.unroute("**/api/v1/jobs/job-1");
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("all forms remain accessible and fit a 400px screen", async ({ page }) => {
  await mock(page);
  await page.setViewportSize({ width: 400, height: 900 });
  for (const url of [
    "/settings",
    "/goals/new",
    "/lessons/lesson-1",
    "/goals/goal-1/progress",
  ]) {
    await page.goto(url);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.locator(".state")).toHaveCount(0);
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(400);
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  }
});
