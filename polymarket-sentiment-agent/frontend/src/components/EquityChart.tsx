import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import type { EquityPoint } from "../api";

export function EquityChart({ data }: { data: EquityPoint[] }) {
  const shaped = data.map((d) => ({
    t: new Date(d.t).toLocaleTimeString(),
    pnl: d.pnl,
  }));
  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={shaped} margin={{ left: 4, right: 8, top: 8, bottom: 4 }}>
          <CartesianGrid stroke="#1c222d" strokeDasharray="3 3" />
          <XAxis dataKey="t" stroke="#8693a8" tick={{ fontSize: 10 }} />
          <YAxis stroke="#8693a8" tick={{ fontSize: 10 }} width={48} />
          <Tooltip
            contentStyle={{
              background: "#11151c",
              border: "1px solid #1c222d",
              fontSize: 12,
            }}
          />
          <ReferenceLine y={0} stroke="#8693a8" strokeDasharray="4 4" />
          <Line type="monotone" dataKey="pnl" stroke="#7cf6c4" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
