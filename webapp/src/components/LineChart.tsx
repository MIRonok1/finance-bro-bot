// Свой минимальный SVG-график вместо Chart.js/Recharts — незачем тянуть
// библиотеку под один тип графика в строго монохромном дизайне (см.
// CLAUDE.md, раздел про Mini App).

export interface LineChartPoint {
  label: string;
  value: number;
}

interface LineChartProps {
  points: LineChartPoint[];
  height?: number;
  formatValue?: (v: number) => string;
}

const VIEW_WIDTH = 320;
const PADDING = 10;

export function LineChart({ points, height = 120, formatValue }: LineChartProps) {
  if (points.length === 0) {
    return <div className="state-block">Пока нет данных для графика.</div>;
  }

  const values = points.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const stepX = points.length > 1 ? (VIEW_WIDTH - PADDING * 2) / (points.length - 1) : 0;
  const coords = points.map((p, i) => ({
    x: PADDING + i * stepX,
    y: height - PADDING - ((p.value - min) / range) * (height - PADDING * 2),
  }));

  const pathD = coords
    .map((c, i) => `${i === 0 ? "M" : "L"}${c.x.toFixed(1)},${c.y.toFixed(1)}`)
    .join(" ");
  const last = coords[coords.length - 1];
  const fmt = formatValue ?? ((v: number) => String(v));

  return (
    <div>
      <svg
        viewBox={`0 0 ${VIEW_WIDTH} ${height}`}
        width="100%"
        height={height}
        preserveAspectRatio="none"
        role="img"
        aria-label="График"
      >
        <line
          x1={PADDING}
          y1={height - PADDING}
          x2={VIEW_WIDTH - PADDING}
          y2={height - PADDING}
          stroke="var(--border)"
          strokeWidth={1}
        />
        <path
          d={pathD}
          fill="none"
          stroke="var(--fg)"
          strokeWidth={2}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        <circle cx={last.x} cy={last.y} r={3} fill="var(--fg)" />
      </svg>
      <div className="row-sub" style={{ display: "flex", justifyContent: "space-between" }}>
        <span>{points[0].label}</span>
        <span>{fmt(points[points.length - 1].value)}</span>
        <span>{points[points.length - 1].label}</span>
      </div>
    </div>
  );
}
