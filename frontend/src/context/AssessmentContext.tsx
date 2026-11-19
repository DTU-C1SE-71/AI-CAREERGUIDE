import { summarizeAssessmentAttempt } from "../utils/assessmentEvidence"
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react"
import { requestJSON } from "../services/api"
import { readStorage, writeStorage } from "../services/storage"
import type {
  AcademicScore,
  AssessmentHistoryItem,
  AssessmentState,
  CareerAspirationInput,
} from "../types/assessment"
import { useAuth } from "./AuthContext"

interface ServerAssessmentProfile {
  assessment_id?: string | null
  has_assessment?: boolean
  riasec_answers?: Record<string, unknown>
  cognitive_answers?: Record<string, unknown>
  raw_grades?: Record<string, unknown>
  aspiration?: {
    dream_job?: string
    desired_field?: string
    work_values?: string[]
    preferred_environment?: string
    score_strategy?: string
  } | null
  last_updated?: string
}

const initial: AssessmentState = {
  step: 1,
  answers: {},
  cognitive: {},
  scores: [],
  completed: false,
}

interface AssessmentContextValue {
  assessment: AssessmentState
  history: AssessmentHistoryItem[]
  activeHistoryId: string | null
  hydrating: boolean
  update: (changes: Partial<AssessmentState>) => void
  reset: () => void
  recordCompletedAttempt: (state: AssessmentState) => AssessmentHistoryItem
  selectHistoryAttempt: (id: string) => void
  deleteHistoryAttempt: (id: string) => void
}

const AssessmentContext = createContext<AssessmentContextValue | null>(null)

export function AssessmentProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  return <ScopedAssessmentProvider key={user?.id || "guest"}>{children}</ScopedAssessmentProvider>
}

