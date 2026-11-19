import { useCallback, useMemo, useState } from "react"
import { readStorage, writeStorage } from "../services/storage"
import { useAuth } from "../context/AuthContext"

export function useRoadmap(majorCode: string, totalTasksCount: number) {
  const { user } = useAuth()
  const storageKey = `career-guide:roadmap:${user?.id || "guest"}:${majorCode}`
  const [state, setState] = useState(() => ({ key: storageKey, completed: readStorage<string[]>(storageKey, []) }))
  const completed = state.key === storageKey ? state.completed : readStorage<string[]>(storageKey, [])
  const toggle = (id: string) => setState(current => {
    const active = current.key === storageKey ? current.completed : readStorage<string[]>(storageKey, [])
    const next = active.includes(id) ? active.filter(item => item !== id) : [...active, id]
    writeStorage(storageKey, next)
    return { key: storageKey, completed: next }
  })
  const restoreCompleted = useCallback((items: string[]) => {
    const next = [...new Set(items)]
    writeStorage(storageKey, next)
    setState({ key: storageKey, completed: next })
  }, [storageKey])
  return { completed, toggle, restoreCompleted, progress: useMemo(() => totalTasksCount > 0 ? Math.min(100, Math.round(completed.length / totalTasksCount * 100)) : 0, [completed, totalTasksCount]) }
}
