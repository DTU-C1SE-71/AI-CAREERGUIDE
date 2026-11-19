import { useMemo } from "react"
import { useAssessment } from "./useAssessment"

/** Match Dashboard: current profile at index zero, immutable snapshot for older attempts. */
export function useSelectedAssessment() {
  const { assessment, history, activeHistoryId } = useAssessment()
  return useMemo(() => {
    const index = activeHistoryId ? history.findIndex(item => item.id === activeHistoryId) : 0
    const snapshot = index > 0 ? history[index] : (!assessment.completed ? history[0] : undefined)
    return snapshot ? {
      ...assessment,
      answers: snapshot.answers || {}, cognitive: snapshot.cognitive || {},
      scores: snapshot.scores || [], aspiration: snapshot.aspiration,
      completed: true, completedAt: snapshot.createdAt,
    } : assessment
  }, [assessment, history, activeHistoryId])
}
