import type { ReactNode } from "react"

export function Badge({
  children,
  tone = "indigo",
}: {
  children: ReactNode
  tone?: "indigo" | "emerald" | "amber" | "slate" | "rose"
}) {
  const tones = {
    indigo: "bg-sky-500/12 text-sky-700 ring-white/80 backdrop-blur-md",
    emerald: "bg-sky-500/15 text-sky-800 ring-sky-200/80 backdrop-blur-md",
    amber: "bg-cyan-500/12 text-cyan-800 ring-cyan-200/80 backdrop-blur-md",
    slate: "bg-white/65 text-slate-600 ring-white/85 backdrop-blur-md",
    rose: "bg-rose-500/12 text-rose-700 ring-rose-200/80 backdrop-blur-md",
  }
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-bold ring-1 ring-inset ${tones[tone]}`}
    >
      {children}
    </span>
  )
}
