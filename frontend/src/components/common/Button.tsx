import { LoaderCircle, type LucideIcon } from "lucide-react"
import type { ButtonHTMLAttributes, ReactNode } from "react"

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "dark"
  size?: "sm" | "md" | "lg"
  icon?: LucideIcon
  loading?: boolean
  children: ReactNode
}

export function Button({
  variant = "primary",
  size = "md",
  icon: Icon,
  loading,
  className = "",
  children,
  ...props
}: ButtonProps) {
  const styles = {
    primary:
      "bg-sky-600 text-white hover:bg-sky-700 shadow-sm shadow-sky-600/20",
    secondary:
      "bg-white/95 text-slate-800 border border-slate-200/90 hover:border-sky-300 hover:bg-sky-50/60",
    ghost: "text-slate-600 hover:bg-slate-100/90 hover:text-slate-900",
    dark: "bg-gradient-to-r from-sky-600 to-cyan-600 text-white hover:from-sky-700 hover:to-cyan-700 shadow-sm shadow-sky-600/20",
  }

  const sizes = {
    sm: "min-h-9 px-3.5 py-1.5 text-xs rounded-xl gap-1.5",
    md: "min-h-11 px-5 py-2.5 text-sm rounded-xl gap-2",
    lg: "min-h-12 px-6 py-3 text-base rounded-2xl gap-2.5",
  }

  return (
    <button
      className={`inline-flex items-center justify-center font-semibold transition-all duration-200 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-sky-500/20 disabled:pointer-events-none disabled:opacity-50 ${styles[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {loading ? (
        <LoaderCircle className="animate-spin shrink-0" size={17} />
      ) : Icon ? (
        <Icon className="shrink-0" size={17} strokeWidth={2.1} />
      ) : null}
      {children}
    </button>
  )
}
