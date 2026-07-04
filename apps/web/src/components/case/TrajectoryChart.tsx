import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { HormoneResult } from "../../types/contracts";

export function TrajectoryChart({ results }: { results: HormoneResult[] }) {
  if (results.length === 0) return <p>No results recorded yet.</p>;

  return (
    <div className="trajectory-chart" role="img" aria-label="Hormone trajectory over cycle days">
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={results} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="cycle_day" label={{ value: "Cycle day", position: "insideBottom", offset: -4 }} />
          <YAxis yAxisId="e2" label={{ value: "E2 (pg/mL)", angle: -90, position: "insideLeft" }} />
          <YAxis
            yAxisId="other"
            orientation="right"
            label={{ value: "LH / progesterone (ng/mL)", angle: 90, position: "insideRight" }}
          />
          <Tooltip />
          <Legend />
          <Line yAxisId="e2" type="monotone" dataKey="e2" name="E2" stroke="#b4530a" strokeWidth={2} />
          <Line yAxisId="other" type="monotone" dataKey="lh" name="LH" stroke="#3a6ea5" strokeWidth={2} />
          <Line
            yAxisId="other"
            type="monotone"
            dataKey="progesterone"
            name="Progesterone"
            stroke="#5a8f5a"
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
