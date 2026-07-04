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
  if (results.length === 0) return <p className="loading-state">No results recorded yet.</p>;

  return (
    <div className="trajectory-chart" role="img" aria-label="Hormone trajectory over cycle days">
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={results} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e8e4df" />
          <XAxis
            dataKey="cycle_day"
            stroke="#6c7078"
            tick={{ fontSize: 12 }}
            label={{ value: "Cycle day", position: "insideBottom", offset: -4, fontSize: 12 }}
          />
          <YAxis
            yAxisId="e2"
            stroke="#6c7078"
            tick={{ fontSize: 12 }}
            label={{ value: "E2 (pg/mL)", angle: -90, position: "insideLeft", fontSize: 12 }}
          />
          <YAxis
            yAxisId="other"
            orientation="right"
            stroke="#6c7078"
            tick={{ fontSize: 12 }}
            label={{ value: "LH / progesterone (ng/mL)", angle: 90, position: "insideRight", fontSize: 12 }}
          />
          <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #e8e4df", fontSize: 13 }} />
          <Legend wrapperStyle={{ fontSize: 13 }} />
          <Line yAxisId="e2" type="monotone" dataKey="e2" name="Estrogen (E2)" stroke="#9a6b12" strokeWidth={2} dot={{ r: 2.5 }} />
          <Line yAxisId="other" type="monotone" dataKey="lh" name="LH" stroke="#2f6e8f" strokeWidth={2} dot={{ r: 2.5 }} />
          <Line
            yAxisId="other"
            type="monotone"
            dataKey="progesterone"
            name="Progesterone"
            stroke="#3b7a57"
            strokeWidth={2}
            dot={{ r: 2.5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
