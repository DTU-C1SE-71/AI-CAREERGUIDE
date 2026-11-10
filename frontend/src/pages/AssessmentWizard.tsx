import confetti from "canvas-confetti"
import { motion } from "framer-motion"
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Gamepad2,
  Loader2,
  PackagePlus,
  RotateCcw,
  Sparkles,
  Star,
  Zap,
} from "lucide-react"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useNavigate } from "react-router"
import { AcademicInputForm } from "../components/assessment/AcademicInputForm"
import { LootItemIcon } from "../components/assessment/RoleplaySceneVisual"
import { Button } from "../components/common/Button"
import { Card } from "../components/common/Card"
import { PageContainer } from "../components/layout/PageContainer"
import {
  defaultCognitiveQuestions,
  type CognitiveQuestionItem,
} from "../data/cognitiveQuestions"
import {
  LOOT_SITUATIONS,
  RIASEC_GROUP_LABELS,
  type LootItemCard,
  type RiasecGroup,
} from "../data/roleplayScenes"
import { useAssessment } from "../hooks/useAssessment"
import { apiRequest } from "../services/api"

export interface QuestionItem {
  code: string
  category?: string
  dimension?: string
  dimension_badge?: string
  domain_tag?: string
  question_text: string
  order_index?: number
}

interface ActiveQuestionsResponse {
  title?: string
  riasec_questions?: QuestionItem[]
  cognitive_questions?: Array<{
    code: string
    category?: string
    dimension?: string
    dimension_badge?: string
    domain_tag?: string
    question_text?: string
    order_index?: number
    options?: Array<{
      option_key: string
      trait_code?: string
      title: string
      description: string
    }>
  }>
}

const CANONICAL_30_CODES: string[] = [
  "R1", "R2", "R3", "R4", "R5",
  "I1", "I2", "I3", "I4", "I5",
  "A1", "A2", "A3", "A4", "A5",
  "S1", "S2", "S3", "S4", "S5",
  "E1", "E2", "E3", "E4", "E5",
  "C1", "C2", "C3", "C4", "C5",
]

const defaultRiasecFallback: QuestionItem[] = CANONICAL_30_CODES.map(
  (code, idx) => ({
    code,
    dimension: code[0],
    question_text: code,
    order_index: idx + 1,
  })
)

const RIASEC_ORDER: RiasecGroup[] = ["R", "I", "A", "S", "E", "C"]

interface PickedItemEntry {
  itemId: string
  questionCode: string
  boosted: boolean // true if double-clicked or explicitly boosted to 5 pts
}

