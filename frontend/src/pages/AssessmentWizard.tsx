import confetti from "canvas-confetti"
import { AnimatePresence, motion, useMotionValue, useTransform } from "framer-motion"
import {
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronLeft,
  ChevronRight,
  Layers,
  Loader2,
  RotateCcw,
  Sliders,
} from "lucide-react"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useNavigate } from "react-router"
import { AcademicInputForm } from "../components/assessment/AcademicInputForm"
import {
  LiveRiasecHexagon,
  OnetItemVisualIcon,
} from "../components/assessment/OnetSwipeCardVisual"
import { Button } from "../components/common/Button"
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

  // Step 1 Mode: 'swipe' (Liquid Glass Card Carousel) | 'radar' (1-Screen Fast Radar)
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
  const [slideDirection, setSlideDirection] = useState<number>(1)

  // Step 2: Cognitive Quest
  const [cogIndex, setCogIndex] = useState(0)
  const [cogDirection, setCogDirection] = useState(1)
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

  // Navigate questions (Next / Prev) cleanly on swipe or chevron click
  const goToNextCard = useCallback(() => {
    setSlideDirection(1)
    setCardIndex((p) => Math.min(ONET_MINI_IP_ITEMS.length - 1, p + 1))
  }, [])

  const goToPrevCard = useCallback(() => {
    setSlideDirection(-1)
    setCardIndex((p) => Math.max(0, p - 1))
  }, [])

  // Rate current O*NET card (1..5) and advance smoothly to next question
  const rateCurrentCard = useCallback(
    (value: number) => {
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
          setSlideDirection(1)
          setCardIndex((prev) => prev + 1)
        }
      }, 180)
    },
    [currentCard.code, assessment.answers, update, cardIndex]
  )

  // Apply 1-screen Radar score (1..5) to all 5 items of a RIASEC dimension
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

  const goToNextCog = useCallback(() => {
    setCogDirection(1)
    setCogIndex((p) => Math.min(cognitiveQuestions.length - 1, p + 1))
  }, [cognitiveQuestions.length])

  const goToPrevCog = useCallback(() => {
    setCogDirection(-1)
    setCogIndex((p) => Math.max(0, p - 1))
  }, [])

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
          setCogDirection(1)
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

  // Keyboard navigation: Left/Right arrows ONLY navigate prev/next question; 1-5 rate
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
          rateCurrentCard(Number(e.key))
        } else if (e.key === "ArrowRight") {
          e.preventDefault()
          goToNextCard()
        } else if (e.key === "ArrowLeft") {
          e.preventDefault()
          goToPrevCard()
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
          e.preventDefault()
          goToNextCog()
        } else if (e.key === "ArrowLeft") {
          e.preventDefault()
          goToPrevCog()
        }
      }
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [
    step,
    step1Mode,
    rateCurrentCard,
    goToNextCard,
    goToPrevCard,
    handleSelectCognitive,
    goToNextCog,
    goToPrevCog,
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
    <section className="relative py-6 sm:py-8 overflow-x-clip">
      {/* Ambient Animated Liquid Glass Background Orbs */}
      <motion.div
        animate={{
          x: [0, 24, -12, 0],
          y: [0, -18, 12, 0],
          scale: [1, 1.06, 0.96, 1],
        }}
        transition={{ duration: 14, repeat: Infinity, ease: "easeInOut" }}
        className="pointer-events-none absolute left-1/4 top-12 h-72 w-72 rounded-full bg-sky-300/25 blur-3xl"
      />
      <motion.div
        animate={{
          x: [0, -28, 16, 0],
          y: [0, 20, -14, 0],
          scale: [1, 0.95, 1.08, 1],
        }}
        transition={{ duration: 16, repeat: Infinity, ease: "easeInOut" }}
        className="pointer-events-none absolute right-1/4 top-36 h-80 w-80 rounded-full bg-cyan-300/20 blur-3xl"
      />

      <PageContainer className="relative z-10 max-w-3xl">
        {/* Ultra-Clean Top Liquid Glass Navigation Bar */}
        <div className="mb-5 flex flex-wrap items-center justify-between gap-2.5 rounded-3xl border border-white/85 bg-white/55 px-4 py-2.5 shadow-[inset_0_1px_1px_rgba(255,255,255,0.9),0_12px_32px_rgba(14,165,233,0.08)] backdrop-blur-2xl">
          {/* 3 Main Steps */}
          <div className="flex items-center gap-1.5">
            {[
              { id: 1, label: "1. Sở thích", done: allRiasecGroupsCovered },
              {
                id: 2,
                label: "2. Tư duy",
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
                  className={`relative flex items-center gap-2 rounded-2xl px-4 py-2.5 text-sm sm:text-base font-extrabold transition ${
                    active
                      ? "bg-gradient-to-r from-sky-500 to-cyan-500 text-white shadow-[0_6px_18px_rgba(14,165,233,0.28)]"
                      : s.done
                        ? "border border-sky-200/80 bg-white/75 text-sky-700 hover:bg-white"
                        : "bg-white/40 text-slate-600 hover:bg-white/70"
                  }`}
                >
                  {s.done && !active && (
                    <Check className="size-4 text-sky-600" />
                  )}
                  <span>{s.label}</span>
                </button>
              )
            })}
          </div>

          {/* Right Utilities: View Mode Switch + Reset */}
          <div className="flex items-center gap-2">
            {step === 1 && (
              <div className="flex items-center rounded-2xl border border-white/80 bg-white/55 p-1 backdrop-blur-xl">
                <button
                  type="button"
                  onClick={() => setStep1Mode("swipe")}
                  className={`inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-sm font-extrabold transition ${
                    step1Mode === "swipe"
                      ? "bg-sky-600 text-white shadow-sm"
                      : "text-slate-600 hover:text-sky-700"
                  }`}
                >
                  <Layers className="size-4" />
                  <span>Thẻ</span>
                </button>
                <button
                  type="button"
                  onClick={() => setStep1Mode("radar")}
                  className={`inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-sm font-extrabold transition ${
                    step1Mode === "radar"
                      ? "bg-sky-600 text-white shadow-sm"
                      : "text-slate-600 hover:text-sky-700"
                  }`}
                >
                  <Sliders className="size-4" />
                  <span>Radar</span>
                </button>
              </div>
            )}

            {(totalRiasecAnswered > 0 || totalCognitiveAnswered > 0) && (
              <button
                type="button"
                onClick={resetAllAnswers}
                title="Làm lại"
                className="grid size-9 place-items-center rounded-2xl border border-white/85 bg-white/60 text-slate-600 backdrop-blur-xl transition hover:border-sky-300 hover:bg-white hover:text-sky-700"
              >
                <RotateCcw className="size-4" />
              </button>
            )}
          </div>
        </div>

        {loading && step < 3 && (
          <div className="mb-4 flex items-center justify-center gap-2 text-sky-700/70">
            <Loader2 className="size-4 animate-spin" />
          </div>
        )}

        {/* ==================== STEP 1: LIQUID GLASS QUESTION CARDS & 5 EMOJI CHOICES ==================== */}
        {step === 1 && (
          <div className="space-y-6">
            {step1Mode === "swipe" && (
              <>
                {/* Liquid Glass Progress Track */}
                <div className="mx-auto flex max-w-xl items-center gap-3 px-2">
                  <div className="h-2.5 flex-1 overflow-hidden rounded-full border border-white/80 bg-white/50 p-0.5 backdrop-blur-md">
                    <motion.div
                      animate={{
                        width: `${Math.round(
                          (totalRiasecAnswered / 30) * 100
                        )}%`,
                      }}
                      transition={{ type: "spring", stiffness: 260, damping: 24 }}
                      className="h-full rounded-full bg-gradient-to-r from-sky-400 via-sky-500 to-cyan-500"
                    />
                  </div>
                  <span className="text-base font-black text-sky-900">
                    {totalRiasecAnswered}/30
                  </span>
                </div>

                {/* Carousel Stage: Drag / Swipe Left or Right -> Next / Previous Question */}
                <div className="relative mx-auto flex max-w-2xl items-center justify-center gap-3">
                  {/* Left Arrow Button (Previous Question) */}
                  <motion.button
                    type="button"
                    whileHover={{ scale: 1.08 }}
                    whileTap={{ scale: 0.92 }}
                    disabled={cardIndex === 0}
                    onClick={goToPrevCard}
                    aria-label="Câu trước"
                    className="hidden sm:grid size-12 shrink-0 place-items-center rounded-full border border-white/90 bg-white/60 text-sky-700 shadow-[inset_0_1px_1px_rgba(255,255,255,0.9),0_8px_24px_rgba(14,165,233,0.12)] backdrop-blur-2xl transition hover:bg-white/90 disabled:opacity-30"
                  >
                    <ChevronLeft className="size-6" />
                  </motion.button>

                  {/* Center Liquid Glass Card */}
                  <div className="relative w-full max-w-lg">
                    {/* Layered Frost Depth */}
                    <div className="pointer-events-none absolute inset-x-6 -bottom-3 top-5 rounded-[34px] border border-white/60 bg-white/30 backdrop-blur-xl" />

                    <AnimatePresence mode="wait" custom={slideDirection}>
                      <LiquidGlassQuestionCard
                        key={currentCard.code}
                        item={currentCard}
                        index={cardIndex}
                        total={ONET_MINI_IP_ITEMS.length}
                        direction={slideDirection}
                        onNext={goToNextCard}
                        onPrev={goToPrevCard}
                      />
                    </AnimatePresence>
                  </div>

                  {/* Right Arrow Button (Next Question) */}
                  <motion.button
                    type="button"
                    whileHover={{ scale: 1.08 }}
                    whileTap={{ scale: 0.92 }}
                    disabled={cardIndex >= ONET_MINI_IP_ITEMS.length - 1}
                    onClick={goToNextCard}
                    aria-label="Câu tiếp theo"
                    className="hidden sm:grid size-12 shrink-0 place-items-center rounded-full border border-white/90 bg-white/60 text-sky-700 shadow-[inset_0_1px_1px_rgba(255,255,255,0.9),0_8px_24px_rgba(14,165,233,0.12)] backdrop-blur-2xl transition hover:bg-white/90 disabled:opacity-30"
                  >
                    <ChevronRight className="size-6" />
                  </motion.button>
                </div>

                {/* 5 Clean Big Choices ONLY (No small text underneath) */}
                <div className="mx-auto max-w-2xl">
                  <div className="grid grid-cols-5 gap-2.5 sm:gap-3">
                    {ONET_REACTION_SCALE.map((btn) => {
                      const active = currentCardValue === btn.value
                      return (
                        <motion.button
                          key={btn.value}
                          type="button"
                          whileHover={{ y: -4, scale: 1.03 }}
                          whileTap={{ scale: 0.94 }}
                          transition={{
                            type: "spring",
                            stiffness: 400,
                            damping: 22,
                          }}
                          onClick={() => rateCurrentCard(btn.value)}
                          className={`relative flex flex-col items-center justify-center rounded-[26px] border py-5 px-2.5 text-center backdrop-blur-2xl transition-colors duration-200 ${
                            active
                              ? "border-sky-400 bg-gradient-to-b from-sky-500 to-cyan-500 text-white shadow-[inset_0_1px_2px_rgba(255,255,255,0.6),0_14px_30px_rgba(14,165,233,0.32)]"
                              : "border-white/90 bg-white/60 text-slate-800 shadow-[inset_0_1px_1px_rgba(255,255,255,0.9),0_8px_24px_rgba(14,165,233,0.08)] hover:border-sky-300 hover:bg-white/85"
                          }`}
                        >
                          <span className="text-4xl sm:text-5xl leading-none">
                            {btn.emoji}
                          </span>
                          <span className="mt-3 text-sm sm:text-base font-extrabold tracking-tight leading-tight">
                            {btn.label}
                          </span>
                        </motion.button>
                      )
                    })}
                  </div>
                </div>
              </>
            )}

            {/* MODE B: 1-SCREEN RADAR SLIDERS */}
            {step1Mode === "radar" && (
              <div className="grid gap-5 rounded-[30px] border border-white/90 bg-white/60 p-6 shadow-[inset_0_1px_1px_rgba(255,255,255,0.95),0_20px_50px_rgba(14,165,233,0.12)] backdrop-blur-2xl md:grid-cols-[1.2fr_0.8fr]">
                <div className="space-y-3">
                  {RIASEC_ORDER.map((dim) => {
                    const meta = RIASEC_META[dim]
                    const avg = riasecGroupAvg[dim]
                    const isFilled = riasecGroupCounts[dim] >= 5
                    return (
                      <div
                        key={dim}
                        className="flex items-center justify-between gap-3 rounded-2xl border border-white/80 bg-white/70 px-4 py-3 backdrop-blur-xl"
                      >
                        <span className="text-base sm:text-lg font-extrabold text-slate-900">
                          {meta.label}
                        </span>
                        <div className="flex items-center gap-1.5">
                          {[1, 2, 3, 4, 5].map((lv) => {
                            const active = isFilled && Math.round(avg) === lv
                            return (
                              <motion.button
                                key={lv}
                                type="button"
                                whileTap={{ scale: 0.9 }}
                                onClick={() => setGroupLevel(dim, lv)}
                                className={`size-10 rounded-xl text-base font-black transition ${
                                  active
                                    ? "bg-gradient-to-br from-sky-500 to-cyan-500 text-white shadow-md"
                                    : "bg-sky-50/80 text-sky-800 hover:bg-sky-100"
                                }`}
                              >
                                {lv}
                              </motion.button>
                            )
                          })}
                        </div>
                      </div>
                    )
                  })}
                </div>

                <div className="flex flex-col items-center justify-center rounded-3xl border border-white/80 bg-sky-50/45 p-5 backdrop-blur-xl">
                  <LiveRiasecHexagon scores={riasecGroupPct} />
                </div>
              </div>
            )}
          </div>
        )}

        {/* ==================== STEP 2: BIG CLEAN LIQUID GLASS COGNITIVE ==================== */}
        {step === 2 && currentCog && (
          <div className="relative mx-auto flex max-w-3xl items-center justify-center gap-3">
            <motion.button
              type="button"
              whileHover={{ scale: 1.08 }}
              whileTap={{ scale: 0.92 }}
              disabled={cogIndex === 0}
              onClick={goToPrevCog}
              aria-label="Câu trước"
              className="hidden sm:grid size-11 shrink-0 place-items-center rounded-full border border-white/90 bg-white/60 text-sky-700 shadow-lg backdrop-blur-2xl disabled:opacity-30"
            >
              <ChevronLeft className="size-6" />
            </motion.button>

            <AnimatePresence mode="wait" custom={cogDirection}>
              <motion.div
                key={currentCog.code}
                custom={cogDirection}
                initial={{ opacity: 0, x: cogDirection * 48, scale: 0.97 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: cogDirection * -48, scale: 0.97 }}
                transition={{ type: "spring", stiffness: 320, damping: 28 }}
                drag="x"
                dragConstraints={{ left: 0, right: 0 }}
                dragElastic={0.35}
                onDragEnd={(_, info) => {
                  if (info.offset.x < -55 || info.velocity.x < -300) {
                    goToNextCog()
                  } else if (info.offset.x > 55 || info.velocity.x > 300) {
                    goToPrevCog()
                  }
                }}
                className="w-full rounded-[32px] border border-white/90 bg-white/60 p-6 sm:p-8 shadow-[inset_0_1px_1px_rgba(255,255,255,0.95),0_20px_50px_rgba(14,165,233,0.14)] backdrop-blur-2xl"
              >
                <div className="mb-5 flex items-center justify-between">
                  <span className="rounded-full border border-white/80 bg-white/80 px-4 py-1.5 text-sm font-black text-sky-700">
                    {cogIndex + 1} / {cognitiveQuestions.length}
                  </span>
                </div>

                <h2 className="mb-7 text-2xl sm:text-3xl font-black leading-snug text-slate-900">
                  {currentCog.subtitle}
                </h2>

                <div className="grid gap-3.5 sm:grid-cols-2">
                  {currentCog.options.map((opt) => {
                    const isSelected = String(currentCogValue) === opt.option_key
                    return (
                      <motion.button
                        key={opt.option_key}
                        type="button"
                        whileHover={{ y: -3, scale: 1.02 }}
                        whileTap={{ scale: 0.96 }}
                        onClick={() => handleSelectCognitive(opt.option_key)}
                        className={`flex items-center gap-4 rounded-2xl border p-5 text-left backdrop-blur-xl transition-colors ${
                          isSelected
                            ? "border-sky-400 bg-gradient-to-br from-sky-500 to-cyan-500 text-white shadow-[0_12px_28px_rgba(14,165,233,0.28)]"
                            : "border-white/90 bg-white/75 text-slate-900 hover:border-sky-300 hover:bg-white"
                        }`}
                      >
                        <span
                          className={`grid size-11 shrink-0 place-items-center rounded-xl text-base font-black ${
                            isSelected
                              ? "bg-white text-sky-700"
                              : "bg-sky-100 text-sky-800"
                          }`}
                        >
                          {opt.option_key}
                        </span>
                        <span className="text-base sm:text-lg font-extrabold leading-snug">
                          {opt.title}
                        </span>
                      </motion.button>
                    )
                  })}
                </div>
              </motion.div>
            </AnimatePresence>

            <motion.button
              type="button"
              whileHover={{ scale: 1.08 }}
              whileTap={{ scale: 0.92 }}
              disabled={cogIndex >= cognitiveQuestions.length - 1}
              onClick={goToNextCog}
              aria-label="Câu tiếp theo"
              className="hidden sm:grid size-11 shrink-0 place-items-center rounded-full border border-white/90 bg-white/60 text-sky-700 shadow-lg backdrop-blur-2xl disabled:opacity-30"
            >
              <ChevronRight className="size-6" />
            </motion.button>
          </div>
        )}

        {/* ==================== STEP 3: ACADEMIC SCORES ==================== */}
        {step === 3 && (
          <div className="rounded-[32px] border border-white/90 bg-white/60 p-6 sm:p-8 shadow-[inset_0_1px_1px_rgba(255,255,255,0.95),0_20px_50px_rgba(14,165,233,0.14)] backdrop-blur-2xl">
            <AcademicInputForm
              scores={scores}
              onChange={(subject, value) =>
                setScores((prev) => ({ ...prev, [subject]: value }))
              }
            />
          </div>
        )}

        {/* Clean Bottom Footer Bar */}
        <div className="mt-8 flex items-center justify-between gap-3">
          <Button
            variant="ghost"
            icon={ArrowLeft}
            className="text-base px-5 py-3"
            disabled={step === 1 && (step1Mode === "radar" || cardIndex === 0)}
            onClick={() => {
              if (step === 1 && step1Mode === "swipe" && cardIndex > 0) {
                goToPrevCard()
                return
              }
              if (step === 2 && cogIndex > 0) {
                goToPrevCog()
                return
              }
              const prevStep = Math.max(1, step - 1)
              setStep(prevStep)
              update({ step: prevStep })
            }}
          >
            Quay lại
          </Button>

          <div>
            {step === 1 && (
              <Button
                icon={ArrowRight}
                className="text-base px-6 py-3"
                disabled={!allRiasecGroupsCovered}
                onClick={() => {
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
                Tiếp tục
              </Button>
            )}

            {step === 2 && (
              <Button
                icon={ArrowRight}
                className="text-base px-6 py-3"
                disabled={totalCognitiveAnswered < cognitiveQuestions.length}
                onClick={() => {
                  setStep(3)
                  update({ step: 3 })
                  window.scrollTo({ top: 0, behavior: "smooth" })
                }}
              >
                Tiếp tục
              </Button>
            )}

            {step === 3 && (
              <Button
                icon={Check}
                className="text-base px-6 py-3"
                disabled={Object.values(scores).filter((v) => v > 0).length < 3}
                onClick={handleCompleteAssessment}
              >
                Xem kết quả
              </Button>
            )}
          </div>
        </div>
      </PageContainer>
    </section>
  )
}

