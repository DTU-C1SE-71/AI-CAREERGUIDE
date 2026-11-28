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
import { ApiError, requestJSON } from "../services/api"
import { readStorage, writeStorage } from "../services/storage"
import type {
  AcademicScore,
  AssessmentHistoryItem,
  AssessmentState,
  CareerAspirationInput,
} from "../types/assessment"
import { useAuth } from "./AuthContext"

interface ServerAspirationPayload {
  dream_job?: string
  desired_field?: string
  work_values?: string[]
  preferred_environment?: string
  score_strategy?: string
}

interface ServerAssessmentProfile {
  assessment_id?: string | null
  has_assessment?: boolean
  riasec_answers?: Record<string, unknown>
  cognitive_answers?: Record<string, unknown>
  raw_grades?: Record<string, unknown>
  aspiration?: ServerAspirationPayload | null
  last_updated?: string
}

interface ServerAssessmentSubmission {
  submission_id: string
  set_code?: string | null
  version?: string | null
  riasec_answers?: Record<string, unknown>
  raw_cognitive_answers?: Record<string, unknown>
  cognitive_answers?: Record<string, unknown>
  grades_by_subject?: Record<string, unknown>
  aspiration?: ServerAspirationPayload | null
  completed_at?: string
}

function normalizeServerAnswers(raw?: Record<string, unknown>): Record<string, number> {
  const answers: Record<string, number> = {}
  Object.entries(raw || {}).forEach(([k, v]) => {
    const num = Number(v)
    if (Number.isInteger(num) && num >= 1 && num <= 5) {
      answers[k] = num
    }
  })
  return answers
}

function normalizeServerCognitive(raw?: Record<string, unknown>): Record<string, string> {
  const cognitive: Record<string, string> = {}
  Object.entries(raw || {}).forEach(([k, v]) => {
    if (typeof v === "string" && v.trim()) {
      cognitive[k] = v.trim()
    }
  })
  return cognitive
}

function normalizeServerScores(raw?: Record<string, unknown>): AcademicScore[] {
  return Object.entries(raw || {})
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
}

function normalizeServerAspiration(
  asp?: ServerAspirationPayload | null,
): CareerAspirationInput | undefined {
  const hasAsp = Boolean(
    asp &&
      (asp.dream_job ||
        asp.desired_field ||
        (Array.isArray(asp.work_values) && asp.work_values.length > 0) ||
        asp.preferred_environment),
  )
  if (!hasAsp || !asp) return undefined
  return {
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
}

function buildHistoryItemFromSubmission(
  sub: ServerAssessmentSubmission,
): AssessmentHistoryItem | null {
  if (!sub?.submission_id) return null
  const answers = normalizeServerAnswers(sub.riasec_answers)
  const rawCog =
    sub.raw_cognitive_answers && Object.keys(sub.raw_cognitive_answers).length > 0
      ? sub.raw_cognitive_answers
      : sub.cognitive_answers
  const cognitive = normalizeServerCognitive(rawCog)
  const scores = normalizeServerScores(sub.grades_by_subject)
  if (Object.keys(answers).length === 0 && scores.length === 0 && Object.keys(cognitive).length === 0) {
    return null
  }
  const aspiration = normalizeServerAspiration(sub.aspiration)
  const summary = summarizeAssessmentAttempt(answers, cognitive, scores)
  return {
    id: `db-${sub.submission_id}`,
    createdAt: sub.completed_at || new Date().toISOString(),
    ...summary,
    aspiration,
  }
}

function buildAttemptContentFingerprint(item: AssessmentHistoryItem): string {
  const answers = Object.entries(item.answers || {})
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([k, v]) => `${k}:${v}`)
    .join("|")
  const cognitive = Object.entries(item.cognitive || {})
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([k, v]) => `${k}:${v}`)
    .join("|")
  const scores = [...(item.scores || [])]
    .sort((a, b) => a.subject.localeCompare(b.subject))
    .map((s) => `${s.subject}:${Number(s.score).toFixed(2)}`)
    .join("|")
  return `${answers}#${cognitive}#${scores}`
}