export function AssessmentWizard() {
  const { assessment, update, reset, recordCompletedAttempt } = useAssessment()
  const navigate = useNavigate()
  const [step, setStep] = useState<number>(assessment.step || 1)
  const [scores, setScores] = useState<Record<string, number>>(() => {
    const mapped = Object.fromEntries(
      assessment.scores.map((s) => [s.subject, s.score])
    )
    return {
      Toán: mapped["Toán"] ?? 8.2,
      "Ngữ văn": mapped["Ngữ văn"] ?? 7.1,
      "Tiếng Anh": mapped["Tiếng Anh"] ?? 7.8,
      "Vật lý": mapped["Vật lý"] ?? 8.0,
      "Hóa học": mapped["Hóa học"] ?? 7.4,
      "Sinh học": mapped["Sinh học"] ?? 6.9,
      ...mapped,
    }
  })
  const [loading, setLoading] = useState(true)
  const [riasecQuestions, setRiasecQuestions] = useState<QuestionItem[]>(
    defaultRiasecFallback
  )
  const [cognitiveQuestions, setCognitiveQuestions] = useState<
    CognitiveQuestionItem[]
  >(defaultCognitiveQuestions)

  // Step 1: 10 Situations of Item Collection (Multi-select weighted 5 / 4 / 2)
  const [situationIdx, setSituationIdx] = useState<number>(0) // 0..9
  const [situationPicks, setSituationPicks] = useState<
    Record<number, PickedItemEntry[]>
  >(() => {
    // Hydrate from existing assessment.answers if present
    const initial: Record<number, PickedItemEntry[]> = {}
    LOOT_SITUATIONS.forEach((sit, sIdx) => {
      const picks: PickedItemEntry[] = []
      sit.items.forEach((item) => {
        const canonicalIdx = CANONICAL_30_CODES.indexOf(item.questionCode)
        const val =
          assessment.answers[item.questionCode] ??
          assessment.answers[`1-${canonicalIdx}`]
        if (typeof val === "number" && val >= 4 && picks.length < 3) {
          picks.push({
            itemId: item.id,
            questionCode: item.questionCode,
            boosted: val >= 5,
          })
        }
      })
      if (picks.length > 0) {
        initial[sIdx] = picks
      }
    })
    return initial
  })

  // Step 2: Cognitive Quest (0..7)
  const [cogIndex, setCogIndex] = useState(0)
  const autoAdvanceTimer = useRef<number | null>(null)

  useEffect(() => {
    let mounted = true
    async function loadQuestions() {
      try {
        setLoading(true)
        const data = await apiRequest<ActiveQuestionsResponse>(
          "/assessment/active-questions",
          {
            riasec_questions: defaultRiasecFallback,
            cognitive_questions: [],
          }
        )
        if (mounted && data) {
          if (data.riasec_questions && data.riasec_questions.length > 0) {
            setRiasecQuestions(data.riasec_questions)
          }
          if (data.cognitive_questions && data.cognitive_questions.length > 0) {
            const fallbackMap = new Map(
              defaultCognitiveQuestions.map((q) => [q.code, q])
            )
            const parsedCogs: CognitiveQuestionItem[] =
              data.cognitive_questions.map((q) => {
                const fb = fallbackMap.get(q.code)
                const title =
                  fb?.title ||
                  q.dimension_badge ||
                  q.question_text?.split(":")[0]?.trim() ||
                  q.code
                const subtitle =
                  fb?.subtitle ||
                  (q.question_text && q.question_text.includes(":")
                    ? q.question_text.split(":").slice(1).join(":").trim()
                    : q.question_text || "")
                const options =
                  q.options && q.options.length > 0
                    ? q.options.map((opt) => ({
                        option_key: opt.option_key,
                        trait_code: opt.trait_code,
                        title: opt.title,
                        description: opt.description,
                      }))
                    : fb?.options || []

                return {
                  code: q.code,
                  dimension: q.dimension || fb?.dimension,
                  dimension_badge: fb?.dimension_badge || q.dimension_badge,
                  title,
                  subtitle,
                  options,
                }
              })
            setCognitiveQuestions(parsedCogs)
          }
        }
      } catch {
        // Fallback already loaded
      } finally {
        if (mounted) setLoading(false)
      }
    }
    loadQuestions()
    return () => {
      mounted = false
      if (autoAdvanceTimer.current) window.clearTimeout(autoAdvanceTimer.current)
    }
  }, [])

  // Compute hidden scores from `situationPicks` and sync to `assessment.answers`
  // Rules:
  // - 1st picked item OR double-clicked (boosted) item = 5 points
  // - 2nd & 3rd picked items = 4 points
  // - Unselected (skipped) items in any active/visited situation = 2 points
  const syncPicksToAnswers = useCallback(
    (nextPicksMap: Record<number, PickedItemEntry[]>) => {
      const codeScoresList: Record<string, number[]> = {}

      LOOT_SITUATIONS.forEach((sit, sIdx) => {
        const picks = nextPicksMap[sIdx]
        if (!picks || picks.length === 0) return

        sit.items.forEach((item) => {
          const pickIdx = picks.findIndex((p) => p.itemId === item.id)
          let pts = 2 // Default skipped item = 2 points
          if (pickIdx === 0) {
            pts = 5 // 1st selected item = 5 points
          } else if (pickIdx > 0) {
            pts = picks[pickIdx].boosted ? 5 : 4 // 2nd/3rd = 4 points (or 5 if double-clicked)
          }
          if (!codeScoresList[item.questionCode]) {
            codeScoresList[item.questionCode] = []
          }
          codeScoresList[item.questionCode].push(pts)
        })
      })

      const mergedAnswers: Record<string, number> = { ...assessment.answers }
      Object.entries(codeScoresList).forEach(([code, arr]) => {
        const avg = Math.round(arr.reduce((a, b) => a + b, 0) / arr.length)
        const canonicalIdx = CANONICAL_30_CODES.indexOf(code)
        mergedAnswers[code] = avg
        if (canonicalIdx >= 0) {
          mergedAnswers[`1-${canonicalIdx}`] = avg
        }
      })

      update({ answers: mergedAnswers })
    },
    [assessment.answers, update]
  )

  const currentSituation =
    LOOT_SITUATIONS[situationIdx] || LOOT_SITUATIONS[0]
  const currentPicks = situationPicks[situationIdx] || []

  // Toggle selection on single click (up to 3 items per situation)
  const handleItemClick = useCallback(
    (item: LootItemCard) => {
      setSituationPicks((prev) => {
        const current = prev[situationIdx] ? [...prev[situationIdx]] : []
        const existingIdx = current.findIndex((p) => p.itemId === item.id)

        let updated: PickedItemEntry[]
        if (existingIdx >= 0) {
          // Clicking an already-selected card unselects it (back to 2 pts)
          updated = current.filter((p) => p.itemId !== item.id)
        } else {
          // Selecting a new card (max 3 cards per situation)
          const isFirst = current.length === 0
          const newEntry: PickedItemEntry = {
            itemId: item.id,
            questionCode: item.questionCode,
            boosted: isFirst, // 1st selected automatically gets 5 pts
          }
          if (current.length < 3) {
            updated = [...current, newEntry]
          } else {
            // Replace the 3rd pick if already at 3 picks
            updated = [current[0], current[1], newEntry]
          }
        }

        const nextMap = { ...prev, [situationIdx]: updated }
        syncPicksToAnswers(nextMap)
        return nextMap
      })
    },
    [situationIdx, syncPicksToAnswers]
  )

  // Double-click (or clicking ⭐ boost button) sets the item to 5 points (Rất thích)
  const handleItemBoost5 = useCallback(
    (item: LootItemCard, e?: React.MouseEvent) => {
      if (e) e.stopPropagation()
      setSituationPicks((prev) => {
        const current = prev[situationIdx] ? [...prev[situationIdx]] : []
        const existingIdx = current.findIndex((p) => p.itemId === item.id)

        let updated: PickedItemEntry[]
        if (existingIdx >= 0) {
          updated = current.map((p, i) =>
            i === existingIdx ? { ...p, boosted: true } : p
          )
        } else {
          const newEntry: PickedItemEntry = {
            itemId: item.id,
            questionCode: item.questionCode,
            boosted: true,
          }
          if (current.length < 3) {
            updated = [...current, newEntry]
          } else {
            updated = [current[0], current[1], newEntry]
          }
        }

        const nextMap = { ...prev, [situationIdx]: updated }
        syncPicksToAnswers(nextMap)
        return nextMap
      })
    },
    [situationIdx, syncPicksToAnswers]
  )

  // Count how many situations have at least 1 item picked
  const completedSituationsCount = useMemo(() => {
    return LOOT_SITUATIONS.filter(
      (_, idx) => (situationPicks[idx]?.length || 0) > 0
    ).length
  }, [situationPicks])

  // Count how many of the 30 canonical codes have answers
  const totalRiasecAnswered = useMemo(() => {
    return CANONICAL_30_CODES.filter((code, idx) => {
      const val = assessment.answers[code] ?? assessment.answers[`1-${idx}`]
      return typeof val === "number" && val >= 1 && val <= 5
    }).length
  }, [assessment.answers])

  // Live RIASEC scores by group for the top inventory bar
  const riasecGroupScores = useMemo(() => {
    const totals: Record<RiasecGroup, number> = {
      R: 0,
      I: 0,
      A: 0,
      S: 0,
      E: 0,
      C: 0,
    }
    CANONICAL_30_CODES.forEach((code, idx) => {
      const g = code[0] as RiasecGroup
      const val = assessment.answers[code] ?? assessment.answers[`1-${idx}`]
      if (typeof val === "number" && val > 0) {
        totals[g] += val * 4 // Max 5 items * 5 pts * 4 = 100%
      }
    })
    return totals
  }, [assessment.answers])

  const totalCognitiveAnswered = useMemo(() => {
    return cognitiveQuestions.filter((q, idx) => {
      const v = assessment.cognitive[q.code] ?? assessment.cognitive[`2-${idx}`]
      return v !== undefined && v !== null && String(v).trim() !== ""
    }).length
  }, [assessment.cognitive, cognitiveQuestions])

  // Minimum 3 situations (= 18 questions across all 6 RIASEC groups) or 5+ situations (= all 30 questions)
  const allRiasecGroupsCovered = useMemo(() => {
    return totalRiasecAnswered >= 18 || completedSituationsCount >= 3
  }, [totalRiasecAnswered, completedSituationsCount])

  const currentCog = cognitiveQuestions[cogIndex] || cognitiveQuestions[0]
  const handleSelectCognitive = useCallback(
    (optionKey: string) => {
      const qKey = currentCog.code || `2-${cogIndex}`
      update({
        cognitive: {
          ...assessment.cognitive,
          [qKey]: optionKey,
          [`2-${cogIndex}`]: optionKey,
        },
      })

      if (autoAdvanceTimer.current) {
        window.clearTimeout(autoAdvanceTimer.current)
      }
      autoAdvanceTimer.current = window.setTimeout(() => {
        if (cogIndex < cognitiveQuestions.length - 1) {
          setCogIndex((prev) =>
            Math.min(cognitiveQuestions.length - 1, prev + 1)
          )
        }
      }, 240)
    },
    [
      currentCog.code,
      cogIndex,
      assessment.cognitive,
      update,
      cognitiveQuestions.length,
    ]
  )

  // Keyboard shortcuts: 1-6 to toggle items in Step 1, Enter/ArrowRight to advance situation
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (
        document.activeElement?.tagName === "INPUT" ||
        document.activeElement?.tagName === "TEXTAREA"
      ) {
        return
      }
      if (step === 1) {
        const num = Number(e.key)
        if (num >= 1 && num <= 6) {
          e.preventDefault()
          const targetItem = currentSituation.items[num - 1]
          if (targetItem) handleItemClick(targetItem)
        } else if (e.key === "ArrowRight" || e.key === "Enter") {
          if (situationIdx < LOOT_SITUATIONS.length - 1) {
            setSituationIdx((p) => p + 1)
          }
        } else if (e.key === "ArrowLeft") {
          setSituationIdx((p) => Math.max(0, p - 1))
        }
      } else if (step === 2) {
        const keyMap: Record<string, string> = {
          "1": "A",
          "2": "B",
          "3": "C",
          "4": "D",
          a: "A",
          b: "B",
          c: "C",
          d: "D",
          A: "A",
          B: "B",
          C: "C",
          D: "D",
        }
        if (keyMap[e.key]) {
          e.preventDefault()
          handleSelectCognitive(keyMap[e.key])
        } else if (e.key === "ArrowRight") {
          setCogIndex((p) => Math.min(cognitiveQuestions.length - 1, p + 1))
        } else if (e.key === "ArrowLeft") {
          setCogIndex((p) => Math.max(0, p - 1))
        }
      }
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [
    step,
    currentSituation.items,
    handleItemClick,
    situationIdx,
    handleSelectCognitive,
    cognitiveQuestions.length,
  ])

  const resetAllAnswers = () => {
    reset()
    setSituationPicks({})
    setSituationIdx(0)
    setCogIndex(0)
    setStep(1)
  }

  const handleCompleteAssessment = () => {
    // Ensure any unvisited question codes default to 2 pts so all 30 codes are complete
    const finalAnswers: Record<string, number> = { ...assessment.answers }
    CANONICAL_30_CODES.forEach((code, idx) => {
      const val = finalAnswers[code] ?? finalAnswers[`1-${idx}`]
      const safeVal = typeof val === "number" && val > 0 ? val : 2
      finalAnswers[code] = safeVal
      finalAnswers[`1-${idx}`] = safeVal
    })

    const normalizedScores = Object.entries(scores).map(([subject, score]) => ({
      subject,
      score,
      zScore: (score - 7.1) / 1.2,
    }))

    recordCompletedAttempt({
      ...assessment,
      answers: finalAnswers,
      step: 3,
      scores: normalizedScores,
      completed: true,
    })

    const riasecMap: Record<string, number> = {}
    riasecQuestions.forEach((q, idx) => {
      const val = finalAnswers[q.code] ?? finalAnswers[`1-${idx}`]
      if (val !== undefined && val !== null) riasecMap[q.code] = Number(val)
    })
    const cogMap: Record<string, string> = {}
    cognitiveQuestions.forEach((q, idx) => {
      const val =
        assessment.cognitive[q.code] ?? assessment.cognitive[`2-${idx}`]
      if (val) cogMap[q.code] = String(val)
    })

    apiRequest("/assessment/submit", null, {
      method: "POST",
      body: JSON.stringify({
        riasec_answers: riasecMap,
        cognitive_answers: cogMap,
      }),
    }).catch((err) => console.log("Background submit response:", err))

    if (Object.keys(scores).length > 0) {
      apiRequest("/assessment/grades", null, {
        method: "POST",
        body: JSON.stringify({
          academic_year: "2025-2026",
          semester: "HK1-L12",
          grades: scores,
        }),
      }).catch((err) => console.log("Background grades submit notice:", err))
    }

    confetti({
      particleCount: 75,
      spread: 65,
      origin: { y: 0.6 },
    })
    navigate("/dashboard")
  }

  const currentCogValue =
    assessment.cognitive[currentCog.code] ??
    assessment.cognitive[`2-${cogIndex}`]

  return (
    <section className="py-5 sm:py-7">
      <PageContainer className="max-w-4xl">
        {/* Top Game HUD Bar (Liquid Glass, Unified Sky/Cyan Palette) */}
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/80 bg-white/75 px-4 py-3 shadow-[0_8px_28px_rgba(14,165,233,0.08)] backdrop-blur-xl">
          <div className="flex items-center gap-2.5">
            <span className="grid size-9 place-items-center rounded-xl bg-gradient-to-br from-sky-500 to-cyan-500 text-white shadow-sm">
              <Gamepad2 className="size-5" />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-black tracking-tight text-slate-900">
                  Thu Thập Vật Phẩm Định Hướng
                </h1>
                <span className="rounded-full bg-sky-100 px-2 py-0.5 text-[10px] font-black text-sky-700">
                  ⚡ Tốc độ &lt; 2 phút
                </span>
              </div>
              <p className="text-[11px] font-semibold text-slate-500">
                10 Tình huống · Chọn 2–3 thẻ/chặng (Chọn đầu/Đúp = 5đ · Chọn thứ 2–3 = 4đ · Bỏ qua = 2đ)
              </p>
            </div>
          </div>

          {/* 3-Quest Step Switcher */}
          <div className="flex items-center gap-1.5">
            {[
              {
                id: 1,
                label: `1. Vật phẩm (${completedSituationsCount}/10)`,
                done: allRiasecGroupsCovered,
              },
              {
                id: 2,
                label: `2. Phản xạ (${totalCognitiveAnswered}/8)`,
                done: totalCognitiveAnswered >= cognitiveQuestions.length,
              },
              { id: 3, label: "3. Học lực", done: assessment.completed },
            ].map((s) => {
              const active = step === s.id
              return (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => {
                    if (
                      s.id === 1 ||
                      (s.id === 2 && allRiasecGroupsCovered) ||
                      (s.id === 3 && allRiasecGroupsCovered)
                    ) {
                      setStep(s.id)
                      update({ step: s.id })
                    }
                  }}
                  className={`flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-extrabold transition ${
                    active
                      ? "bg-sky-600 text-white shadow-sm"
                      : s.done
                        ? "bg-sky-50 text-sky-700 border border-sky-200"
                        : "bg-slate-100/80 text-slate-500"
                  }`}
                >
                  {s.done && !active && (
                    <Check className="size-3.5 text-sky-600" />
                  )}
                  <span>{s.label}</span>
                </button>
              )
            })}
            {(completedSituationsCount > 0 || totalCognitiveAnswered > 0) && (
              <button
                type="button"
                onClick={resetAllAnswers}
                title="Làm mới túi vật phẩm"
                className="ml-1 grid size-8 place-items-center rounded-xl border border-slate-200/80 bg-white/80 text-slate-500 transition hover:border-sky-300 hover:text-sky-700"
              >
                <RotateCcw className="size-3.5" />
              </button>
            )}
          </div>
        </div>

        {loading && step < 3 && (
          <div className="mb-4 flex items-center justify-center gap-2 rounded-2xl border border-sky-100 bg-white/70 p-2.5 text-slate-500 backdrop-blur-md">
            <Loader2 className="size-4 animate-spin text-sky-600" />
            <span className="text-xs font-semibold">
              Đang đồng bộ kho vật phẩm...
            </span>
          </div>
        )}

        {/* ==================== STEP 1: MECHANISM 3 - LOOT COLLECTION (10 SITUATIONS × 6 CARDS) ==================== */}
        {step === 1 && (
          <div className="space-y-4">
            {/* 10-Situation Progress Bar + Live 6-Axis Inventory Meter */}
            <div className="rounded-2xl border border-white/85 bg-white/75 p-3.5 shadow-[0_8px_24px_rgba(14,165,233,0.06)] backdrop-blur-xl">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-1.5">
                  {LOOT_SITUATIONS.map((sit, idx) => {
                    const count = situationPicks[idx]?.length || 0
                    const isCurr = idx === situationIdx
                    return (
                      <button
                        key={sit.situationIndex}
                        type="button"
                        onClick={() => setSituationIdx(idx)}
                        className={`flex h-7 min-w-7 items-center justify-center rounded-lg px-2 text-xs font-black transition-all ${
                          isCurr
                            ? "bg-gradient-to-r from-sky-500 to-cyan-600 text-white shadow-sm scale-105"
                            : count > 0
                              ? "border border-sky-200 bg-sky-50 text-sky-700 hover:bg-sky-100"
                              : "bg-slate-100/80 text-slate-500 hover:bg-slate-200/70"
                        }`}
                      >
                        {idx + 1}
                      </button>
                    )
                  })}
                </div>

                {/* Live 6-Group Mini Energy Pills */}
                <div className="flex flex-wrap items-center gap-1.5">
                  {RIASEC_ORDER.map((g) => (
                    <div
                      key={g}
                      className="flex items-center gap-1 rounded-lg border border-sky-100 bg-sky-50/70 px-2 py-1 text-[10px] font-black text-sky-800"
                      title={RIASEC_GROUP_LABELS[g].role}
                    >
                      <span>{g}</span>
                      <div className="h-1.5 w-8 overflow-hidden rounded-full bg-sky-200/70">
                        <div
                          className="h-full rounded-full bg-sky-600 transition-all duration-300"
                          style={{
                            width: `${Math.min(100, riasecGroupScores[g])}%`,
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Situation Header Banner */}
              <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-sky-900 via-sky-800 to-cyan-900 px-5 py-4 text-white">
                <div className="pointer-events-none absolute -right-10 -top-10 h-32 w-32 rounded-full bg-cyan-400/20 blur-2xl" />
                <div className="relative z-10 flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <span className="inline-flex items-center gap-1.5 rounded-full border border-white/20 bg-white/10 px-2.5 py-0.5 text-[10px] font-black uppercase tracking-wider text-cyan-200">
                      <Sparkles className="size-3" />
                      {currentSituation.badge}
                    </span>
                    <h2 className="mt-1.5 text-lg sm:text-xl font-black tracking-tight text-white">
                      {currentSituation.title}
                    </h2>
                    <p className="mt-0.5 text-xs font-medium text-sky-200">
                      {currentSituation.contextPrompt}
                    </p>
                  </div>

                  {/* Current Situation Bag Counter */}
                  <div className="flex items-center gap-2 rounded-2xl border border-white/20 bg-white/10 px-3.5 py-2 backdrop-blur-md">
                    <PackagePlus className="size-4 text-cyan-300" />
                    <div className="text-right">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-sky-200">
                        Đã chọn
                      </p>
                      <p className="text-sm font-black text-white">
                        {currentPicks.length} / 3 thẻ
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* 6 Interactive Loot / Action Cards (Multi-select Weighted) */}
            <motion.div
              key={currentSituation.situationIndex}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.18 }}
              className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3"
            >
              {currentSituation.items.map((item, idx) => {
                const pickIndex = currentPicks.findIndex(
                  (p) => p.itemId === item.id
                )
                const isSelected = pickIndex >= 0
                const isFivePoints =
                  pickIndex === 0 ||
                  (pickIndex > 0 && currentPicks[pickIndex]?.boosted)
                const pointsEarned = isSelected ? (isFivePoints ? 5 : 4) : 2

                const selectedRank = !isSelected
                  ? "NONE"
                  : isFivePoints
                    ? "FIRST_OR_BOOST"
                    : "SECOND_OR_THIRD"

                return (
                  <div
                    key={item.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => handleItemClick(item)}
                    onDoubleClick={(e) => handleItemBoost5(item, e)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault()
                        handleItemClick(item)
                      }
                    }}
                    className={`group relative flex cursor-pointer select-none flex-col justify-between rounded-[22px] border p-4 text-left transition-all duration-150 ${
                      isFivePoints
                        ? "border-sky-400 bg-gradient-to-br from-sky-600 via-sky-500 to-cyan-600 text-white shadow-[0_14px_30px_rgba(14,165,233,0.28)] -translate-y-0.5"
                        : isSelected
                          ? "border-sky-400 bg-sky-50/95 text-slate-900 shadow-[0_10px_24px_rgba(14,165,233,0.14)] -translate-y-0.5"
                          : "border-white/85 bg-white/80 text-slate-800 shadow-[0_6px_20px_rgba(14,165,233,0.06)] backdrop-blur-xl hover:-translate-y-0.5 hover:border-sky-300 hover:bg-white"
                    }`}
                  >
                    <div>
                      {/* Card Top Row: Icon + Group Tag + Score Badge */}
                      <div className="flex items-start justify-between gap-2">
                        <LootItemIcon
                          iconKey={item.iconKey}
                          selectedRank={selectedRank}
                        />

                        <div className="flex flex-col items-end gap-1">
                          <span
                            className={`rounded-full px-2.5 py-0.5 text-[10px] font-black tracking-wide ${
                              isFivePoints
                                ? "bg-white text-sky-700 shadow-sm"
                                : isSelected
                                  ? "bg-sky-600 text-white"
                                  : "bg-slate-100 text-slate-500"
                            }`}
                          >
                            {isFivePoints
                              ? `⭐ Rất thích · +5đ`
                              : isSelected
                                ? `✓ Đã chọn #${pickIndex + 1} · +4đ`
                                : `Phím ${idx + 1} · Mặc định 2đ`}
                          </span>

                          {/* One-tap 5pt Upgrade Button when selected at 4pts */}
                          {isSelected && !isFivePoints && (
                            <button
                              type="button"
                              onClick={(e) => handleItemBoost5(item, e)}
                              className="inline-flex items-center gap-1 rounded-full border border-sky-300 bg-white px-2 py-0.5 text-[10px] font-extrabold text-sky-700 transition hover:bg-sky-600 hover:text-white"
                              title="Bấm đúp hoặc nhấn vào đây để nâng lên 5 điểm"
                            >
                              <Star className="size-2.5 fill-current" />
                              Nâng lên 5đ
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Item Title & Concise Action */}
                      <div className="mt-3.5">
                        <span
                          className={`text-[10px] font-extrabold uppercase tracking-wider ${
                            isFivePoints
                              ? "text-cyan-100"
                              : isSelected
                                ? "text-sky-700"
                                : "text-sky-600"
                          }`}
                        >
                          {RIASEC_GROUP_LABELS[item.group].short} · Mã{" "}
                          {item.questionCode}
                        </span>
                        <h3
                          className={`mt-0.5 text-sm font-black leading-snug ${
                            isFivePoints ? "text-white" : "text-slate-900"
                          }`}
                        >
                          {item.itemName}
                        </h3>
                        <p
                          className={`mt-1 text-xs leading-relaxed ${
                            isFivePoints
                              ? "text-sky-50"
                              : isSelected
                                ? "text-slate-600"
                                : "text-slate-500"
                          }`}
                        >
                          {item.actionDesc}
                        </p>
                      </div>
                    </div>

                    {/* Bottom subtle status bar */}
                    <div
                      className={`mt-3 flex items-center justify-between border-t pt-2 text-[10px] font-bold ${
                        isFivePoints
                          ? "border-white/20 text-sky-100"
                          : isSelected
                            ? "border-sky-200/80 text-sky-700"
                            : "border-slate-100 text-slate-400"
                      }`}
                    >
                      <span>
                        {isFivePoints
                          ? "Vật phẩm chủ lực (5/5 điểm)"
                          : isSelected
                            ? "Đúp chuột để nâng 5/5 điểm"
                            : "Click để thu thập vật phẩm"}
                      </span>
                      <span className="font-black">+{pointsEarned}đ</span>
                    </div>
                  </div>
                )
              })}
            </motion.div>
          </div>
        )}

        {/* ==================== STEP 2: COGNITIVE REFLEX QUEST ==================== */}
        {step === 2 && currentCog && (
          <motion.div
            key={currentCog.code}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className="rounded-[26px] border border-white/85 bg-white/75 p-5 sm:p-6 shadow-[0_16px_40px_rgba(14,165,233,0.1)] backdrop-blur-2xl"
          >
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-sky-100 px-3 py-1 text-xs font-black text-sky-800">
                <Zap className="size-3.5 text-sky-600" />
                Thử thách Phản Xạ {cogIndex + 1}/{cognitiveQuestions.length} ·{" "}
                {currentCog.dimension_badge}
              </span>

              <div className="flex items-center gap-1">
                {cognitiveQuestions.map((q, idx) => {
                  const done =
                    assessment.cognitive[q.code] !== undefined ||
                    assessment.cognitive[`2-${idx}`] !== undefined
                  return (
                    <button
                      key={q.code}
                      type="button"
                      onClick={() => setCogIndex(idx)}
                      className={`size-6 rounded-lg text-[11px] font-black transition ${
                        idx === cogIndex
                          ? "bg-sky-600 text-white"
                          : done
                            ? "bg-sky-100 text-sky-700"
                            : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {idx + 1}
                    </button>
                  )
                })}
              </div>
            </div>

            <div className="mb-5 rounded-2xl bg-gradient-to-r from-sky-900 via-sky-800 to-cyan-900 p-5 text-white">
              <p className="text-[11px] font-bold uppercase tracking-wider text-cyan-300">
                Tình huống quyết định #{cogIndex + 1}
              </p>
              <h2 className="mt-1 text-base sm:text-lg font-black leading-snug">
                {currentCog.subtitle}
              </h2>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {currentCog.options.map((opt) => {
                const isSelected = String(currentCogValue) === opt.option_key
                return (
                  <button
                    key={opt.option_key}
                    type="button"
                    onClick={() => handleSelectCognitive(opt.option_key)}
                    className={`group flex flex-col justify-between rounded-2xl border p-4 text-left transition-all ${
                      isSelected
                        ? "border-sky-500 bg-gradient-to-br from-sky-500 to-cyan-600 text-white shadow-[0_12px_26px_rgba(14,165,233,0.25)] -translate-y-0.5"
                        : "border-sky-100 bg-white/90 text-slate-800 hover:-translate-y-0.5 hover:border-sky-400 hover:bg-sky-50/60"
                    }`}
                  >
                    <div>
                      <div className="mb-2 flex items-center justify-between">
                        <span
                          className={`inline-flex size-7 items-center justify-center rounded-lg text-xs font-black ${
                            isSelected
                              ? "bg-white text-sky-700"
                              : "bg-sky-100 text-sky-800"
                          }`}
                        >
                          {opt.option_key}
                        </span>
                        <span
                          className={`text-[10px] font-bold ${
                            isSelected ? "text-sky-100" : "text-slate-400"
                          }`}
                        >
                          Phím {opt.option_key}
                        </span>
                      </div>
                      <h3 className="text-sm font-black leading-snug">
                        {opt.title}
                      </h3>
                      <p
                        className={`mt-1.5 text-xs leading-relaxed line-clamp-2 ${
                          isSelected ? "text-sky-50" : "text-slate-500"
                        }`}
                      >
                        {opt.description}
                      </p>
                    </div>
                  </button>
                )
              })}
            </div>
          </motion.div>
        )}

        {/* ==================== STEP 3: ACADEMIC POWER-UP ==================== */}
        {step === 3 && (
          <Card className="p-5 sm:p-6">
            <AcademicInputForm
              scores={scores}
              onChange={(subject, value) =>
                setScores((prev) => ({ ...prev, [subject]: value }))
              }
            />
          </Card>
        )}

        {/* Footer Quest Action Bar */}
        <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
          <Button
            variant="ghost"
            icon={ArrowLeft}
            disabled={step === 1 && situationIdx === 0}
            onClick={() => {
              if (step === 1 && situationIdx > 0) {
                setSituationIdx((p) => Math.max(0, p - 1))
                return
              }
              if (step === 2 && cogIndex > 0) {
                setCogIndex((p) => Math.max(0, p - 1))
                return
              }
              const prevStep = Math.max(1, step - 1)
              setStep(prevStep)
              update({ step: prevStep })
            }}
          >
            Quay lại
          </Button>

          <div className="flex flex-wrap items-center gap-2.5">
            {step === 1 && situationIdx < LOOT_SITUATIONS.length - 1 && (
              <Button
                variant={allRiasecGroupsCovered ? "secondary" : "primary"}
                icon={ArrowRight}
                onClick={() => {
                  // If the user hasn't picked anything in this situation yet and clicks next,
                  // record 2 points for all 6 items in this situation
                  if ((situationPicks[situationIdx]?.length || 0) === 0) {
                    const nextAnswers: Record<string, number> = {
                      ...assessment.answers,
                    }
                    currentSituation.items.forEach((item) => {
                      if (nextAnswers[item.questionCode] === undefined) {
                        const cIdx = CANONICAL_30_CODES.indexOf(
                          item.questionCode
                        )
                        nextAnswers[item.questionCode] = 2
                        if (cIdx >= 0) nextAnswers[`1-${cIdx}`] = 2
                      }
                    })
                    update({ answers: nextAnswers })
                  }
                  setSituationIdx((p) =>
                    Math.min(LOOT_SITUATIONS.length - 1, p + 1)
                  )
                }}
              >
                Chặng tiếp ({situationIdx + 2}/10)
              </Button>
            )}

            {step === 1 && allRiasecGroupsCovered && (
              <Button
                icon={ArrowRight}
                onClick={() => {
                  // Fill default 2 pts for any remaining unvisited codes
                  const filledAnswers: Record<string, number> = {
                    ...assessment.answers,
                  }
                  CANONICAL_30_CODES.forEach((code, idx) => {
                    if (
                      filledAnswers[code] === undefined &&
                      filledAnswers[`1-${idx}`] === undefined
                    ) {
                      filledAnswers[code] = 2
                      filledAnswers[`1-${idx}`] = 2
                    }
                  })
                  update({ answers: filledAnswers, step: 2 })
                  setStep(2)
                  window.scrollTo({ top: 0, behavior: "smooth" })
                }}
              >
                Sang Bước 2: Phản Xạ ({completedSituationsCount}/10 chặng)
              </Button>
            )}

            {step === 2 && (
              <Button
                icon={ArrowRight}
                disabled={totalCognitiveAnswered < cognitiveQuestions.length}
                onClick={() => {
                  setStep(3)
                  update({ step: 3 })
                  window.scrollTo({ top: 0, behavior: "smooth" })
                }}
              >
                Sang Bước 3: Điểm Học Tập ({totalCognitiveAnswered}/
                {cognitiveQuestions.length})
              </Button>
            )}

            {step === 3 && (
              <Button
                icon={Check}
                disabled={Object.values(scores).filter((v) => v > 0).length < 3}
                onClick={handleCompleteAssessment}
              >
                Mở Khóa Bản Đồ 435 Ngành
              </Button>
            )}
          </div>
        </div>
      </PageContainer>
    </section>
  )
}
