import { useId, useState } from "react";
type Point = { date: string; value: number };
function HistoryChart({
  points,
  kind,
}: {
  points: Point[];
  kind: "score" | "time";
}) {
  const [selected, setSelected] = useState<number | null>(null),
    id = useId();
  if (!points.length)
    return (
      <p className="muted">
        {kind === "score"
          ? "Complete a quiz to see your results here."
          : "Save lesson feedback with time spent to see your study history."}
      </p>
    );
  const index = Math.min(selected ?? points.length - 1, points.length - 1),
    current = points[index];
  const max =
    kind === "score" ? 100 : Math.max(1, ...points.map((p) => p.value));
  const x = (i: number) => 55 + (i * 530) / Math.max(points.length - 1, 1),
    y = (v: number) => 155 - (v / max) * 125;
  const label = (p: Point) =>
    new Date(
      p.date.length === 10 ? p.date + "T12:00:00" : p.date,
    ).toLocaleDateString(undefined, { month: "short", day: "numeric" });
  return (
    <div className="interactive-chart">
      <svg
        className="chart"
        viewBox="0 0 640 195"
        role="img"
        aria-label={
          kind === "score"
            ? "Quiz scores in attempt order"
            : "Recorded study minutes by date"
        }
      >
        {[0, 0.5, 1].map((f) => (
          <g key={f}>
            <line
              x1={55}
              x2={600}
              y1={y(f * max)}
              y2={y(f * max)}
              className="chart-gridline"
            />
            <text
              x={43}
              y={y(f * max) + 4}
              textAnchor="end"
              className="chart-axis-label"
            >
              {Math.round(f * max)}
              {kind === "score" ? "%" : ""}
            </text>
          </g>
        ))}
        {kind === "score" ? (
          <>
            <path
              className="chart-line"
              fill="none"
              d={points
                .map((p, i) => (i ? "L" : "M") + x(i) + "," + y(p.value))
                .join(" ")}
            />
            {points.map((p, i) => (
              <circle
                key={i}
                className="chart-point"
                cx={x(i)}
                cy={y(p.value)}
                r={i === index ? 7 : 3.5}
              />
            ))}
          </>
        ) : (
          points.map((p, i) => (
            <rect
              key={i}
              className="chart-bar"
              x={55 + (i * 545) / points.length}
              y={y(p.value)}
              width={Math.max(2, 545 / points.length - 6)}
              height={155 - y(p.value)}
              rx={3}
              opacity={i === index ? 1 : 0.45}
            />
          ))
        )}
        <text x={55} y={182} className="chart-axis-label">
          {label(points[0])}
        </text>
        <text x={600} y={182} textAnchor="end" className="chart-axis-label">
          {label(points[points.length - 1])}
        </text>
      </svg>
      <div className="chart-inspector">
        <div>
          <label htmlFor={id}>
            {kind === "score" ? "Explore an attempt" : "Explore a study day"}
          </label>
          <select
            id={id}
            value={index}
            onChange={(e) => setSelected(Number(e.target.value))}
          >
            {points.map((p, i) => (
              <option key={i} value={i}>
                {kind === "score" ? "Attempt " + (i + 1) + " · " : ""}
                {label(p)}
              </option>
            ))}
          </select>
        </div>
        <p aria-live="polite">
          <strong>
            {Math.round(current.value)}
            {kind === "score" ? "%" : " min"}
          </strong>
          <span>
            {kind === "score"
              ? "Recorded quiz score"
              : "Time logged in feedback"}
          </span>
        </p>
      </div>
    </div>
  );
}
export function ScoreTrendChart({
  points,
}: {
  points: { date: string; score: number }[];
}) {
  return (
    <HistoryChart
      kind="score"
      points={points.map((p) => ({ date: p.date, value: p.score * 100 }))}
    />
  );
}
export function TimeSpentChart({
  points,
}: {
  points: { date: string; minutes: number }[];
}) {
  return (
    <HistoryChart
      kind="time"
      points={points.map((p) => ({ date: p.date, value: p.minutes }))}
    />
  );
}
