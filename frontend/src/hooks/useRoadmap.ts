import { useEffect, useMemo, useState } from "react"
import { readStorage, writeStorage } from "../services/storage"

export function useRoadmap(majorCode = "7480101", totalTasksCount = 12) {
  const storageKey =
    majorCode === "7480101"
      ? "career-guide:roadmap"
      : `career-guide:roadmap:${majorCode}`

  const [completed, setCompleted] = useState<string[]>(() =>
    readStorage(storageKey, []),
  )

  useEffect(() => {
    setCompleted(readStorage(storageKey, []))
  }, [storageKey])

  const toggle = (id: string) =>
    setCompleted((current) => {
      const next = current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id]
      writeStorage(storageKey, next)
      return next
    })

  return {
    completed,
    toggle,
    progress: useMemo(() => {
      const denom = Math.max(1, totalTasksCount)
      return Math.min(100, Math.round((completed.length / denom) * 100))
    }, [completed, totalTasksCount]),
  }
}
