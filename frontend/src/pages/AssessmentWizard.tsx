import confetti from "canvas-confetti"
import { AnimatePresence, motion, useMotionValue, useTransform } from "framer-motion"
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Layers,
  Loader2,
  RotateCcw,
  Sliders,
  Sparkles,
  Zap,
} from "lucide-react"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useNavigate } from "react-router"
import { AcademicInputForm } from "../components/assessment/AcademicInputForm"
import {
  LiveRiasecHexagon,
  OnetItemVisualIcon,
} from "../components/assessment/OnetSwipeCardVisual"
import { Button } from "../components/common/Button"
import { Card } from "../components/common/Card"
import { PageContainer } from "../components/layout/PageContainer"
import {
  defaultCognitiveQuestions,
  type CognitiveQuestionItem,
} from "../data/cognitiveQuestions"
import {
  ONET_MINI_IP_ITEMS,
  ONET_REACTION_SCALE,
  RIASEC_META,
  type OnetMiniIpItem,
  type RiasecDimension,
} from "../data/onetMiniIpQuestions"
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

const RIASEC_ORDER: RiasecDimension[] = ["R", "I", "A", "S", "E", "C"]

const defaultRiasecFallback: QuestionItem[] = CANONICAL_30_CODES.map(
  (code, idx) => {
    const found = ONET_MINI_IP_ITEMS.find((i) => i.code === code)
    return {
      code,
      dimension: code[0],
      question_text: found?.titleVi || code,
      order_index: idx + 1,
    }
  }
)

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

  // Step 1 Mode: 'swipe' (O*NET Mini-IP Swipe Cards) | 'radar' (1-Screen RPG Fast Radar)
  const [step1Mode, setStep1Mode] = useState<"swipe" | "radar">("swipe")
  const [cardIndex, setCardIndex] = useState<number>(() => {
    const firstUnanswered = ONET_MINI_IP_ITEMS.findIndex((item) => {
      const cIdx = CANONICAL_30_CODES.indexOf(item.code)
      return (
        assessment.answers[item.code] === undefined &&
        assessment.answers[`1-${cIdx}`] === undefined
      )
    })
    return firstUnanswered >= 0 ? firstUnanswered : 0
  })
  const [swipeDir, setSwipeDir] = useState<number>(1)

  // Step 2: Cognitive Quest
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
        // Fallback already active
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

  const currentCard: OnetMiniIpItem =
    ONET_MINI_IP_ITEMS[cardIndex] || ONET_MINI_IP_ITEMS[0]

  const currentCardCanonicalIdx = CANONICAL_30_CODES.indexOf(currentCard.code)
  const currentCardValue =
    assessment.answers[currentCard.code] ??
    assessment.answers[`1-${currentCardCanonicalIdx}`]

  // Rate current O*NET card (1..5) and advance smoothly
  const rateCurrentCard = useCallback(
    (value: number, dir = 1) => {
      setSwipeDir(dir)
      const cIdx = CANONICAL_30_CODES.indexOf(currentCard.code)
      const nextAnswers = {
        ...assessment.answers,
        [currentCard.code]: value,
        ...(cIdx >= 0 ? { [`1-${cIdx}`]: value } : {}),
      }
      update({ answers: nextAnswers })

      if (autoAdvanceTimer.current) window.clearTimeout(autoAdvanceTimer.current)
      autoAdvanceTimer.current = window.setTimeout(() => {
        if (cardIndex < ONET_MINI_IP_ITEMS.length - 1) {
          setCardIndex((prev) => prev + 1)
        }
      }, 150)
    },
    [currentCard.code, assessment.answers, update, cardIndex]
  )

  // Apply 1-screen Radar Slider score (1..5) to all 5 items of a RIASEC dimension
  const setGroupLevel = useCallback(
    (dim: RiasecDimension, levelValue: number) => {
      const nextAnswers = { ...assessment.answers }
      ONET_MINI_IP_ITEMS.filter((i) => i.dimension === dim).forEach((item) => {
        const cIdx = CANONICAL_30_CODES.indexOf(item.code)
        nextAnswers[item.code] = levelValue
        if (cIdx >= 0) nextAnswers[`1-${cIdx}`] = levelValue
      })
      update({ answers: nextAnswers })
    },
    [assessment.answers, update]
  )

  // Stats across 6 RIASEC dimensions
  const riasecGroupCounts = useMemo(() => {
    const counts: Record<RiasecDimension, number> = {
      R: 0,
      I: 0,
      A: 0,
      S: 0,
      E: 0,
      C: 0,
    }
    CANONICAL_30_CODES.forEach((code, idx) => {
      const val = assessment.answers[code] ?? assessment.answers[`1-${idx}`]
      if (typeof val === "number" && val >= 1 && val <= 5) {
        counts[code[0] as RiasecDimension] += 1
      }
    })
    return counts
  }, [assessment.answers])

  const riasecGroupPct = useMemo(() => {
    const pct: Record<RiasecDimension, number> = {
      R: 20,
      I: 20,
      A: 20,
      S: 20,
      E: 20,
      C: 20,
    }
    RIASEC_ORDER.forEach((dim) => {
      const vals = ONET_MINI_IP_ITEMS.filter((i) => i.dimension === dim)
        .map((i) => {
          const cIdx = CANONICAL_30_CODES.indexOf(i.code)
          return assessment.answers[i.code] ?? assessment.answers[`1-${cIdx}`]
        })
        .filter((v): v is number => typeof v === "number" && v > 0)
      if (vals.length > 0) {
        const avg = vals.reduce((a, b) => a + b, 0) / vals.length
        pct[dim] = Math.round((avg / 5) * 100)
      }
    })
    return pct
  }, [assessment.answers])

  const riasecGroupAvg = useMemo(() => {
    const avgs: Record<RiasecDimension, number> = {
      R: 3,
      I: 3,
      A: 3,
      S: 3,
      E: 3,
      C: 3,
    }
    RIASEC_ORDER.forEach((dim) => {
      const vals = ONET_MINI_IP_ITEMS.filter((i) => i.dimension === dim)
        .map((i) => {
          const cIdx = CANONICAL_30_CODES.indexOf(i.code)
          return assessment.answers[i.code] ?? assessment.answers[`1-${cIdx}`]
        })
        .filter((v): v is number => typeof v === "number" && v > 0)
      if (vals.length > 0) {
        avgs[dim] = Number(
          (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1)
        )
      }
    })
    return avgs
  }, [assessment.answers])

  const totalRiasecAnswered = useMemo(
    () => Object.values(riasecGroupCounts).reduce((a, b) => a + b, 0),
    [riasecGroupCounts]
  )

  const allRiasecGroupsCovered = useMemo(() => {
    return (
      totalRiasecAnswered >= 18 &&
      RIASEC_ORDER.every((dim) => riasecGroupCounts[dim] >= 2)
    )
  }, [totalRiasecAnswered, riasecGroupCounts])

  const totalCognitiveAnswered = useMemo(() => {
    return cognitiveQuestions.filter((q, idx) => {
      const v = assessment.cognitive[q.code] ?? assessment.cognitive[`2-${idx}`]
      return v !== undefined && v !== null && String(v).trim() !== ""
    }).length
  }, [assessment.cognitive, cognitiveQuestions])

  const currentCog = cognitiveQuestions[cogIndex] || cognitiveQuestions[0]
  const currentCogValue =
    assessment.cognitive[currentCog.code] ??
    assessment.cognitive[`2-${cogIndex}`]

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

      if (autoAdvanceTimer.current) window.clearTimeout(autoAdvanceTimer.current)
      autoAdvanceTimer.current = window.setTimeout(() => {
        if (cogIndex < cognitiveQuestions.length - 1) {
          setCogIndex((prev) =>
            Math.min(cognitiveQuestions.length - 1, prev + 1)
          )
        }
      }, 200)
    },
    [
      currentCog.code,
      cogIndex,
      assessment.cognitive,
      update,
      cognitiveQuestions.length,
    ]
  )

  // Keyboard shortcuts
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (
        document.activeElement?.tagName === "INPUT" ||
        document.activeElement?.tagName === "TEXTAREA"
      ) {
        return
      }
      if (step === 1 && step1Mode === "swipe") {
        if (["1", "2", "3", "4", "5"].includes(e.key)) {
          e.preventDefault()
          const val = Number(e.key)
          rateCurrentCard(val, val >= 4 ? 1 : val <= 2 ? -1 : 1)
        } else if (e.key === "ArrowRight") {
          e.preventDefault()
          rateCurrentCard(4, 1) // Quick swipe right = Thích (4)
        } else if (e.key === "ArrowLeft") {
          e.preventDefault()
          rateCurrentCard(2, -1) // Quick swipe left = Không thích (2)
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
    step1Mode,
    rateCurrentCard,
    handleSelectCognitive,
    cognitiveQuestions.length,
  ])

  const resetAllAnswers = () => {
    reset()
    setCardIndex(0)
    setCogIndex(0)
    setStep(1)
  }

  const handleCompleteAssessment = () => {
    const finalAnswers: Record<string, number> = { ...assessment.answers }
    CANONICAL_30_CODES.forEach((code, idx) => {
      const val = finalAnswers[code] ?? finalAnswers[`1-${idx}`]
      const safeVal = typeof val === "number" && val > 0 ? val : 3
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

  return (
    <section className="py-5 sm:py-7">
      <PageContainer className="max-w-3xl">
        {/* Top Liquid Glass Bar */}
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/85 bg-white/75 px-4 py-3 shadow-[0_8px_28px_rgba(14,165,233,0.08)] backdrop-blur-xl">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-black tracking-tight text-slate-900">
                O*NET Mini-IP (Chuẩn Bộ Lao động Hoa Kỳ)
              </h1>
              <span className="rounded-full bg-sky-100 px-2 py-0.5 text-[10px] font-black text-sky-700">
                30 mục · ~1 phút
              </span>
            </div>
            <p className="text-[11px] font-semibold text-slate-500">
              Rounds et al. (2016) · Ít chữ, trực quan, chuẩn hóa 435 ngành TT74
            </p>
          </div>

          {/* 3-Step Compact Navigation */}
          <div className="flex items-center gap-1.5">
            {[
              {
                id: 1,
                label: `1. Sở thích (${totalRiasecAnswered}/30)`,
                done: allRiasecGroupsCovered,
              },
              {
                id: 2,
                label: `2. Tư duy (${totalCognitiveAnswered}/8)`,
                done: totalCognitiveAnswered >= cognitiveQuestions.length,
              },
              { id: 3, label: "3. Điểm số", done: assessment.completed },
            ].map((s) => {
              const active = step === s.id
              return (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => {
                    if (s.id === 1 || allRiasecGroupsCovered) {
                      setStep(s.id)
                      update({ step: s.id })
                    }
                  }}
                  className={`flex items-center gap-1 rounded-xl px-2.5 py-1.5 text-xs font-extrabold transition ${
                    active
                      ? "bg-sky-600 text-white shadow-sm"
                      : s.done
                        ? "border border-sky-200 bg-sky-50 text-sky-700"
                        : "bg-slate-100/80 text-slate-500"
                  }`}
                >
                  {s.done && !active && (
                    <Check className="size-3 text-sky-600" />
                  )}
                  <span>{s.label}</span>
                </button>
              )
            })}
            {(totalRiasecAnswered > 0 || totalCognitiveAnswered > 0) && (
              <button
                type="button"
                onClick={resetAllAnswers}
                title="Làm lại từ đầu"
                className="ml-0.5 grid size-8 place-items-center rounded-xl border border-slate-200 bg-white text-slate-500 transition hover:border-sky-300 hover:text-sky-700"
              >
                <RotateCcw className="size-3.5" />
              </button>
            )}
          </div>
        </div>

        {loading && step < 3 && (
          <div className="mb-3 flex items-center justify-center gap-2 rounded-xl border border-sky-100 bg-white/70 p-2 text-slate-500">
            <Loader2 className="size-3.5 animate-spin text-sky-600" />
            <span className="text-[11px] font-semibold">
              Đang đồng bộ câu hỏi...
            </span>
          </div>
        )}

        {/* ==================== STEP 1: O*NET MINI-IP (SWIPE OR 1-SCREEN RADAR) ==================== */}
        {step === 1 && (
          <div className="space-y-4">
            {/* Mode Switcher + Thin Progress */}
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-white/85 bg-white/75 px-4 py-2.5 shadow-[0_6px_20px_rgba(14,165,233,0.06)] backdrop-blur-xl">
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => setStep1Mode("swipe")}
                  className={`inline-flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-extrabold transition ${
                    step1Mode === "swipe"
                      ? "bg-sky-600 text-white shadow-sm"
                      : "bg-sky-50 text-sky-700 hover:bg-sky-100"
                  }`}
                >
                  <Layers className="size-3.5" />
                  <span>Quẹt thẻ O*NET (30 thẻ)</span>
                </button>
                <button
                  type="button"
                  onClick={() => setStep1Mode("radar")}
                  className={`inline-flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-extrabold transition ${
                    step1Mode === "radar"
                      ? "bg-sky-600 text-white shadow-sm"
                      : "bg-sky-50 text-sky-700 hover:bg-sky-100"
                  }`}
                >
                  <Sliders className="size-3.5" />
                  <span>Chỉnh nhanh 1 màn hình (15s)</span>
                </button>
              </div>

              <div className="flex items-center gap-2">
                <div className="h-2 w-28 overflow-hidden rounded-full bg-sky-100">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-sky-500 to-cyan-500 transition-all duration-300"
                    style={{
                      width: `${Math.round((totalRiasecAnswered / 30) * 100)}%`,
                    }}
                  />
                </div>
                <span className="text-xs font-black text-sky-800">
                  {totalRiasecAnswered}/30
                </span>
              </div>
            </div>

            {/* MODE A: TINDER SWIPE DECK FOR O*NET MINI-IP */}
            {step1Mode === "swipe" && (
              <div className="space-y-4">
                <div className="relative mx-auto max-w-md pt-2">
                  {/* Stacked background card depth effect */}
                  <div className="pointer-events-none absolute inset-x-4 top-5 h-full rounded-[28px] border border-sky-200/50 bg-white/45 backdrop-blur-md" />

                  <AnimatePresence mode="wait">
                    <SwipeableOnetCard
                      key={currentCard.code}
                      item={currentCard}
                      index={cardIndex}
                      total={ONET_MINI_IP_ITEMS.length}
                      swipeDir={swipeDir}
                      currentValue={
                        typeof currentCardValue === "number"
                          ? currentCardValue
                          : undefined
                      }
                      onSwipeRight={() => rateCurrentCard(4, 1)}
                      onSwipeLeft={() => rateCurrentCard(2, -1)}
                      onPrev={() => setCardIndex((p) => Math.max(0, p - 1))}
                      onNext={() =>
                        setCardIndex((p) =>
                          Math.min(ONET_MINI_IP_ITEMS.length - 1, p + 1)
                        )
                      }
                    />
                  </AnimatePresence>
                </div>

                {/* Official 5-Level O*NET Reaction Buttons */}
                <div className="mx-auto max-w-xl">
                  <div className="grid grid-cols-5 gap-2">
                    {ONET_REACTION_SCALE.map((btn) => {
                      const active = currentCardValue === btn.value
                      return (
                        <button
                          key={btn.value}
                          type="button"
                          onClick={() =>
                            rateCurrentCard(
                              btn.value,
                              btn.value >= 4 ? 1 : btn.value <= 2 ? -1 : 1
                            )
                          }
                          className={`flex flex-col items-center justify-center rounded-2xl border py-3 px-1.5 text-center transition-all duration-150 ${
                            active
                              ? "border-sky-500 bg-gradient-to-b from-sky-500 to-cyan-600 text-white shadow-[0_10px_22px_rgba(14,165,233,0.3)] -translate-y-0.5"
                              : "border-white/85 bg-white/80 text-slate-800 shadow-sm backdrop-blur-xl hover:-translate-y-0.5 hover:border-sky-300 hover:bg-sky-50/70"
                          }`}
                        >
                          <span className="text-2xl leading-none">
                            {btn.emoji}
                          </span>
                          <span className="mt-1.5 text-[11px] font-black leading-tight">
                            {btn.label}
                          </span>
                          <span
                            className={`mt-1 text-[9px] font-bold ${
                              active ? "text-sky-100" : "text-slate-400"
                            }`}
                          >
                            Phím {btn.key}
                          </span>
                        </button>
                      )
                    })}
                  </div>
                  <p className="mt-2.5 text-center text-[11px] font-semibold text-slate-500">
                    Kéo thẻ sang phải = Thích 👍 · Sang trái = Không hợp ✕ · Hoặc
                    bấm phím <kbd className="rounded bg-white px-1.5 py-0.5 shadow-sm">1</kbd>–
                    <kbd className="rounded bg-white px-1.5 py-0.5 shadow-sm">5</kbd>
                  </p>
                </div>
              </div>
            )}

            {/* MODE B: 1-SCREEN INSTANT RADAR & SLIDERS (15 SECONDS) */}
            {step1Mode === "radar" && (
              <div className="grid gap-4 rounded-[26px] border border-white/85 bg-white/80 p-5 shadow-[0_14px_36px_rgba(14,165,233,0.08)] backdrop-blur-2xl md:grid-cols-[1.2fr_0.8fr]">
                <div className="space-y-3">
                  {RIASEC_ORDER.map((dim) => {
                    const meta = RIASEC_META[dim]
                    const avg = riasecGroupAvg[dim]
                    const isFilled = riasecGroupCounts[dim] >= 5
                    return (
                      <div
                        key={dim}
                        className="rounded-2xl border border-sky-100/80 bg-white/85 p-3 shadow-sm"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div>
                            <span className="text-xs font-black text-slate-900">
                              {meta.label}
                            </span>
                            <p className="text-[11px] font-medium text-slate-500">
                              {meta.sampleHint}
                            </p>
                          </div>
                          <div className="flex items-center gap-1">
                            {[1, 2, 3, 4, 5].map((lv) => {
                              const active = isFilled && Math.round(avg) === lv
                              return (
                                <button
                                  key={lv}
                                  type="button"
                                  onClick={() => setGroupLevel(dim, lv)}
                                  className={`size-7 rounded-lg text-xs font-black transition ${
                                    active
                                      ? "bg-sky-600 text-white shadow-sm"
                                      : "bg-sky-50 text-sky-700 hover:bg-sky-100"
                                  }`}
                                >
                                  {lv}
                                </button>
                              )
                            })}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>

                {/* Live Hexagon Radar Preview */}
                <div className="flex flex-col items-center justify-center rounded-2xl border border-sky-100 bg-sky-50/50 p-4 text-center">
                  <span className="mb-1 inline-flex items-center gap-1 rounded-full bg-white px-3 py-1 text-[10px] font-black uppercase tracking-wider text-sky-700 shadow-sm">
                    <Sparkles className="size-3" />
                    Biểu đồ RIASEC trực tiếp
                  </span>
                  <LiveRiasecHexagon scores={riasecGroupPct} />
                  <p className="mt-1 text-[11px] font-semibold text-slate-500">
                    Chạm các mức 1–5 bên trái để tự động điền chuẩn 30 câu O*NET
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ==================== STEP 2: ULTRA-COMPACT COGNITIVE REFLEX ==================== */}
        {step === 2 && currentCog && (
          <motion.div
            key={currentCog.code}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.18 }}
            className="rounded-[26px] border border-white/85 bg-white/80 p-5 sm:p-6 shadow-[0_14px_38px_rgba(14,165,233,0.1)] backdrop-blur-2xl"
          >
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-sky-100 px-3 py-1 text-xs font-black text-sky-800">
                <Zap className="size-3.5 text-sky-600" />
                Tình huống {cogIndex + 1}/{cognitiveQuestions.length} ·{" "}
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

            <h2 className="mb-4 text-base sm:text-lg font-black text-slate-900">
              {currentCog.subtitle}
            </h2>

            <div className="grid gap-2.5 sm:grid-cols-2">
              {currentCog.options.map((opt) => {
                const isSelected = String(currentCogValue) === opt.option_key
                return (
                  <button
                    key={opt.option_key}
                    type="button"
                    onClick={() => handleSelectCognitive(opt.option_key)}
                    className={`flex items-start gap-3 rounded-2xl border p-3.5 text-left transition-all ${
                      isSelected
                        ? "border-sky-500 bg-gradient-to-br from-sky-500 to-cyan-600 text-white shadow-[0_10px_22px_rgba(14,165,233,0.25)]"
                        : "border-sky-100 bg-white/90 text-slate-800 hover:border-sky-400 hover:bg-sky-50/70"
                    }`}
                  >
                    <span
                      className={`mt-0.5 inline-flex size-7 shrink-0 items-center justify-center rounded-lg text-xs font-black ${
                        isSelected
                          ? "bg-white text-sky-700"
                          : "bg-sky-100 text-sky-800"
                      }`}
                    >
                      {opt.option_key}
                    </span>
                    <div className="min-w-0">
                      <h3 className="text-sm font-black leading-snug">
                        {opt.title}
                      </h3>
                      <p
                        className={`mt-1 text-xs line-clamp-1 ${
                          isSelected ? "text-sky-100" : "text-slate-500"
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

        {/* ==================== STEP 3: ACADEMIC SCORES ==================== */}
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

        {/* Bottom Navigation Bar */}
        <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
          <Button
            variant="ghost"
            icon={ArrowLeft}
            disabled={step === 1 && (step1Mode === "radar" || cardIndex === 0)}
            onClick={() => {
              if (step === 1 && step1Mode === "swipe" && cardIndex > 0) {
                setCardIndex((p) => Math.max(0, p - 1))
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
            {step === 1 && !allRiasecGroupsCovered && (
              <span className="text-xs font-bold text-slate-500">
                Cần tối thiểu 18/30 thẻ ({totalRiasecAnswered}/18)
              </span>
            )}

            {step === 1 && (
              <Button
                icon={ArrowRight}
                disabled={!allRiasecGroupsCovered}
                onClick={() => {
                  // Auto-fill neutral (3) only if user stops early between 18..29 cards
                  const filled: Record<string, number> = {
                    ...assessment.answers,
                  }
                  CANONICAL_30_CODES.forEach((code, idx) => {
                    if (
                      filled[code] === undefined &&
                      filled[`1-${idx}`] === undefined
                    ) {
                      filled[code] = 3
                      filled[`1-${idx}`] = 3
                    }
                  })
                  update({ answers: filled, step: 2 })
                  setStep(2)
                  window.scrollTo({ top: 0, behavior: "smooth" })
                }}
              >
                Qua Bước 2 ({totalRiasecAnswered}/30)
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
                Qua Bước 3 ({totalCognitiveAnswered}/{cognitiveQuestions.length})
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

function SwipeableOnetCard({
  item,
  index,
  total,
  swipeDir,
  currentValue,
  onSwipeRight,
  onSwipeLeft,
  onPrev,
  onNext,
}: {
  item: OnetMiniIpItem
  index: number
  total: number
  swipeDir: number
  currentValue?: number
  onSwipeRight: () => void
  onSwipeLeft: () => void
  onPrev: () => void
  onNext: () => void
}) {
  const x = useMotionValue(0)
  const rotate = useTransform(x, [-180, 180], [-10, 10])
  const likeOpacity = useTransform(x, [25, 100], [0, 1])
  const nopeOpacity = useTransform(x, [-100, -25], [1, 0])

  const meta = RIASEC_META[item.dimension]

  return (
    <motion.div
      style={{ x, rotate }}
      drag="x"
      dragConstraints={{ left: 0, right: 0 }}
      dragElastic={0.45}
      onDragEnd={(_, info) => {
        if (info.offset.x > 85) {
          onSwipeRight()
        } else if (info.offset.x < -85) {
          onSwipeLeft()
        }
      }}
      initial={{ opacity: 0, x: swipeDir >= 0 ? 40 : -40, scale: 0.96 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: swipeDir >= 0 ? -120 : 120, scale: 0.92 }}
      transition={{ duration: 0.16 }}
      className="relative cursor-grab active:cursor-grabbing select-none rounded-[28px] border border-white/90 bg-white/85 p-6 sm:p-7 shadow-[0_20px_48px_rgba(14,165,233,0.14)] backdrop-blur-2xl"
    >
      {/* Live Drag Overlay Badges */}
      <motion.div
        style={{ opacity: likeOpacity }}
        className="pointer-events-none absolute right-5 top-5 rounded-xl border-2 border-sky-500 bg-sky-50/90 px-3 py-1 text-xs font-black text-sky-700 rotate-6"
      >
        THÍCH 👍
      </motion.div>
      <motion.div
        style={{ opacity: nopeOpacity }}
        className="pointer-events-none absolute left-5 top-5 rounded-xl border-2 border-slate-400 bg-slate-100/90 px-3 py-1 text-xs font-black text-slate-600 -rotate-6"
      >
        BỎ QUA ✕
      </motion.div>

      {/* Header Pill + Prev/Next */}
      <div className="mb-6 flex items-center justify-between gap-2">
        <span className="rounded-full bg-sky-50 px-3 py-1 text-[11px] font-black text-sky-700 border border-sky-200/80">
          {index + 1}/{total} · {meta.label}
        </span>

        <div className="flex items-center gap-1">
          <button
            type="button"
            disabled={index === 0}
            onClick={(e) => {
              e.stopPropagation()
              onPrev()
            }}
            className="rounded-lg border border-slate-200 bg-white px-2 py-0.5 text-[11px] font-bold text-slate-600 hover:border-sky-300 disabled:opacity-35"
          >
            ←
          </button>
          <button
            type="button"
            disabled={index >= total - 1}
            onClick={(e) => {
              e.stopPropagation()
              onNext()
            }}
            className="rounded-lg border border-slate-200 bg-white px-2 py-0.5 text-[11px] font-bold text-slate-600 hover:border-sky-300 disabled:opacity-35"
          >
            →
          </button>
        </div>
      </div>

      {/* Central Visual Icon */}
      <OnetItemVisualIcon iconKey={item.iconKey} />

      {/* Minimal Concise Title + Authentic O*NET English Phrase */}
      <div className="mt-6 text-center">
        <h2 className="text-xl sm:text-2xl font-black tracking-tight text-slate-900 leading-snug">
          “{item.titleVi}”
        </h2>
        <p className="mt-1.5 text-xs font-semibold text-slate-400">
          O*NET Mini-IP ({item.code}): {item.titleEn}
        </p>
      </div>

      {/* Current Answer Status Pill (if revisiting) */}
      <div className="mt-5 flex justify-center">
        {currentValue !== undefined ? (
          <span className="rounded-full bg-sky-100 px-3 py-1 text-[11px] font-black text-sky-800">
            Đã chọn:{" "}
            {ONET_REACTION_SCALE.find((r) => r.value === currentValue)?.emoji}{" "}
            {ONET_REACTION_SCALE.find((r) => r.value === currentValue)?.label} (
            {currentValue}/5)
          </span>
        ) : (
          <span className="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-bold text-slate-500">
            Vòng {item.round}/5 · Chạm mức cảm xúc bên dưới hoặc quẹt thẻ
          </span>
        )}
      </div>
    </motion.div>
  )
}
