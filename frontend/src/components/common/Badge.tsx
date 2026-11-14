import type { ReactNode } from "react"

export function Badge({
  children,
  tone = "indigo",
  className = "",
}: {
  children: ReactNode
  tone?: "indigo" | "emerald" | "amber" | "slate" | "rose"
  className?: string
}) {
  const tones = {
    indigo: "bg-sky-50/90 text-sky-700 ring-sky-200/85",
    emerald: "bg-emerald-50/90 text-emerald-700 ring-emerald-200/85",
    amber: "bg-amber-50/90 text-amber-800 ring-amber-200/85",
    slate: "bg-slate-100/85 text-slate-600 ring-slate-200/85",
    rose: "bg-rose-50/90 text-rose-700 ring-rose-200/85",
  }

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${tones[tone]} ${className}`}
    >
      {children}
    </span>
  )
}