function mergeServerAndLocalHistory(
  serverItems: AssessmentHistoryItem[],
  localItems: AssessmentHistoryItem[],
): AssessmentHistoryItem[] {
  const byId = new Map<string, AssessmentHistoryItem>()
  const serverFingerprints = new Set<string>()
  for (const item of serverItems) {
    byId.set(item.id, item)
    serverFingerprints.add(buildAttemptContentFingerprint(item))
  }
  for (const local of localItems) {
    if (byId.has(local.id)) continue
    // Bỏ qua bản ghi db-* cũ không còn tồn tại trong serverItems để tránh hồi sinh bản đã xóa,
    // nhưng luôn giữ toàn bộ bản ghi local chưa đồng bộ (attempt-*) trừ khi đã khớp bản server.
    if (local.id.startsWith("db-")) continue
    const localTime = Date.parse(local.createdAt)
    const duplicatedByTime = serverItems.some((srv) => {
      const srvTime = Date.parse(srv.createdAt)
      if (!Number.isFinite(localTime) || !Number.isFinite(srvTime)) return false
      if (Math.abs(srvTime - localTime) > 60_000) return false
      return (
        Object.keys(srv.answers || {}).length === Object.keys(local.answers || {}).length &&
        (srv.scores || []).length === (local.scores || []).length
      )
    })
    const duplicatedByContent = serverFingerprints.has(buildAttemptContentFingerprint(local))
    if (!duplicatedByTime && !duplicatedByContent) {
      byId.set(local.id, local)
    }
  }
  return Array.from(byId.values()).sort(
    (a, b) => (Date.parse(b.createdAt) || 0) - (Date.parse(a.createdAt) || 0),
  )
}

const initial: AssessmentState = {
  step: 1,
  answers: {},
  cognitive: {},
  scores: [],
  completed: false,
}

const AI_EXPLANATION_CACHE_PREFIX = "careerguide:ai_explanation:"

export function clearClientAiExplanationCache(): void {
  if (typeof window === "undefined") return
  try {
    const keys: string[] = []
    for (let i = 0; i < window.sessionStorage.length; i += 1) {
      const k = window.sessionStorage.key(i)
      if (k && k.startsWith(AI_EXPLANATION_CACHE_PREFIX)) {
        keys.push(k)
      }
    }
    keys.forEach((k) => window.sessionStorage.removeItem(k))
  } catch {
    // Ignore sessionStorage restrictions
  }
}

interface AssessmentContextValue {
  assessment: AssessmentState
  history: AssessmentHistoryItem[]
  activeHistoryId: string | null
  hydrating: boolean
  profileRevision: number
  update: (changes: Partial<AssessmentState>) => void
  reset: () => void
  recordCompletedAttempt: (state: AssessmentState) => AssessmentHistoryItem
  updateHistoryAttempt: (
    id: string,
    state: AssessmentState,
    options?: { bumpRevision?: boolean },
  ) => void
  linkHistoryAttemptSubmission: (localAttemptId: string, submissionId: string) => void
  selectHistoryAttempt: (id: string) => void
  deleteHistoryAttempt: (id: string) => Promise<void> | void
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
  const [profileRevision, setProfileRevision] = useState(0)
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
    const hasInProgressDraft = Boolean(
      stored &&
        !stored.completed &&
        (Object.keys(stored.answers || {}).length > 0 ||
          (stored.scores || []).length > 0),
    )

    let active = true
    const controller = new AbortController()
    if (!hasCompletedLocal) {
      setHydrating(true)
    }

    const submissionsReq = requestJSON<ServerAssessmentSubmission[]>(
      "/assessment/submissions?limit=20",
      { signal: controller.signal },
    ).catch(() => null)

    const profileReq = hasCompletedLocal
      ? Promise.resolve<ServerAssessmentProfile | null>(null)
      : requestJSON<ServerAssessmentProfile>("/assessment/profile", {
          signal: controller.signal,
        }).catch(() => null)

