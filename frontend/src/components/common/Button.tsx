import { LoaderCircle, type LucideIcon } from "lucide-react"
import type { ButtonHTMLAttributes, ReactNode } from "react"

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "dark"
  icon?: LucideIcon
  loading?: boolean
  children: ReactNode
}

export function Button({
  variant = "primary",
  icon: Icon,
  loading,
  className = "",
  children,
  ...props
}: ButtonProps) {
  const styles = {
    primary: "bg-sky-600 text-white hover:bg-sky-700 shadow-lg shadow-sky-200",
    secondary:
      "bg-white text-slate-800 border border-slate-200 hover:border-sky-300 hover:bg-sky-50",
    ghost: "text-slate-600 hover:bg-slate-100",
    dark: "bg-gradient-to-r from-sky-500 to-blue-600 text-white hover:from-sky-600 hover:to-blue-700",
  }
  return (
    <button
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold transition-all focus:outline-none focus:ring-4 focus:ring-sky-100 disabled:opacity-50 ${styles[variant]} ${className}`}
      {...props}
    >
      {loading ? (
        <LoaderCircle className="animate-spin" size={17} />
      ) : Icon ? (
        <Icon size={17} strokeWidth={2.2} />
      ) : null}
      {children}
    </button>
  )
}
