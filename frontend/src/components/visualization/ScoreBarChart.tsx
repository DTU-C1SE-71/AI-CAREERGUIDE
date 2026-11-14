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
    <div className="h-48 sm:h-52 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 18 }}>
          <CartesianGrid
            strokeDasharray="3 3"
            horizontal={false}
            stroke="rgba(148, 163, 184, 0.22)"
          />
          <XAxis type="number" domain={[0, 100]} hide />
          <YAxis
            type="category"
            dataKey="name"
            width={88}
            tick={{ fontSize: 12, fill: "#334155", fontWeight: 600 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            cursor={{ fill: "rgba(240, 249, 255, 0.6)" }}
            contentStyle={{
              borderRadius: 16,
              fontSize: 13,
              fontWeight: 600,
              background: "rgba(255, 255, 255, 0.95)",
              borderColor: "rgba(226, 232, 240, 0.9)",
              boxShadow: "0 10px 25px -5px rgba(15, 23, 42, 0.1)",
            }}
          />
          <Bar dataKey="value" radius={[0, 10, 10, 0]} barSize={18}>
            {data.map((_, index) => (
              <Cell
                key={index}
                fill={["#0284c7", "#0ea5e9", "#06b6d4"][index % 3]}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
