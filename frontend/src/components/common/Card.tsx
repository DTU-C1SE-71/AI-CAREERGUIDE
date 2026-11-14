import type { HTMLAttributes } from "react"

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  interactive?: boolean
}

export function Card({
  className = "",
  interactive = false,
  ...props
}: CardProps) {
  return (
    <div
      className={`glass-card rounded-2xl sm:rounded-3xl ${
        interactive ? "glass-card-interactive" : ""
      } ${className}`}
      {...props}
    />
  )
}
