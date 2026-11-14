import {
  Background,
  Controls,
  Handle,
  Position,
  ReactFlow,
  type Node,
  type NodeProps,
} from "@xyflow/react"
import "@xyflow/react/dist/style.css"
import { Check, ChevronRight, LockKeyhole, Sparkles } from "lucide-react"
import { roadmap as fallbackRoadmap } from "../../services/mockData"
import type { RoadmapWeek } from "../../types/roadmap"

type RoadmapNodeData = {
  week: number
  eyebrow: string
  title: string
  description: string
  done: boolean
  locked: boolean
  completedCount: number
  totalTasks: number
  onOpen: (id: string) => void
}

function RoadmapNode({ id, data }: NodeProps<Node<RoadmapNodeData>>) {
  const isDone = data.done

  return (
    <button
      type="button"
      onClick={() => !data.locked && data.onOpen(id)}
      className={`group w-72 sm:w-80 rounded-2xl border p-4 sm:p-5 text-left transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-sky-400 ${
        data.locked
          ? "cursor-not-allowed border-slate-200 bg-slate-100/80 opacity-60"
          : isDone
            ? "border-emerald-300 bg-emerald-50/30 hover:-translate-y-1 hover:border-emerald-400 hover:shadow-lg shadow-sm"
            : "border-sky-200/90 bg-white/95 hover:-translate-y-1 hover:border-sky-400 hover:shadow-lg shadow-sm"
      }`}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!size-3.5 !rounded-full !border-2 !border-white !bg-sky-500"
      />

      {/* Top Header: Week Badge & Status */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className={`grid size-9 place-items-center rounded-xl text-xs font-black shadow-2xs ${
              isDone
                ? "bg-emerald-600 text-white"
                : "border border-sky-200 bg-sky-50 text-sky-700"
            }`}
          >
            {isDone ? <Check size={18} strokeWidth={2.5} /> : `W${data.week}`}
          </span>
          <span className="text-xs font-bold uppercase tracking-wider text-sky-700">
            {data.eyebrow}
          </span>
        </div>

        {data.locked ? (
          <LockKeyhole size={15} className="text-slate-400" />
        ) : (
          <span className="grid size-7 place-items-center rounded-lg bg-slate-100 text-slate-500 group-hover:bg-sky-100 group-hover:text-sky-600 transition-colors">
            <ChevronRight size={16} />
          </span>
        )}
      </div>

      {/* Title & Description */}
      <div className="mt-3">
        <h3 className="text-sm font-extrabold text-slate-900 group-hover:text-sky-700 transition-colors line-clamp-2 leading-snug">
          {data.title}
        </h3>
        <p className="mt-1.5 text-xs text-slate-600 line-clamp-2 leading-relaxed">
          {data.description}
        </p>
      </div>

      {/* Bottom Progress Tracker */}
      <div className="mt-3.5 flex items-center justify-between border-t border-slate-100 pt-2.5 text-xs font-semibold">
        <div className="flex items-center gap-1.5 text-slate-500">
          <span
            className={`size-2 rounded-full ${
              isDone ? "bg-emerald-500" : "bg-sky-500"
            }`}
          />
          <span>
            {data.completedCount}/{data.totalTasks} nhiệm vụ
          </span>
        </div>
        <span className="text-sky-600 group-hover:underline flex items-center gap-1 text-[11px] font-bold">
          Chi tiết
          <ChevronRight size={12} />
        </span>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className="!size-3.5 !rounded-full !border-2 !border-white !bg-sky-500"
      />
    </button>
  )
}

const nodeTypes = { roadmap: RoadmapNode }

export function RoadmapFlow({
  weeks = fallbackRoadmap,
  completed,
  onOpen,
}: {
  weeks?: RoadmapWeek[]
  completed: string[]
  onOpen: (id: string) => void
}) {
  const activeWeeks = weeks.length > 0 ? weeks : fallbackRoadmap

  const nodes: Node<RoadmapNodeData>[] = activeWeeks.map((week, index) => {
    const weekTaskIds = week.tasks.map((_, tIdx) => `${week.id}-${tIdx}`)
    const completedInWeek = weekTaskIds.filter((tId) =>
      completed.includes(tId),
    ).length
    const isDone =
      week.tasks.length > 0 && completedInWeek === week.tasks.length

    return {
      id: week.id,
      type: "roadmap",
      position: { x: index * 340 + 30, y: index % 2 ? 165 : 35 },
      data: {
        ...week,
        done: isDone,
        locked: false,
        completedCount: completedInWeek,
        totalTasks: week.tasks.length,
        onOpen,
      },
    }
  })

  const edges = activeWeeks.slice(0, -1).map((week, index) => ({
    id: `e-${week.id}`,
    source: week.id,
    target: activeWeeks[index + 1].id,
    animated: true,
    style: { stroke: "#0284c7", strokeWidth: 2.5 },
  }))

  return (
    <div className="relative h-[440px] sm:h-[500px] xl:h-[560px] w-full overflow-hidden rounded-3xl border border-slate-200/90 bg-gradient-to-b from-slate-50/70 via-sky-50/30 to-slate-50/80 shadow-xs">
      <div className="pointer-events-none absolute left-4 top-4 z-10 hidden sm:flex items-center gap-2 rounded-xl border border-white/80 bg-white/80 px-3 py-1.5 text-xs font-semibold text-slate-600 shadow-2xs backdrop-blur-md">
        <Sparkles size={14} className="text-sky-600" />
        Kéo thả hoặc cuộn chuột để phóng to/thu nhỏ sơ đồ
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.5}
        maxZoom={1.4}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#cbd5e1" gap={28} size={1} />
        <Controls className="!overflow-hidden !rounded-2xl !border !border-slate-200 !bg-white/90 !shadow-md !backdrop-blur-md" />
      </ReactFlow>
    </div>
  )
}
