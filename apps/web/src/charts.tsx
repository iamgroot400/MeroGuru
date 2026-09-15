// Minimal, dependency-free SVG charts. Kept intentionally simple (no charting
// library) since this app renders only a handful of chart shapes; colors use
// CSS custom properties so they follow the light/dark theme automatically.

const WIDTH = 640;
const HEIGHT = 180;
const PAD = 28;

export function ScoreTrendChart({
  points,
}: {
  points: { date: string; score: number }[];
}) {
  if (points.length < 2) {
    return (
      <p className="muted">
        Complete a few more quizzes to see your score trend here.
      </p>
    );
  }
  const innerW = WIDTH - PAD * 2;
  const innerH = HEIGHT - PAD * 2;
  const stepX = innerW / (points.length - 1);
  const coords = points.map((p, i) => ({
    x: PAD + i * stepX,
    y: PAD + innerH * (1 - p.score),
    ...p,
  }));
  const path = coords
    .map((c, i) => `${i === 0 ? "M" : "L"}${c.x.toFixed(1)},${c.y.toFixed(1)}`)
    .join(" ");
  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      className="chart"
      role="img"
      aria-label={`Quiz score trend across ${points.length} attempts, from ${Math.round(points[0].score * 100)}% to ${Math.round(points[points.length - 1].score * 100)}%`}
    >
      {[0, 0.5, 1].map((frac) => (
        <line
          key={frac}
          x1={PAD}
          x2={WIDTH - PAD}
          y1={PAD + innerH * (1 - frac)}
          y2={PAD + innerH * (1 - frac)}
          className="chart-gridline"
        />
      ))}
      <line
        x1={PAD}
        x2={WIDTH - PAD}
        y1={PAD + innerH * 0.3}
        y2={PAD + innerH * 0.3}
        className="chart-threshold"
        strokeDasharray="4 4"
      />
      <path d={path} className="chart-line" fill="none" />
      {coords.map((c, i) => (
        <circle key={i} cx={c.x} cy={c.y} r={3.5} className="chart-point" />
      ))}
    </svg>
  );
}

export function TimeSpentChart({
  points,
}: {
  points: { date: string; minutes: number }[];
}) {
  if (!points.length) {
    return (
      <p className="muted">
        Complete a lesson and save feedback to see time spent here.
      </p>
    );
  }
  const innerW = WIDTH - PAD * 2;
  const innerH = HEIGHT - PAD * 2;
  const max = Math.max(...points.map((p) => p.minutes), 1);
  const barW = innerW / points.length;
  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      className="chart"
      role="img"
      aria-label={`Minutes spent per day over the last ${points.length} days`}
    >
      {points.map((p, i) => {
        const h = (p.minutes / max) * innerH;
        return (
          <g key={p.date}>
            <rect
              x={PAD + i * barW + barW * 0.15}
              y={PAD + innerH - h}
              width={barW * 0.7}
              height={h}
              rx={3}
              className="chart-bar"
            />
            <text
              x={PAD + i * barW + barW / 2}
              y={HEIGHT - 6}
              textAnchor="middle"
              className="chart-axis-label"
            >
              {new Date(p.date).toLocaleDateString(undefined, { weekday: "narrow" })}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
