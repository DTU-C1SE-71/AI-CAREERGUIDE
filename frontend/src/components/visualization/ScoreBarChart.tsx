import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

interface ScoreDatum {
  name: string
  value: number
}

export function ScoreBarChart({ data }: { data: ScoreDatum[] }) {
  return (
    <div className="h-44 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 6, right: 16 }}>
          <CartesianGrid
            strokeDasharray="3 3"
            horizontal={false}
            stroke="rgba(148, 163, 184, 0.25)"
          />
          <XAxis type="number" domain={[0, 100]} hide />
          <YAxis
            type="category"
            dataKey="name"
            width={82}
            tick={{ fontSize: 11, fill: "#334155", fontWeight: 700 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            cursor={{ fill: "rgba(255, 255, 255, 0.4)" }}
            contentStyle={{
              borderRadius: 14,
              fontSize: 12,
              background: "rgba(255, 255, 255, 0.85)",
              borderColor: "rgba(255, 255, 255, 0.9)",
              backdropFilter: "blur(16px)",
            }}
          />
          <Bar dataKey="value" radius={[0, 10, 10, 0]} barSize={16}>
            {data.map((_, index) => (
              <Cell
                key={index}
                fill={["#0284c7", "#0ea5e9", "#38bdf8"][index % 3]}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
