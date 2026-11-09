import {
  Legend,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts"
import { riasecData, type RiasecRadarPoint } from "../../services/mockData"

interface RiasecRadarChartProps {
  data?: RiasecRadarPoint[]
}

export function RiasecRadarChart({
  data = riasecData,
}: RiasecRadarChartProps) {
  return (
    <div className="h-76 w-full pt-1">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} outerRadius="68%">
          <PolarGrid stroke="rgba(148, 163, 184, 0.3)" strokeDasharray="3 3" />
          <PolarAngleAxis
            dataKey="key"
            tick={{ fill: "#1e293b", fontSize: 13, fontWeight: 800 }}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const item = payload[0].payload as RiasecRadarPoint
                return (
                  <div className="rounded-2xl border border-white/90 bg-white/85 p-3 shadow-lg backdrop-blur-xl text-xs">
                    <p className="font-extrabold text-slate-900 mb-1.5 border-b border-slate-200/60 pb-1">
                      {item.key} · {item.label}
                    </p>
                    <div className="space-y-1">
                      <div className="flex items-center justify-between gap-4 text-sky-700">
                        <span className="font-semibold">Sở thích:</span>
                        <span className="font-black">{item.value}%</span>
                      </div>
                      <div className="flex items-center justify-between gap-4 text-cyan-700">
                        <span className="font-semibold">Học lực:</span>
                        <span className="font-black">
                          {item.academicValue ?? item.value}%
                        </span>
                      </div>
                    </div>
                  </div>
                )
              }
              return null
            }}
          />
          <Radar
            name="Sở thích (%)"
            dataKey="value"
            stroke="#0284c7"
            fill="#0ea5e9"
            fillOpacity={0.26}
            strokeWidth={2.5}
          />
          <Radar
            name="Học lực (%)"
            dataKey="academicValue"
            stroke="#06b6d4"
            fill="#22d3ee"
            fillOpacity={0.2}
            strokeWidth={2}
          />
          <Legend
            verticalAlign="bottom"
            height={32}
            iconType="circle"
            wrapperStyle={{
              paddingTop: "8px",
              fontSize: "11px",
              fontWeight: 700,
            }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}
