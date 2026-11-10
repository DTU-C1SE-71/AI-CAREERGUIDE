import confetti from "canvas-confetti"
import { motion } from "framer-motion"
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Compass,
  Gamepad2,
  Loader2,
  RotateCcw,
  Sparkles,
  Zap,
} from "lucide-react"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useNavigate } from "react-router"
import { AcademicInputForm } from "../components/assessment/AcademicInputForm"
import { RoleplaySceneVisual } from "../components/assessment/RoleplaySceneVisual"
import { Button } from "../components/common/Button"
import { Card } from "../components/common/Card"
import { PageContainer } from "../components/layout/PageContainer"
import {
  defaultCognitiveQuestions,
  type CognitiveQuestionItem,
} from "../data/cognitiveQuestions"
import {
  REACTION_CARDS,
  ROLEPLAY_SCENES,
  STATIONS_META,
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

const defaultRiasecFallback: QuestionItem[] = ROLEPLAY_SCENES.map(
  (scene, idx) => ({
    code: scene.code,
    dimension: scene.group,
    dimension_badge: scene.stationTitle,
    domain_tag: scene.sceneBadge,
    question_text: scene.actionTitle,
    order_index: idx + 1,
  })
)

const RIASEC_ORDER = ["R", "I", "A", "S", "E", "C"] as const

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

  // Mini-Game state for Step 1 (Roleplay Odyssey)
  const [quickMode18, setQuickMode18] = useState(false)
  const [sceneIndex, setSceneIndex] = useState(0)

  // Mini-Game state for Step 2 (Cognitive Quest 1..8)
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
        // Fallback already in state
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

  const resetAllAnswers = () => {
    reset()
    setStep(1)
    setSceneIndex(0)
    setCogIndex(0)
  }

  // Active scenes list in Step 1 (30 full or 18 core)
  const activeScenes = useMemo(() => {
    return quickMode18
      ? ROLEPLAY_SCENES.filter((s) => s.isCore18)
      : ROLEPLAY_SCENES
  }, [quickMode18])

  const safeSceneIndex = Math.min(
    Math.max(0, sceneIndex),
    Math.max(0, activeScenes.length - 1)
  )
  const currentScene = activeScenes[safeSceneIndex] || ROLEPLAY_SCENES[0]

  // Count how many RIASEC & Cognitive items are answered
  const riasecGroupCounts = useMemo(() => {
    const counts: Record<string, number> = {
      R: 0,
      I: 0,
      A: 0,
      S: 0,
      E: 0,
      C: 0,
    }
    ROLEPLAY_SCENES.forEach((scene, idx) => {
      const val =
        assessment.answers[scene.code] ?? assessment.answers[`1-${idx}`]
      if (typeof val === "number" && val >= 1 && val <= 5) {
        counts[scene.group] = (counts[scene.group] || 0) + 1
      }
    })
    return counts
  }, [assessment.answers])

  // Live RIASEC energy % for the 6-station header
  const riasecEnergy = useMemo(() => {
    const energy: Record<string, number> = {
      R: 0,
      I: 0,
      A: 0,
      S: 0,
      E: 0,
      C: 0,
    }
    ROLEPLAY_SCENES.forEach((scene, idx) => {
      const val =
        assessment.answers[scene.code] ?? assessment.answers[`1-${idx}`]
      if (typeof val === "number" && val >= 1 && val <= 5) {
        energy[scene.group] += val * 4
      }
    })
    return energy
  }, [assessment.answers])

  const totalRiasecAnswered = useMemo(
    () => Object.values(riasecGroupCounts).reduce((a, b) => a + b, 0),
    [riasecGroupCounts]
  )

  const totalCognitiveAnswered = useMemo(() => {
    return cognitiveQuestions.filter((q, idx) => {
      const v = assessment.cognitive[q.code] ?? assessment.cognitive[`2-${idx}`]
      return v !== undefined && v !== null && String(v).trim() !== ""
    }).length
  }, [assessment.cognitive, cognitiveQuestions])

  const allRiasecGroupsCovered = useMemo(() => {
    return (
      totalRiasecAnswered >= 18 &&
      RIASEC_ORDER.every((dim) => (riasecGroupCounts[dim] || 0) >= 2)
    )
  }, [totalRiasecAnswered, riasecGroupCounts])

  const totalXP = useMemo(() => {
    return (
      totalRiasecAnswered * 25 +
      totalCognitiveAnswered * 40 +
      (step === 3 ? 120 : 0)
    )
  }, [totalRiasecAnswered, totalCognitiveAnswered, step])

  const canContinue = useMemo(() => {
    if (step === 1) return allRiasecGroupsCovered
    if (step === 2) return totalCognitiveAnswered >= cognitiveQuestions.length
    if (step === 3) {
      return Object.values(scores).filter((v) => v > 0).length >= 3
    }
    return false
  }, [
    step,
    allRiasecGroupsCovered,
    totalCognitiveAnswered,
    cognitiveQuestions.length,
    scores,
  ])

  // Select a reaction in Step 1 and auto-advance smoothly
  const handleSelectReaction = useCallback(
    (value: number) => {
      const globalIdx = ROLEPLAY_SCENES.findIndex(
        (s) => s.code === currentScene.code
      )
      const idxKey = globalIdx >= 0 ? globalIdx : safeSceneIndex

      update({
        answers: {
          ...assessment.answers,
          [currentScene.code]: value,
          [`1-${idxKey}`]: value,
        },
      })

      if (autoAdvanceTimer.current) {
        window.clearTimeout(autoAdvanceTimer.current)
      }
      autoAdvanceTimer.current = window.setTimeout(() => {
        if (safeSceneIndex < activeScenes.length - 1) {
          setSceneIndex((prev) => Math.min(activeScenes.length - 1, prev + 1))
        }
      }, 220)
    },
    [
      currentScene.code,
      safeSceneIndex,
      assessment.answers,
      update,
      activeScenes.length,
    ]
  )

  // Select an option in Step 2 and auto-advance smoothly
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

  // Keyboard shortcuts (1-5 in Step 1, A-D or 1-4 in Step 2, Left/Right arrows)
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (
        document.activeElement?.tagName === "INPUT" ||
        document.activeElement?.tagName === "TEXTAREA"
      ) {
        return
      }
      if (step === 1) {
        if (["1", "2", "3", "4", "5"].includes(e.key)) {
          e.preventDefault()
          handleSelectReaction(Number(e.key))
        } else if (e.key === "ArrowRight") {
          setSceneIndex((p) => Math.min(activeScenes.length - 1, p + 1))
        } else if (e.key === "ArrowLeft") {
          setSceneIndex((p) => Math.max(0, p - 1))
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
    handleSelectReaction,
    handleSelectCognitive,
    activeScenes.length,
    cognitiveQuestions.length,
  ])

  const handleCompleteAssessment = () => {
    const normalizedScores = Object.entries(scores).map(([subject, score]) => ({
      subject,
      score,
      zScore: (score - 7.1) / 1.2,
    }))
    recordCompletedAttempt({
      ...assessment,
      step: 3,
      scores: normalizedScores,
      completed: true,
    })

    // Send answers to backend in background
    const riasecMap: Record<string, number> = {}
    riasecQuestions.forEach((q, idx) => {
      const val = assessment.answers[q.code] ?? assessment.answers[`1-${idx}`]
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

  const currentGlobalIndex = ROLEPLAY_SCENES.findIndex(
    (s) => s.code === currentScene.code
  )
  const currentSceneValue =
    assessment.answers[currentScene.code] ??
    assessment.answers[`1-${currentGlobalIndex}`]

  const currentCogValue =
    assessment.cognitive[currentCog.code] ??
    assessment.cognitive[`2-${cogIndex}`]

  return (
    <section className="py-5 sm:py-7">
      <PageContainer className="max-w-3xl">
        {/* Top Game HUD Bar (Liquid Glass, Unified Sky/Cyan Palette) */}
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-white/80 bg-white/70 px-4 py-3 shadow-[0_8px_28px_rgba(14,165,233,0.08)] backdrop-blur-xl">
          <div className="flex items-center gap-2.5">
            <span className="grid size-9 place-items-center rounded-xl bg-gradient-to-br from-sky-500 to-cyan-500 text-white shadow-sm">
              <Gamepad2 className="size-5" />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-black tracking-tight text-slate-900">
                  Hành Trình Khám Phá Tương Lai
                </h1>
                <span className="rounded-full bg-sky-100 px-2 py-0.5 text-[10px] font-black text-sky-700">
                  {totalXP} XP
                </span>
              </div>
              <p className="text-[11px] font-semibold text-slate-500">
                Nhập vai tương tác · Mở khóa 435 ngành chuẩn Bộ GD&ĐT
              </p>
            </div>
          </div>

          {/* 3-Quest Step Switcher */}
          <div className="flex items-center gap-1.5">
            {[
              { id: 1, label: "1. Nhập vai", done: allRiasecGroupsCovered },
              {
                id: 2,
                label: "2. Phản xạ",
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
            {(totalRiasecAnswered > 0 || totalCognitiveAnswered > 0) && (
              <button
                type="button"
                onClick={resetAllAnswers}
                title="Chơi lại từ đầu"
                className="ml-1 grid size-8 place-items-center rounded-xl border border-slate-200/80 bg-white/80 text-slate-500 transition hover:border-sky-300 hover:text-sky-700"
              >
                <RotateCcw className="size-3.5" />
              </button>
            )}
          </div>
        </div>

        {loading && step < 3 && (
          <div className="mb-4 flex items-center justify-center gap-2 rounded-2xl border border-sky-100 bg-white/70 p-3 text-slate-500 backdrop-blur-md">
            <Loader2 className="size-4 animate-spin text-sky-600" />
            <span className="text-xs font-semibold">
              Đang đồng bộ chặng hành trình...
            </span>
          </div>
        )}

        {/* ==================== STEP 1: ROLEPLAY ODYSSEY ==================== */}
        {step === 1 && (
          <div className="space-y-4">
            {/* 6-Station Odyssey Map Bar + Mode Toggle */}
            <div className="rounded-2xl border border-white/80 bg-white/70 p-3 shadow-[0_8px_24px_rgba(14,165,233,0.06)] backdrop-blur-xl">
              <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2 px-1">
                <div className="flex items-center gap-2">
                  <Compass className="size-4 text-sky-600" />
                  <span className="text-xs font-black text-slate-800">
                    Bản đồ 6 Trạm Trải Nghiệm ({totalRiasecAnswered}/
                    {quickMode18 ? 18 : 30})
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => {
                      setQuickMode18(true)
                      setSceneIndex(0)
                    }}
                    className={`rounded-lg px-2.5 py-1 text-[11px] font-extrabold transition ${
                      quickMode18
                        ? "bg-sky-600 text-white"
                        : "bg-sky-50 text-sky-700 hover:bg-sky-100"
                    }`}
                  >
                    ⚡ Nhanh (18 cảnh)
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setQuickMode18(false)
                      setSceneIndex(0)
                    }}
                    className={`rounded-lg px-2.5 py-1 text-[11px] font-extrabold transition ${
                      !quickMode18
                        ? "bg-sky-600 text-white"
                        : "bg-sky-50 text-sky-700 hover:bg-sky-100"
                    }`}
                  >
                    Đầy đủ (30 cảnh)
                  </button>
                </div>
              </div>

              {/* 6 Interactive Station Pills */}
              <div className="grid grid-cols-3 gap-1.5 sm:grid-cols-6">
                {STATIONS_META.map((station) => {
                  const isCurrentStation = currentScene.group === station.group
                  const count = riasecGroupCounts[station.group] || 0
                  const target = quickMode18 ? 3 : 5
                  const isDone = count >= target
                  const firstSceneIdx = activeScenes.findIndex(
                    (s) => s.group === station.group
                  )

                  return (
                    <button
                      key={station.group}
                      type="button"
                      onClick={() => {
                        if (firstSceneIdx >= 0) setSceneIndex(firstSceneIdx)
                      }}
                      className={`group relative overflow-hidden rounded-xl border px-2.5 py-2 text-left transition ${
                        isCurrentStation
                          ? "border-sky-500 bg-gradient-to-br from-sky-500 to-cyan-600 text-white shadow-sm"
                          : isDone
                            ? "border-sky-200 bg-sky-50/90 text-sky-900 hover:border-sky-400"
                            : "border-slate-200/70 bg-white/80 text-slate-600 hover:border-sky-200"
                      }`}
                    >
                      <div className="flex items-center justify-between text-[10px] font-black">
                        <span>TRẠM {station.group}</span>
                        <span>
                          {Math.min(count, target)}/{target}
                        </span>
                      </div>
                      <p className="mt-0.5 truncate text-[11px] font-bold">
                        {station.shortName}
                      </p>
                      <div className="mt-1.5 h-1 w-full overflow-hidden rounded-full bg-black/10">
                        <div
                          className={`h-full rounded-full transition-all ${
                            isCurrentStation ? "bg-white" : "bg-sky-500"
                          }`}
                          style={{
                            width: `${Math.min(
                              100,
                              riasecEnergy[station.group] || 0
                            )}%`,
                          }}
                        />
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Main Interactive Roleplay Scene Stage */}
            <motion.div
              key={currentScene.code}
              initial={{ opacity: 0, y: 8, scale: 0.99 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ duration: 0.2 }}
              className="rounded-[26px] border border-white/85 bg-white/75 p-5 sm:p-6 shadow-[0_16px_40px_rgba(14,165,233,0.1)] backdrop-blur-2xl"
            >
              {/* Scene Progress Dots */}
              <div className="mb-4 flex items-center justify-between gap-2">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-sky-100/90 px-3 py-1 text-xs font-black text-sky-800">
                  <Sparkles className="size-3.5 text-sky-600" />
                  Cảnh {safeSceneIndex + 1}/{activeScenes.length} ·{" "}
                  {currentScene.stationTitle}
                </span>

                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    disabled={safeSceneIndex === 0}
                    onClick={() => setSceneIndex((p) => Math.max(0, p - 1))}
                    className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-bold text-slate-600 transition hover:border-sky-300 disabled:opacity-40"
                  >
                    ← Trước
                  </button>
                  <button
                    type="button"
                    disabled={safeSceneIndex >= activeScenes.length - 1}
                    onClick={() =>
                      setSceneIndex((p) =>
                        Math.min(activeScenes.length - 1, p + 1)
                      )
                    }
                    className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-bold text-slate-600 transition hover:border-sky-300 disabled:opacity-40"
                  >
                    Tiếp →
                  </button>
                </div>
              </div>

              {/* Hologram Scene Illustration */}
              <RoleplaySceneVisual
                visualType={currentScene.visualType}
                group={currentScene.group}
                sceneBadge={currentScene.sceneBadge}
              />

              {/* Concise Action Scenario */}
              <div className="my-5 text-center">
                <h2 className="text-lg sm:text-xl font-black tracking-tight text-slate-900">
                  “{currentScene.actionTitle}”
                </h2>
                <p className="mt-1 text-xs font-semibold text-slate-500">
                  {currentScene.subHint}
                </p>
              </div>

              {/* 5 Interactive Reaction Cards (Auto-Advances on Click) */}
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
                {REACTION_CARDS.map((card) => {
                  const selected = currentSceneValue === card.value
                  return (
                    <button
                      key={card.value}
                      type="button"
                      onClick={() => handleSelectReaction(card.value)}
                      className={`group relative flex flex-col items-center justify-center rounded-2xl border p-3 text-center transition-all duration-150 ${
                        selected
                          ? "border-sky-500 bg-gradient-to-b from-sky-500 to-cyan-600 text-white shadow-[0_10px_24px_rgba(14,165,233,0.3)] -translate-y-0.5"
                          : "border-sky-100 bg-white/90 text-slate-800 hover:-translate-y-0.5 hover:border-sky-400 hover:bg-sky-50/70"
                      }`}
                    >
                      <span className="text-xl">{card.emoji}</span>
                      <span className="mt-1.5 text-xs font-black">
                        {card.shortLabel}
                      </span>
                      <span
                        className={`mt-1 rounded-full px-2 py-0.5 text-[10px] font-bold ${
                          selected
                            ? "bg-white/20 text-white"
                            : "bg-sky-50 text-sky-700"
                        }`}
                      >
                        Phím {card.keyHint}
                      </span>
                    </button>
                  )
                })}
              </div>

              {/* Quick Scene Jump Bar */}
              <div className="mt-5 flex flex-wrap items-center justify-center gap-1.5 pt-2 border-t border-slate-200/60">
                {activeScenes.map((s, idx) => {
                  const gIdx = ROLEPLAY_SCENES.findIndex(
                    (item) => item.code === s.code
                  )
                  const answered =
                    assessment.answers[s.code] !== undefined ||
                    assessment.answers[`1-${gIdx}`] !== undefined
                  const isCurr = idx === safeSceneIndex
                  return (
                    <button
                      key={s.code}
                      type="button"
                      onClick={() => setSceneIndex(idx)}
                      title={`${s.code}: ${s.actionTitle}`}
                      className={`h-2.5 rounded-full transition-all ${
                        isCurr
                          ? "w-6 bg-sky-600"
                          : answered
                            ? "w-2.5 bg-cyan-400 hover:bg-sky-500"
                            : "w-2.5 bg-slate-200 hover:bg-slate-300"
                      }`}
                    />
                  )
                })}
              </div>
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
            {/* Header & 8-Challenge Progress */}
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

            {/* 4 Interactive Choice Cards (A, B, C, D) */}
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
            disabled={step === 1 && safeSceneIndex === 0}
            onClick={() => {
              if (step === 1 && safeSceneIndex > 0) {
                setSceneIndex((p) => Math.max(0, p - 1))
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

          <div className="flex items-center gap-2.5">
            {step === 1 && !allRiasecGroupsCovered && (
              <span className="text-xs font-bold text-slate-500">
                Cần tối thiểu 18 cảnh ({totalRiasecAnswered}/18) để qua Chặng 2
              </span>
            )}

            {step === 1 && (
              <Button
                icon={ArrowRight}
                disabled={!allRiasecGroupsCovered}
                onClick={() => {
                  setStep(2)
                  update({ step: 2 })
                  window.scrollTo({ top: 0, behavior: "smooth" })
                }}
              >
                Qua Chặng 2: Phản Xạ ({totalRiasecAnswered}/
                {quickMode18 ? 18 : 30})
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
                Qua Chặng 3: Nạp Điểm ({totalCognitiveAnswered}/
                {cognitiveQuestions.length})
              </Button>
            )}

            {step === 3 && (
              <Button
                icon={Check}
                disabled={!canContinue}
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