function LiquidGlassQuestionCard({
  item,
  index,
  total,
  direction,
  onNext,
  onPrev,
}: {
  item: OnetMiniIpItem
  index: number
  total: number
  direction: number
  onNext: () => void
  onPrev: () => void
}) {
  const x = useMotionValue(0)
  const rotate = useTransform(x, [-220, 220], [-6, 6])
  const scaleDrag = useTransform(x, [-220, 0, 220], [0.97, 1, 0.97])

  return (
    <motion.div
      custom={direction}
      style={{ x, rotate, scale: scaleDrag }}
      drag="x"
      dragConstraints={{ left: 0, right: 0 }}
      dragElastic={0.42}
      onDragEnd={(_, info) => {
        // Swipe left -> Next question; Swipe right -> Previous question
        if (info.offset.x < -55 || info.velocity.x < -300) {
          onNext()
        } else if (info.offset.x > 55 || info.velocity.x > 300) {
          onPrev()
        }
      }}
      initial={{
        opacity: 0,
        x: direction >= 0 ? 72 : -72,
        scale: 0.95,
        filter: "blur(4px)",
      }}
      animate={{
        opacity: 1,
        x: 0,
        scale: 1,
        filter: "blur(0px)",
      }}
      exit={{
        opacity: 0,
        x: direction >= 0 ? -72 : 72,
        scale: 0.95,
        filter: "blur(4px)",
      }}
      transition={{
        type: "spring",
        stiffness: 320,
        damping: 28,
        mass: 0.85,
      }}
      className="relative cursor-grab active:cursor-grabbing select-none overflow-hidden rounded-[34px] border border-white/90 bg-white/55 px-6 py-10 sm:px-10 sm:py-12 shadow-[inset_0_1px_1px_rgba(255,255,255,0.95),0_24px_54px_rgba(14,165,233,0.14)] backdrop-blur-2xl"
    >
      {/* Specular Top Reflection */}
      <div className="pointer-events-none absolute inset-x-10 top-0 h-px bg-gradient-to-r from-transparent via-white to-transparent" />

      {/* Minimal Top Index + Mobile Prev/Next Tap */}
      <div className="mb-7 flex items-center justify-between">
        <span className="rounded-full border border-white/80 bg-white/75 px-4 py-1.5 text-sm sm:text-base font-black text-sky-800 backdrop-blur-md">
          {index + 1} / {total}
        </span>

        <div className="flex items-center gap-1.5 sm:hidden">
          <button
            type="button"
            disabled={index === 0}
            onClick={(e) => {
              e.stopPropagation()
              onPrev()
            }}
            className="grid size-9 place-items-center rounded-full border border-white/80 bg-white/75 text-sky-700 disabled:opacity-30"
          >
            <ChevronLeft className="size-5" />
          </button>
          <button
            type="button"
            disabled={index >= total - 1}
            onClick={(e) => {
              e.stopPropagation()
              onNext()
            }}
            className="grid size-9 place-items-center rounded-full border border-white/80 bg-white/75 text-sky-700 disabled:opacity-30"
          >
            <ChevronRight className="size-5" />
          </button>
        </div>
      </div>

      {/* Liquid Glass Hero Icon */}
      <OnetItemVisualIcon iconKey={item.iconKey} />

      {/* BIG CLEAR QUESTION (No quotation marks, larger font) */}
      <div className="mt-8 text-center">
        <h2 className="text-2xl sm:text-4xl font-black tracking-tight text-slate-900 leading-tight">
          {item.titleVi}
        </h2>
      </div>
    </motion.div>
  )
}
