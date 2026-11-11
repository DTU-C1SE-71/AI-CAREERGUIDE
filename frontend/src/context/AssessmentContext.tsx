import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react"
import { readStorage, writeStorage } from "../services/storage"
import type {
  AcademicScore,
  AssessmentHistoryItem,
  AssessmentState,
} from "../types/assessment"
import { useAuth } from "./AuthContext"

const initial: AssessmentState = {
  step: 1,
  answers: {},
  cognitive: {},
  scores: [],
  completed: false,
}

const ARCHETYPES: Record<string, string> = {
  I: "Nhà nghiên cứu xã hội & Khoa học",
  R: "Kỹ sư Thực hành & Công nghệ",
  A: "Nhà sáng tạo Nghệ thuật & Nội dung",
  S: "Chuyên gia Kết nối & Phát triển Con người",
  E: "Nhà lãnh đạo & Chiến lược Kinh doanh",
  C: "Chuyên gia Hệ thống & Quản trị Dữ liệu",
}

const FIELD_PROFILES: Array<{
  primaryKey: string
  secondaryKey: string
  field: string
  majorName: string
  majorCode: string
}> = [
  {
    primaryKey: "I",
    secondaryKey: "R",
    field: "Máy tính & Công nghệ thông tin",
    majorName: "Khoa học máy tính",
    majorCode: "7480101",
  },
  {
    primaryKey: "R",
    secondaryKey: "I",
    field: "Công nghệ kỹ thuật",
    majorName: "Công nghệ kỹ thuật điều khiển & Tự động hóa",
    majorCode: "7510301",
  },
  {
    primaryKey: "A",
    secondaryKey: "E",
    field: "Nghệ thuật & Truyền thông số",
    majorName: "Thiết kế đồ họa & Đa phương tiện",
    majorCode: "7210403",
  },
  {
    primaryKey: "S",
    secondaryKey: "A",
    field: "Khoa học Giáo dục & Xã hội",
    majorName: "Tâm lý học giáo dục & Tham vấn",
    majorCode: "7310401",
  },
  {
    primaryKey: "E",
    secondaryKey: "C",
    field: "Kinh doanh & Quản lý",
    majorName: "Marketing số",
    majorCode: "7340115",
  },
  {
    primaryKey: "C",
    secondaryKey: "E",
    field: "Tài chính - Kế toán & Quản trị",
    majorName: "Thương mại điện tử",
    majorCode: "7340122",
  },
]