    Promise.all([submissionsReq, profileReq])
      .then(([submissions, profile]) => {
        if (!active || controller.signal.aborted) return
        hydratedRef.current = true

        const serverHistoryItems = Array.isArray(submissions)
          ? submissions
              .map(buildHistoryItemFromSubmission)
              .filter((item): item is AssessmentHistoryItem => item !== null)
          : []

        const existingHistory = readStorage<AssessmentHistoryItem[]>(
          historyStorageKey,
          [],
        )

        if (serverHistoryItems.length > 0) {
          const mergedHistory = mergeServerAndLocalHistory(
            serverHistoryItems,
            existingHistory,
          )
          setHistory(mergedHistory)
          writeStorage(historyStorageKey, mergedHistory)

          if (!hasCompletedLocal && !hasInProgressDraft) {
            const latest = serverHistoryItems[0]
            const latestSubId = latest.id.startsWith("db-")
              ? latest.id.slice(3)
              : undefined
            const hydratedState: AssessmentState = {
              step: 4,
              answers: { ...latest.answers },
              cognitive: { ...latest.cognitive },
              scores: [...latest.scores],
              aspiration: latest.aspiration ? { ...latest.aspiration } : undefined,
              completed: true,
              completedAt: latest.createdAt,
              syncStatus: "SYNCED",
              submissionId: latestSubId,
            }
            setAssessment(hydratedState)
            writeStorage(assessmentStorageKey, hydratedState)
            setActiveHistoryId(latest.id)
          }
          return
        }

        if (hasCompletedLocal || !profile?.has_assessment) return

        const answerCount = Object.keys(profile.riasec_answers || {}).length
        const gradeCount = Object.keys(profile.raw_grades || {}).length
        if (answerCount < 3 && gradeCount < 2) return

        const answers = normalizeServerAnswers(profile.riasec_answers)
        const cognitive = normalizeServerCognitive(profile.cognitive_answers)
        const scores = normalizeServerScores(profile.raw_grades)
        const aspiration = normalizeServerAspiration(profile.aspiration)
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

        if (!hasInProgressDraft) {
          setAssessment(hydratedState)
          writeStorage(assessmentStorageKey, hydratedState)
          if (seededHistory) {
            setActiveHistoryId(dbHistoryId)
          }
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
      const itemId = completedState.submissionId
        ? `db-${completedState.submissionId}`
        : `attempt-${Date.now()}`
      const newItem: AssessmentHistoryItem = {
        id: itemId,
        createdAt: nowIso,
        ...summary,
        aspiration: completedState.aspiration
          ? { ...completedState.aspiration }
          : undefined,
      }

      setHistory((prev) => {
        const nextHistory = [newItem, ...prev.filter((item) => item.id !== itemId)]
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
      const isServerBacked = found.id.startsWith("db-")
      const restored: AssessmentState = {
        step: 4,
        answers: { ...found.answers },
        cognitive: { ...found.cognitive },
        scores: [...found.scores],
        aspiration: found.aspiration ? { ...found.aspiration } : undefined,
        completed: true,
        completedAt: found.createdAt,
        syncStatus: isServerBacked ? "SYNCED" : undefined,
        submissionId: isServerBacked ? found.id.slice(3) : undefined,
      }
      setAssessment(restored)
      writeStorage(assessmentStorageKey, restored)
      setActiveHistoryId(found.id)
    },
    [history, assessmentStorageKey],
  )

  const updateHistoryAttempt = useCallback(
    (
      id: string,
      state: AssessmentState,
      options?: { bumpRevision?: boolean },
    ) => {
      const summary = summarizeAssessmentAttempt(
        state.answers,
        state.cognitive,
        state.scores,
      )
      setHistory((prev) => {
        const idx = prev.findIndex((item) => item.id === id)
        const baseItem = idx >= 0 ? prev[idx] : null
        const updatedItem: AssessmentHistoryItem = {
          id,
          createdAt: baseItem?.createdAt || state.completedAt || new Date().toISOString(),
          ...summary,
          aspiration: state.aspiration ? { ...state.aspiration } : undefined,
        }
        const nextHistory =
          idx >= 0
            ? prev.map((item, i) => (i === idx ? updatedItem : item))
            : [updatedItem, ...prev]
        writeStorage(historyStorageKey, nextHistory)
        return nextHistory
      })
      const isServerBacked = id.startsWith("db-")
      const syncedState: AssessmentState = {
        ...state,
        step: 4,
        completed: true,
        syncStatus: isServerBacked ? "SYNCED" : state.syncStatus,
        submissionId: isServerBacked ? id.slice(3) : state.submissionId,
      }
      setAssessment(syncedState)
      writeStorage(assessmentStorageKey, syncedState)
      setActiveHistoryId(id)
      if (options?.bumpRevision !== false) {
        clearClientAiExplanationCache()
        setProfileRevision((n) => n + 1)
      }
    },
    [assessmentStorageKey, historyStorageKey],
  )

  const linkHistoryAttemptSubmission = useCallback(
    (localAttemptId: string, submissionId: string) => {
      if (!localAttemptId || !submissionId) return
      const serverId = `db-${submissionId}`
      setHistory((prev) => {
        const idx = prev.findIndex((item) => item.id === localAttemptId)
        if (idx === -1) return prev
        const target = prev[idx]
        const renamed: AssessmentHistoryItem = { ...target, id: serverId }
        const deduped = prev.filter(
          (item) => item.id !== localAttemptId && item.id !== serverId,
        )
        deduped.splice(Math.min(idx, deduped.length), 0, renamed)
        writeStorage(historyStorageKey, deduped)
        return deduped
      })
      setActiveHistoryId((current) =>
        current === localAttemptId ? serverId : current,
      )
    },
    [historyStorageKey],
  )

  const deleteHistoryAttempt = useCallback(
    async (id: string) => {
      if (id.startsWith("db-") && token) {
        const submissionId = id.slice(3)
        try {
          await requestJSON<null>(
            `/assessment/submissions/${encodeURIComponent(submissionId)}`,
            { method: "DELETE" },
          )
        } catch (err) {
          if (!(err instanceof ApiError && err.status === 404)) {
            return
          }
        }
      }

      setHistory((prev) => {
        const wasActive =
          activeHistoryId === id ||
          (!activeHistoryId && prev[0]?.id === id) ||
          (id.startsWith("db-") && assessment.submissionId === id.slice(3))
        const nextHistory = prev.filter((item) => item.id !== id)
        writeStorage(historyStorageKey, nextHistory)

        if (nextHistory.length === 0) {
          setAssessment(initial)
          writeStorage(assessmentStorageKey, initial)
          setActiveHistoryId(null)
        } else if (wasActive) {
          const fallback = nextHistory[0]
          const isServerBacked = fallback.id.startsWith("db-")
          const restored: AssessmentState = {
            step: 4,
            answers: { ...fallback.answers },
            cognitive: { ...fallback.cognitive },
            scores: [...fallback.scores],
            aspiration: fallback.aspiration ? { ...fallback.aspiration } : undefined,
            completed: true,
            completedAt: fallback.createdAt,
            syncStatus: isServerBacked ? "SYNCED" : undefined,
            submissionId: isServerBacked ? fallback.id.slice(3) : undefined,
          }
          setAssessment(restored)
          writeStorage(assessmentStorageKey, restored)
          setActiveHistoryId(fallback.id)
        }
        return nextHistory
      })
    },
    [
      activeHistoryId,
      assessment.submissionId,
      assessmentStorageKey,
      historyStorageKey,
      token,
    ],
  )

  const value = useMemo(
    () => ({
      assessment,
      history,
      activeHistoryId,
      hydrating,
      profileRevision,
      update,
      reset,
      recordCompletedAttempt,
      updateHistoryAttempt,
      linkHistoryAttemptSubmission,
      selectHistoryAttempt,
      deleteHistoryAttempt,
    }),
    [
      assessment,
      history,
      activeHistoryId,
      hydrating,
      profileRevision,
      update,
      reset,
      recordCompletedAttempt,
      updateHistoryAttempt,
      linkHistoryAttemptSubmission,
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
