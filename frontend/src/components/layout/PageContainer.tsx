import type { ReactNode } from "react"

export function PageContainer({
  children,
  className = "",
  size = "default",
}: {
  children: ReactNode
  className?: string
  size?: "default" | "narrow" | "wide"
}) {
  const widths = {
    narrow: "max-w-5xl",
    default: "max-w-[92rem] 2xl:max-w-[104rem]",
    wide: "max-w-[108rem] 2xl:max-w-[118rem]",
  }

  return (
    <div
      className={`mx-auto w-full ${widths[size]} px-4 sm:px-6 lg:px-8 xl:px-10 ${className}`}
    >
      {children}
    </div>
  )
}
