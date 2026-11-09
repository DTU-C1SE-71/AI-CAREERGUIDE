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
import { Check, ChevronRight, LockKeyhole } from "lucide-react"
import { roadmap as fallbackRoadmap } from "../../services/mockData"
import type { RoadmapWeek } from "../../types/roadmap"

type RoadmapNodeData = {
  week: number
  eyebrow: string
  title: string
  description: string
  done: boolean
  locked: boolean
  onOpen: (id: string) => void
}

function RoadmapNode({ id, data }: NodeProps<Node<RoadmapNodeData>>) {
  return (
    <button
      onClick={() => !data.locked && data.onOpen(id)}
      className={`w-64 rounded-2xl border bg-white p-4 text-left shadow-lg transition ${
        data.locked
          ? "cursor-not-allowed border-slate-200 opacity-60"
          : data.done
            ? "border-emerald-300 hover:-translate-y-1"
            : "border-sky-200 hover:-translate-y-1 hover:border-sky-400"
      }`}
    >
      <Handle type="target" position={Position.Left} className="!bg-sky-500" />
      <div className="flex items-start justify-between">
        <span
          className={`grid size-9 place-items-center rounded-xl text-xs font-black ${
            data.done
              ? "bg-emerald-100 text-emerald-700"
              : "bg-sky-100 text-sky-700"
          }`}
        >
          {data.done ? <Check size={17} /> : `W${data.week}`}
        </span>
        {data.locked ? (
          <LockKeyhole size={15} className="text-slate-400" />
        ) : (
          <ChevronRight size={17} className="text-sky-500" />
        )}
      </div>
      <p className="mt-4 text-[10px] font-extrabold uppercase tracking-widest text-slate-400">
        {data.eyebrow}
      </p>
      <h3 className="mt-1 text-sm font-extrabold text-slate-900 line-clamp-2">
        {data.title}
      </h3>
      <p className="mt-2 text-[11px] leading-5 text-slate-500 line-clamp-3">
        {data.description}
      </p>
      <Handle type="source" position={Position.Right} className="!bg-sky-500" />
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
  const nodes: Node<RoadmapNodeData>[] = activeWeeks.map((week, index) => ({
    id: week.id,
    type: "roadmap",
    position: { x: index * 310, y: index % 2 ? 155 : 25 },
    data: {
      ...week,
      done:
        week.tasks.length > 0 &&
        week.tasks.every((_, taskIndex) =>
          completed.includes(`${week.id}-${taskIndex}`),
        ),
      locked: false,
      onOpen,
    },
  }))
  const edges = activeWeeks.slice(0, -1).map((week, index) => ({
    id: `e-${week.id}`,
    source: week.id,
    target: activeWeeks[index + 1].id,
    animated: true,
    style: { stroke: "#38bdf8", strokeWidth: 2 },
  }))
  return (
    <div className="h-[500px] w-full overflow-hidden rounded-3xl border border-slate-200 bg-slate-50">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.5}
        maxZoom={1.3}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#cbd5e1" gap={24} size={1} />
        <Controls className="!overflow-hidden !rounded-xl !border-slate-200 !shadow-lg" />
      </ReactFlow>
    </div>
  )
}