export function summarizeAssessmentAttempt(
  answers: Record<string, number>,
  cognitive: Record<string, string | number>,
  scores: AcademicScore[],
): Omit<AssessmentHistoryItem, "id" | "createdAt"> {
  const keys = ["R", "I", "A", "S", "E", "C"]
  const dimScores = keys.map((key) => {
    const vals: number[] = []
    for (let i = 1; i <= 5; i++) {
      const v = answers[`${key}${i}`]
      if (typeof v === "number" && v > 0) vals.push(v)
    }
    const pct =
      vals.length > 0
        ? Math.round((vals.reduce((a, b) => a + b, 0) / vals.length / 5) * 100)
        : 60
    return { key, pct }
  })

  const sorted = [...dimScores].sort((a, b) => b.pct - a.pct)
  const top3 = sorted.slice(0, 3)
  const hollandCode = top3.map((d) => d.key).join(" · ")
  const topKey = top3[0]?.key || "I"
  const archetype = ARCHETYPES[topKey] || "Nhà nghiên cứu xã hội & Khoa học"

  const sm = Object.fromEntries((scores || []).map((s) => [s.subject, s.score]))
  const g = (subj: string) => (typeof sm[subj] === "number" ? sm[subj] : 0)
  const blocks = [
    { name: "Khối A00", sum: g("Toán") + g("Vật lý") + g("Hóa học") },
    { name: "Khối A01", sum: g("Toán") + g("Vật lý") + g("Tiếng Anh") },
    { name: "Khối B00", sum: g("Toán") + g("Hóa học") + g("Sinh học") },
    { name: "Khối C00", sum: g("Ngữ văn") + g("Lịch sử") + g("Địa lý") },
    { name: "Khối D01", sum: g("Toán") + g("Ngữ văn") + g("Tiếng Anh") },
    { name: "Khối D07", sum: g("Toán") + g("Hóa học") + g("Tiếng Anh") },
    { name: "Khối D14", sum: g("Ngữ văn") + g("Lịch sử") + g("Tiếng Anh") },
    { name: "Khối D15", sum: g("Ngữ văn") + g("Địa lý") + g("Tiếng Anh") },
  ].sort((a, b) => b.sum - a.sum)

  const bestBlock = blocks[0]?.name || "Khối A00"
  const avgAcademicPct = Math.min(
    98,
    Math.max(55, Math.round(((blocks[0]?.sum || 22.5) / 30) * 100)),
  )
  const cogCount = Object.keys(cognitive || {}).length
  const cogPct = Math.min(96, 80 + Math.min(16, cogCount * 2))

  const matchedProfile =
    FIELD_PROFILES.find((p) => p.primaryKey === topKey) || FIELD_PROFILES[0]
  const topMatchScore = Math.min(
    98,
    Math.max(
      72,
      Math.round(
        0.45 * (top3[0]?.pct || 85) + 0.35 * avgAcademicPct + 0.2 * cogPct,
      ),
    ),
  )

  return {
    hollandCode,
    archetype,
    topField: matchedProfile.field,
    topMajorName: matchedProfile.majorName,
    topMajorCode: matchedProfile.majorCode,
    topMatchScore,
    bestBlock,
    answers: { ...answers },
    cognitive: { ...cognitive },
    scores: [...(scores || [])],
  }
}

interface AssessmentContextValue {
  assessment: AssessmentState
  history: AssessmentHistoryItem[]
  activeHistoryId: string | null
  update: (changes: Partial<AssessmentState>) => void
  reset: () => void
  recordCompletedAttempt: (state: AssessmentState) => AssessmentHistoryItem
  selectHistoryAttempt: (id: string) => void
  deleteHistoryAttempt: (id: string) => void
}

const AssessmentContext = createContext<AssessmentContextValue | null>(null)

export function AssessmentProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const userKey = useMemo(
    () => (user?.email || user?.id || "guest").toLowerCase().trim(),
    [user?.email, user?.id],
  )

  const assessmentStorageKey = `career-guide:assessment:${userKey}`
  const historyStorageKey = `career-guide:assessment-history:${userKey}`

  const [assessment, setAssessment] = useState<AssessmentState>(() =>
    readStorage<AssessmentState>(assessmentStorageKey, initial),
  )
  const [history, setHistory] = useState<AssessmentHistoryItem[]>(() =>
    readStorage<AssessmentHistoryItem[]>(historyStorageKey, []),
  )
  const [activeHistoryId, setActiveHistoryId] = useState<string | null>(null)

  // Reload user-scoped assessment & history when logged-in user changes
  useEffect(() => {
    const loadedAssessment = readStorage<AssessmentState>(
      assessmentStorageKey,
      initial,
    )
    const loadedHistory = readStorage<AssessmentHistoryItem[]>(
      historyStorageKey,
      [],
    )
    setAssessment(loadedAssessment)
    setHistory(loadedHistory)
    setActiveHistoryId(loadedHistory[0]?.id || null)
  }, [assessmentStorageKey, historyStorageKey])

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
          const fallbackAttempt = nextHistory[0]
          const restored: AssessmentState = {
            step: 4,
            answers: { ...fallbackAttempt.answers },
            cognitive: { ...fallbackAttempt.cognitive },
            scores: [...fallbackAttempt.scores],
            aspiration: fallbackAttempt.aspiration
              ? { ...fallbackAttempt.aspiration }
              : undefined,
            completed: true,
            completedAt: fallbackAttempt.createdAt,
          }
          setAssessment(restored)
          writeStorage(assessmentStorageKey, restored)
          setActiveHistoryId(fallbackAttempt.id)
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
