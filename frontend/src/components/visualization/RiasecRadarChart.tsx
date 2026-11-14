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
    <div className="h-80 sm:h-88 xl:h-96 w-full pt-2">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} outerRadius="72%">
          <PolarGrid stroke="rgba(148, 163, 184, 0.28)" strokeDasharray="3 3" />
          <PolarAngleAxis
            dataKey="key"
            tick={{ fill: "#0f172a", fontSize: 14, fontWeight: 700 }}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const item = payload[0].payload as RiasecRadarPoint
                return (
                  <div className="rounded-2xl border border-slate-200/90 bg-white/95 p-3.5 shadow-xl backdrop-blur-xl text-xs">
                    <p className="font-bold text-slate-900 mb-2 border-b border-slate-100 pb-1.5 text-sm">
                      {item.key} · {item.label}
                    </p>
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between gap-5 text-sky-700">
                        <span className="font-medium">Sở thích:</span>
                        <span className="font-bold tabular-nums text-sm">{item.value}%</span>
                      </div>
                      <div className="flex items-center justify-between gap-5 text-cyan-700">
                        <span className="font-medium">Học lực:</span>
                        <span className="font-bold tabular-nums text-sm">
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
            fillOpacity={0.28}
            strokeWidth={2.5}
          />
          <Radar
            name="Học lực (%)"
            dataKey="academicValue"
            stroke="#06b6d4"
            fill="#22d3ee"
            fillOpacity={0.22}
            strokeWidth={2}
          />
          <Legend
            verticalAlign="bottom"
            height={36}
            iconType="circle"
            wrapperStyle={{
              paddingTop: "10px",
              fontSize: "12px",
              fontWeight: 600,
            }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}