function ScopedAssessmentProvider({ children }: { children: ReactNode }) {
  const { user, token } = useAuth()
  const userKey = useMemo(
    () => (user?.email || user?.id || "guest").toLowerCase().trim(),
    [user?.email, user?.id],
  )

  const assessmentStorageKey = `career-guide:assessment:${userKey}`
  const historyStorageKey = `career-guide:assessment-history:${userKey}`

  const [history, setHistory] = useState<AssessmentHistoryItem[]>(() =>
    readStorage<AssessmentHistoryItem[]>(historyStorageKey, []),
  )
  const [assessment, setAssessment] = useState<AssessmentState>(() => {
    const stored = readStorage<AssessmentState | null>(assessmentStorageKey, null)
    return stored ?? initial
  })
  const [activeHistoryId, setActiveHistoryId] = useState<string | null>(null)
  const [hydrating, setHydrating] = useState(false)
  const hydratedRef = useRef(false)

  useEffect(() => {
    if (hydratedRef.current || !user || !token || user.role?.toLowerCase() === "admin") {
      return
    }
    const stored = readStorage<AssessmentState | null>(assessmentStorageKey, null)
    const hasCompletedLocal = Boolean(
      stored?.completed &&
        (Object.keys(stored.answers || {}).length >= 3 ||
          (stored.scores || []).length >= 2),
    )
    if (hasCompletedLocal) {
      hydratedRef.current = true
      return
    }

    let active = true
    const controller = new AbortController()
    setHydrating(true)

    requestJSON<ServerAssessmentProfile>("/assessment/profile", {
      signal: controller.signal,
    })
      .then((profile) => {
        if (!active || controller.signal.aborted) return
        hydratedRef.current = true
        if (!profile?.has_assessment) return

        const answerCount = Object.keys(profile.riasec_answers || {}).length
        const gradeCount = Object.keys(profile.raw_grades || {}).length
        if (answerCount < 3 && gradeCount < 2) return

        const answers: Record<string, number> = {}
        Object.entries(profile.riasec_answers || {}).forEach(([k, v]) => {
          const num = Number(v)
          if (Number.isInteger(num) && num >= 1 && num <= 5) {
            answers[k] = num
          }
        })

        const cognitive: Record<string, string> = {}
        Object.entries(profile.cognitive_answers || {}).forEach(([k, v]) => {
          if (typeof v === "string" && v.trim()) {
            cognitive[k] = v.trim()
          }
        })

        const scores: AcademicScore[] = Object.entries(profile.raw_grades || {})
          .map(([subject, score]) => ({
            subject,
            score: Number(score),
            zScore: null,
          }))
          .filter(
            (s) =>
              s.subject &&
              Number.isFinite(s.score) &&
              s.score >= 0 &&
              s.score <= 10,
          )

        const asp = profile.aspiration
        const hasAsp = Boolean(
          asp &&
            (asp.dream_job ||
              asp.desired_field ||
              (Array.isArray(asp.work_values) && asp.work_values.length > 0) ||
              asp.preferred_environment),
        )
        const aspiration: CareerAspirationInput | undefined =
          hasAsp && asp
            ? {
                dreamJob: asp.dream_job || "",
                desiredField: asp.desired_field || "",
                workValues: Array.isArray(asp.work_values) ? asp.work_values : [],
                preferredEnvironment: asp.preferred_environment || "",
                scoreStrategy:
                  asp.score_strategy === "REALISTIC_SAFE" ||
                  asp.score_strategy === "CHALLENGE_TOP" ||
                  asp.score_strategy === "FLEXIBLE_PATHWAY"
                    ? asp.score_strategy
                    : "FLEXIBLE_PATHWAY",
              }
            : undefined

        const completedAt = profile.last_updated || new Date().toISOString()
        const hydratedState: AssessmentState = {
          step: 4,
          answers,
          cognitive,
          scores,
          aspiration,
          completed: true,
          completedAt,
          syncStatus: "SYNCED",
          submissionId: profile.assessment_id || undefined,
        }

        const existingHistory = readStorage<AssessmentHistoryItem[]>(
          historyStorageKey,
          [],
        )
        const dbHistoryId = `db-${profile.assessment_id || "latest"}`
        const seededHistory =
          existingHistory.length === 0 &&
          !existingHistory.some((h) => h.id === dbHistoryId)
        if (seededHistory) {
          const summary = summarizeAssessmentAttempt(answers, cognitive, scores)
          const historyItem: AssessmentHistoryItem = {
            id: dbHistoryId,
            createdAt: completedAt,
            ...summary,
            aspiration,
          }
          setHistory([historyItem])
          writeStorage(historyStorageKey, [historyItem])
        }

        const hasInProgressDraft = Boolean(
          stored &&
            !stored.completed &&
            (Object.keys(stored.answers || {}).length > 0 ||
              (stored.scores || []).length > 0),
        )
        if (!hasInProgressDraft) {
          setAssessment(hydratedState)
          writeStorage(assessmentStorageKey, hydratedState)
          if (seededHistory) {
            setActiveHistoryId(dbHistoryId)
          }
        }
      })
      .catch(() => {
        if (active && !controller.signal.aborted) {
          hydratedRef.current = true
        }
      })
      .finally(() => {
        if (active) {
          setHydrating(false)
        }
      })

    return () => {
      active = false
      controller.abort()
    }
  }, [user?.id, user?.role, token, assessmentStorageKey, historyStorageKey])

  useEffect(() => {
    const sync = (event: StorageEvent) => {
      if (event.key === assessmentStorageKey) { setAssessment(readStorage<AssessmentState>(assessmentStorageKey, initial)); setActiveHistoryId(null) }
      if (event.key === historyStorageKey) setHistory(readStorage<AssessmentHistoryItem[]>(historyStorageKey, []))
    }
    const handleLogout = () => {
      if (userKey === "guest") {
        setAssessment(initial)
        setHistory([])
        setActiveHistoryId(null)
      }
    }
    window.addEventListener("storage", sync)
    window.addEventListener("career-guide:logout", handleLogout)
    return () => {
      window.removeEventListener("storage", sync)
      window.removeEventListener("career-guide:logout", handleLogout)
    }
  }, [assessmentStorageKey, historyStorageKey, userKey])

  const update = useCallback(
    (changes: Partial<AssessmentState>) => {
      setAssessment((current) => {
        const next = { ...current, ...changes }
        writeStorage(assessmentStorageKey, next)
        return next
      })
    },
    [assessmentStorageKey],
  )

  const reset = useCallback(() => {
    setAssessment(initial)
    setActiveHistoryId(null)
    writeStorage(assessmentStorageKey, initial)
  }, [assessmentStorageKey])

  const recordCompletedAttempt = useCallback(
    (state: AssessmentState): AssessmentHistoryItem => {
      const nowIso = new Date().toISOString()
      const completedState: AssessmentState = {
        ...state,
        completed: true,
        completedAt: nowIso,
      }
      setAssessment(completedState)
      writeStorage(assessmentStorageKey, completedState)

      const summary = summarizeAssessmentAttempt(
        completedState.answers,
        completedState.cognitive,
        completedState.scores,
      )
      const newItem: AssessmentHistoryItem = {
        id: `attempt-${Date.now()}`,
        createdAt: nowIso,
        ...summary,
        aspiration: completedState.aspiration
          ? { ...completedState.aspiration }
          : undefined,
      }

      setHistory((prev) => {
        const nextHistory = [newItem, ...prev]
        writeStorage(historyStorageKey, nextHistory)
        return nextHistory
      })
      setActiveHistoryId(newItem.id)
      return newItem
    },
    [assessmentStorageKey, historyStorageKey],
  )

  const selectHistoryAttempt = useCallback(
    (id: string) => {
      const found = history.find((item) => item.id === id)
      if (!found) return
      const restored: AssessmentState = {
        step: 4,
        answers: { ...found.answers },
        cognitive: { ...found.cognitive },
        scores: [...found.scores],
        aspiration: found.aspiration ? { ...found.aspiration } : undefined,
        completed: true,
        completedAt: found.createdAt,
      }
      setAssessment(restored)
      writeStorage(assessmentStorageKey, restored)
      setActiveHistoryId(found.id)
    },
    [history, assessmentStorageKey],
  )

  const deleteHistoryAttempt = useCallback(
    (id: string) => {
      setHistory((prev) => {
        const nextHistory = prev.filter((item) => item.id !== id)
        writeStorage(historyStorageKey, nextHistory)

        if (nextHistory.length === 0) {
          setAssessment(initial)
          writeStorage(assessmentStorageKey, initial)
          setActiveHistoryId(null)
        } else if (activeHistoryId === id) {
          setAssessment(initial)
          writeStorage(assessmentStorageKey, initial)
          setActiveHistoryId(null)
        }
        return nextHistory
      })
    },
    [activeHistoryId, assessmentStorageKey, historyStorageKey],
  )

  const value = useMemo(
    () => ({
      assessment,
      history,
      activeHistoryId,
      hydrating,
      update,
      reset,
      recordCompletedAttempt,
      selectHistoryAttempt,
      deleteHistoryAttempt,
    }),
    [
      assessment,
      history,
      activeHistoryId,
      hydrating,
      update,
      reset,
      recordCompletedAttempt,
      selectHistoryAttempt,
      deleteHistoryAttempt,
    ],
  )

  return (
    <AssessmentContext.Provider value={value}>
      {children}
    </AssessmentContext.Provider>
  )
}

export function useAssessment() {
  const context = useContext(AssessmentContext)
  if (!context)
    throw new Error("useAssessment must be used within AssessmentProvider")
  return context
}
