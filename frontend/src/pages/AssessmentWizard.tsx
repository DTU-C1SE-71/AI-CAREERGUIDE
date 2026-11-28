import confetti from "canvas-confetti"
import { AnimatePresence, motion, useMotionValue, useTransform } from "framer-motion"
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  Clock,
  History,
  Layers,
  LayoutDashboard,
  ListChecks,
  Loader2,
  LockKeyhole,
  RotateCcw,
  Sliders,
  Sparkles,
} from "lucide-react"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useNavigate, useSearchParams } from "react-router"
import {
  AcademicInputForm,
  HIGH_SCHOOL_SUBJECTS,
  type SubjectGrade,
} from "../components/assessment/AcademicInputForm"
import { CognitiveOptionIcon } from "../components/assessment/CognitiveOptionIcon"
import {
  LiveRiasecHexagon,
  QuestionIllustrationFrame,
} from "../components/assessment/OnetSwipeCardVisual"
import { Button } from "../components/common/Button"
import { PageContainer } from "../components/layout/PageContainer"
import { useAuth } from "../context/AuthContext"
import {
  defaultCognitiveQuestions,
  legacyCognitiveQuestions,
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
import { apiRequest, currentToken, requestJSON } from "../services/api"
import type { AssessmentHistoryItem, AssessmentState, CareerAspirationInput } from "../types/assessment"
import { evaluateAssessmentCompleteness } from "../utils/assessmentEvidence"
import { getValidRiasecAnswer } from "../utils/assessmentPayload"

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

function resolveCogQuestionsForAttempt(
  cog: Record<string, string | number> | undefined,
  activeCogQuestions: CognitiveQuestionItem[],
): CognitiveQuestionItem[] {
  const safe = cog || {}
  const hasV2 = Object.keys(safe).some(
    (k) =>
      k.startsWith("COG_V2_") ||
      /^(analytical|abstract|spatial|linguistic)_[12]$/.test(k),
  )
  const hasLegacy = legacyCognitiveQuestions.some(
    (q) => q.code in safe || (q.dimension ? q.dimension in safe : false),
  )
  return !hasV2 && hasLegacy ? legacyCognitiveQuestions : activeCogQuestions
}

function buildWizardProfileFingerprint(
  answers: Record<string, number>,
  cognitive: Record<string, string | number> | undefined,
  scoresMap: Record<string, number>,
  aspiration: CareerAspirationInput | undefined,
  cogQuestions: CognitiveQuestionItem[],
): string {
  const riasecNorm: Record<string, number> = {}
  CANONICAL_30_CODES.forEach((code, idx) => {
    const val = getValidRiasecAnswer(answers, code, idx)
    if (val !== undefined) riasecNorm[code] = val
  })
  const cogNorm: Record<string, string> = {}
  cogQuestions.forEach((q, idx) => {
    const v =
      cognitive?.[q.code] ??
      (q.dimension ? cognitive?.[q.dimension] : undefined) ??
      cognitive?.[`2-${idx}`]
    if (v !== undefined && v !== null && String(v).trim()) {
      cogNorm[q.code] = String(v).trim().toUpperCase()
    }
  })
  const scoresNorm = Object.entries(scoresMap)
    .filter(([, s]) => Number.isFinite(s) && s >= 0 && s <= 10)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([subj, s]) => `${subj}:${s.toFixed(2)}`)
  const asp = aspiration
    ? {
        dreamJob: (aspiration.dreamJob || "").trim(),
        desiredField: (aspiration.desiredField || "").trim(),
        workValues: [...(aspiration.workValues || [])].sort(),
        preferredEnvironment: (aspiration.preferredEnvironment || "").trim(),
        scoreStrategy: aspiration.scoreStrategy || "FLEXIBLE_PATHWAY",
      }
    : null
  return JSON.stringify({
    riasec: riasecNorm,
    cognitive: cogNorm,
    scores: scoresNorm,
    aspiration: asp,
  })
}

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
  const { user, token } = useAuth()
  const {
    assessment,
    history,
    activeHistoryId,
    update,
    reset,
    recordCompletedAttempt,
    updateHistoryAttempt,
    linkHistoryAttemptSubmission,
    selectHistoryAttempt,
  } = useAssessment()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [sessionStarted, setSessionStarted] = useState<boolean>(
    () => searchParams.get("new") === "true" || searchParams.get("review") === "true",
  )
  const [showHistoryPicker, setShowHistoryPicker] = useState(false)
  const [isReviewMode, setIsReviewMode] = useState<boolean>(
    () => searchParams.get("review") === "true",
  )
  const [editingAttemptId, setEditingAttemptId] = useState<string | null>(null)
  const [reviewBaselineFingerprint, setReviewBaselineFingerprint] = useState<string | null>(null)
  const [saveEditError, setSaveEditError] = useState<string | null>(null)
  const submittingRef = useRef(false)
  const [submitting, setSubmitting] = useState(false)
  const [step, setStep] = useState<number>(() => {
    const paramStep = Number(searchParams.get("step"))
    if (Number.isInteger(paramStep) && paramStep >= 1 && paramStep <= 3) {
      return paramStep
    }
    return Math.min(Math.max(1, assessment.step || 1), 3)
  })
  const [scores, setScores] = useState<Record<string, number>>(() => {
    const mapped = Object.fromEntries(
      assessment.scores.map((s) => [s.subject, s.score])
    )
    const initial: Record<string, number> = {}
    HIGH_SCHOOL_SUBJECTS.forEach((subj) => {
      const existing = mapped[subj.name]
      if (typeof existing === "number" && Number.isFinite(existing)) {
        initial[subj.name] = existing
      }
    })
    return initial
  })
  const [loading, setLoading] = useState(true)
  const [riasecQuestions, setRiasecQuestions] = useState<QuestionItem[]>(
    defaultRiasecFallback
  )
  const [cognitiveQuestions, setCognitiveQuestions] = useState<
    CognitiveQuestionItem[]
  >(defaultCognitiveQuestions)

  // Step 1 Mode: 'swipe' (Thẻ) | 'list' (Danh sách 30 câu) | 'radar' (Radar tổng quan)
  const [step1Mode, setStep1Mode] = useState<"swipe" | "radar" | "list">(
    () => (searchParams.get("review") === "true" ? "list" : "swipe"),
  )
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
  const [step2Mode, setStep2Mode] = useState<"swipe" | "list">(
    () => (searchParams.get("review") === "true" ? "list" : "swipe"),
  )
  const [cogIndex, setCogIndex] = useState(0)
  const [cogDirection, setCogDirection] = useState(1)
  const [expandedCogOptions, setExpandedCogOptions] = useState<Record<string, boolean>>({})
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
                const fbOptMap = new Map(
                  (fb?.options || []).map((opt) => [
                    opt.option_key.toUpperCase(),
                    opt,
                  ])
                )
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
                    ? q.options.map((opt) => {
                        const fbOpt = fbOptMap.get(opt.option_key.toUpperCase())
                        return {
                          option_key: opt.option_key,
                          trait_code:
                            opt.trait_code || fbOpt?.trait_code || "",
                          label: fbOpt?.label || opt.title,
                          description:
                            fbOpt?.description || opt.description || "",
                          icon: fbOpt?.icon || "Sparkles",
                        }
                      })
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

  const handleRateByCode = useCallback(
    (code: string, value: number) => {
      const cIdx = CANONICAL_30_CODES.indexOf(code)
      const nextAnswers = {
        ...assessment.answers,
        [code]: value,
        ...(cIdx >= 0 ? { [`1-${cIdx}`]: value } : {}),
      }
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
      const val = getValidRiasecAnswer(assessment.answers, code, idx)
      if (typeof val === "number" && val >= 1 && val <= 5) {
        counts[code[0] as RiasecDimension] += 1
      }
    })
    return counts
  }, [assessment.answers])

  const riasecGroupPct = useMemo(() => {
    const pct: Record<RiasecDimension, number> = {
      R: 0,
      I: 0,
      A: 0,
      S: 0,
      E: 0,
      C: 0,
    }
    RIASEC_ORDER.forEach((dim) => {
      const vals = ONET_MINI_IP_ITEMS.filter((i) => i.dimension === dim)
        .map((i) => {
          const cIdx = CANONICAL_30_CODES.indexOf(i.code)
          return getValidRiasecAnswer(assessment.answers, i.code, cIdx)
        })
        .filter((v): v is number => v !== undefined)
      if (vals.length > 0) {
        const avg = vals.reduce((a, b) => a + b, 0) / vals.length
        pct[dim] = Math.round(((avg - 1) / 4) * 100)
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
          return getValidRiasecAnswer(assessment.answers, i.code, cIdx)
        })
        .filter((v): v is number => v !== undefined)
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

  const aspiration: CareerAspirationInput = useMemo(
    () =>
      assessment.aspiration || {
        dreamJob: "",
        desiredField: "",
        workValues: [],
        scoreStrategy: "FLEXIBLE_PATHWAY",
      },
    [assessment.aspiration]
  )

  const displayedCognitiveQuestions = useMemo(() => {
    if (!isReviewMode) return cognitiveQuestions
    return resolveCogQuestionsForAttempt(assessment.cognitive, cognitiveQuestions)
  }, [isReviewMode, assessment.cognitive, cognitiveQuestions])

  const currentReviewFingerprint = useMemo(
    () =>
      buildWizardProfileFingerprint(
        assessment.answers,
        assessment.cognitive,
        scores,
        aspiration,
        displayedCognitiveQuestions,
      ),
    [assessment.answers, assessment.cognitive, scores, aspiration, displayedCognitiveQuestions],
  )

  const hasReviewChanges = Boolean(
    isReviewMode &&
      reviewBaselineFingerprint &&
      currentReviewFingerprint !== reviewBaselineFingerprint,
  )

  useEffect(() => {
    if (!isReviewMode || reviewBaselineFingerprint) return
    const targetId =
      activeHistoryId ||
      history[0]?.id ||
      (assessment.submissionId ? `db-${assessment.submissionId}` : null)
    const sourceAttempt = history.find((h) => h.id === targetId) || null
    const baseAnswers = sourceAttempt?.answers || assessment.answers || {}
    const baseCognitive = sourceAttempt?.cognitive || assessment.cognitive || {}
    const baseScoresMap: Record<string, number> = {}
    ;(sourceAttempt?.scores || assessment.scores || []).forEach((s) => {
      if (s.subject && typeof s.score === "number" && Number.isFinite(s.score)) {
        baseScoresMap[s.subject] = s.score
      }
    })
    const baseCogQuestions = resolveCogQuestionsForAttempt(baseCognitive, cognitiveQuestions)
    setEditingAttemptId(targetId)
    setReviewBaselineFingerprint(
      buildWizardProfileFingerprint(
        baseAnswers,
        baseCognitive,
        baseScoresMap,
        sourceAttempt?.aspiration || assessment.aspiration,
        baseCogQuestions,
      ),
    )
  }, [
    isReviewMode,
    reviewBaselineFingerprint,
    activeHistoryId,
    history,
    assessment.answers,
    assessment.cognitive,
    assessment.scores,
    assessment.aspiration,
    assessment.submissionId,
    cognitiveQuestions,
  ])

  const totalCognitiveAnswered = useMemo(() => {
    return displayedCognitiveQuestions.filter((q, idx) => {
      const v =
        assessment.cognitive[q.code] ??
        (q.dimension ? assessment.cognitive[q.dimension] : undefined) ??
        assessment.cognitive[`2-${idx}`]
      return v !== undefined && v !== null && String(v).trim() !== ""
    }).length
  }, [assessment.cognitive, displayedCognitiveQuestions])

  const completeness = useMemo(
    () =>
      evaluateAssessmentCompleteness(
        {
          answers: assessment.answers,
          cognitive: assessment.cognitive,
          scores,
        },
        displayedCognitiveQuestions,
      ),
    [assessment.answers, assessment.cognitive, scores, displayedCognitiveQuestions],
  )

  const safeCogIndex = Math.min(
    cogIndex,
    Math.max(0, displayedCognitiveQuestions.length - 1),
  )
  const currentCog =
    displayedCognitiveQuestions[safeCogIndex] || displayedCognitiveQuestions[0]
  const currentCogValue =
    assessment.cognitive[currentCog.code] ??
    (currentCog.dimension ? assessment.cognitive[currentCog.dimension] : undefined) ??
    assessment.cognitive[`2-${safeCogIndex}`]

  const goToNextCog = useCallback(() => {
    setCogDirection(1)
    setCogIndex((p) => Math.min(displayedCognitiveQuestions.length - 1, p + 1))
  }, [displayedCognitiveQuestions.length])

  const goToPrevCog = useCallback(() => {
    setCogDirection(-1)
    setCogIndex((p) => Math.max(0, p - 1))
  }, [])

  const openHistoryAttemptForReview = useCallback(
    (item: AssessmentHistoryItem, keepCurrentStep = false) => {
      selectHistoryAttempt(item.id)
      const nextScores: Record<string, number> = {}
      ;(item.scores || []).forEach((s) => {
        if (s.subject && typeof s.score === "number" && Number.isFinite(s.score)) {
          nextScores[s.subject] = s.score
        }
      })
      const attemptCogQs = resolveCogQuestionsForAttempt(
        item.cognitive,
        cognitiveQuestions,
      )
      setEditingAttemptId(item.id)
      setReviewBaselineFingerprint(
        buildWizardProfileFingerprint(
          item.answers || {},
          item.cognitive || {},
          nextScores,
          item.aspiration,
          attemptCogQs,
        ),
      )
      setSaveEditError(null)
      setScores(nextScores)
      setIsReviewMode(true)
      setStep1Mode("list")
      setStep2Mode("list")
      setCardIndex(0)
      setCogIndex(0)
      setShowHistoryPicker(false)
      setSessionStarted(true)
      if (!keepCurrentStep) {
        setStep(1)
        window.scrollTo({ top: 0, behavior: "smooth" })
      }
    },
    [selectHistoryAttempt, cognitiveQuestions],
  )

  const handleSelectCognitiveByIndex = useCallback(
    (code: string, idx: number, optionKey: string) => {
      const qKey = code || `2-${idx}`
      update({
        cognitive: {
          ...assessment.cognitive,
          [qKey]: optionKey,
          [`2-${idx}`]: optionKey,
        },
      })
    },
    [assessment.cognitive, update],
  )

  const handleSelectCognitive = useCallback(
    (optionKey: string) => {
      const qKey = currentCog.code || `2-${safeCogIndex}`
      update({
        cognitive: {
          ...assessment.cognitive,
          [qKey]: optionKey,
          [`2-${safeCogIndex}`]: optionKey,
        },
      })

      if (autoAdvanceTimer.current) window.clearTimeout(autoAdvanceTimer.current)
      autoAdvanceTimer.current = window.setTimeout(() => {
        if (safeCogIndex < displayedCognitiveQuestions.length - 1) {
          setCogDirection(1)
          setCogIndex((prev) =>
            Math.min(displayedCognitiveQuestions.length - 1, prev + 1),
          )
        }
      }, 350)
    },
    [
      currentCog.code,
      safeCogIndex,
      assessment.cognitive,
      update,
      displayedCognitiveQuestions.length,
    ],
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
      } else if (step === 2 && step2Mode === "swipe") {
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
        const chosenKey = keyMap[e.key]
        if (
          chosenKey &&
          currentCog?.options.some((opt) => opt.option_key === chosenKey)
        ) {
          e.preventDefault()
          handleSelectCognitive(chosenKey)
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
    step2Mode,
    rateCurrentCard,
    goToNextCard,
    goToPrevCard,
    handleSelectCognitive,
    goToNextCog,
    goToPrevCog,
    currentCog,
  ])

  const resetAllAnswers = () => {
    reset()
    setScores({})
    setStep1Mode("swipe")
    setStep2Mode("swipe")
    setCardIndex(0)
    setCogIndex(0)
    setStep(1)
    setIsReviewMode(false)
    setEditingAttemptId(null)
    setReviewBaselineFingerprint(null)
    setSaveEditError(null)
  }

  const handleSaveReviewChanges = async (
    navigateAfter: "dashboard" | "stay" | "close",
  ) => {
    if (submittingRef.current) return
    if (!hasReviewChanges) {
      if (navigateAfter === "dashboard") navigate("/dashboard")
      else if (navigateAfter === "close") setSessionStarted(false)
      return
    }
    if (!completeness.isComplete) {
      const firstMissing = completeness.missingSteps[0]
      if (firstMissing) {
        setStep(firstMissing)
        update({ step: firstMissing })
        window.scrollTo({ top: 0, behavior: "smooth" })
      }
      return
    }
    if (
      Object.values(scores).some(
        (value) => !Number.isFinite(value) || value < 0 || value > 10,
      )
    ) {
      setStep(3)
      return
    }

    submittingRef.current = true
    setSubmitting(true)
    setSaveEditError(null)

    const finalAnswers: Record<string, number> = {}
    CANONICAL_30_CODES.forEach((code, idx) => {
      const value = getValidRiasecAnswer(assessment.answers, code, idx)
      if (value !== undefined) finalAnswers[code] = value
    })

    const finalCog: Record<string, string> = {}
    displayedCognitiveQuestions.forEach((q, idx) => {
      const val =
        assessment.cognitive[q.code] ??
        (q.dimension ? assessment.cognitive[q.dimension] : undefined) ??
        assessment.cognitive[`2-${idx}`]
      if (typeof val === "string" && val.trim()) {
        finalCog[q.code] = val.trim().toUpperCase()
      }
    })

    const normalizedScores: SubjectGrade[] = Object.entries(scores)
      .filter(([, score]) => Number.isFinite(score) && score >= 0 && score <= 10)
      .map(([subject, score]) => ({ subject, score, zScore: null }))

    const aspirationPayload = {
      dream_job: aspiration.dreamJob || "",
      desired_field: aspiration.desiredField || "",
      work_values: aspiration.workValues || [],
      preferred_environment: aspiration.preferredEnvironment || "",
      score_strategy: aspiration.scoreStrategy || "FLEXIBLE_PATHWAY",
    }

    const targetHistoryId =
      editingAttemptId || activeHistoryId || history[0]?.id || null
    const targetSubmissionId = targetHistoryId?.startsWith("db-")
      ? targetHistoryId.slice(3)
      : assessment.submissionId

    try {
      let resolvedHistoryId = targetHistoryId
      let changedFlag = true

      if (token && targetSubmissionId) {
        const res = await requestJSON<{
          submission_id?: string
          changed?: boolean
        }>(`/assessment/submissions/${encodeURIComponent(targetSubmissionId)}`, {
          method: "PUT",
          body: JSON.stringify({
            riasec_answers: finalAnswers,
            cognitive_answers: finalCog,
            aspiration: aspirationPayload,
            grades_by_subject: Object.fromEntries(
              normalizedScores.map(({ subject, score }) => [subject, score]),
            ),
            score_context: { kind: "TRANSCRIPT", scale: 10 },
          }),
        })
        changedFlag = res?.changed !== false
        resolvedHistoryId = targetHistoryId || `db-${res?.submission_id || targetSubmissionId}`
      } else if (token) {
        const res = await requestJSON<{ submission_id?: string }>(
          "/assessment/submit",
          {
            method: "POST",
            body: JSON.stringify({
              riasec_answers: finalAnswers,
              cognitive_answers: finalCog,
              aspiration: aspirationPayload,
              grades_by_subject: Object.fromEntries(
                normalizedScores.map(({ subject, score }) => [subject, score]),
              ),
              score_context: { kind: "TRANSCRIPT", scale: 10 },
            }),
          },
        )
        if (res?.submission_id && targetHistoryId) {
          linkHistoryAttemptSubmission(targetHistoryId, res.submission_id)
          resolvedHistoryId = `db-${res.submission_id}`
        } else if (res?.submission_id) {
          resolvedHistoryId = `db-${res.submission_id}`
        }
      }

      if (currentToken() !== token) return

      const nextState: AssessmentState = {
        ...assessment,
        step: 4,
        answers: finalAnswers,
        cognitive: finalCog,
        scores: normalizedScores,
        aspiration: assessment.aspiration,
        completed: true,
        syncStatus: resolvedHistoryId?.startsWith("db-")
          ? "SYNCED"
          : assessment.syncStatus,
        submissionId: resolvedHistoryId?.startsWith("db-")
          ? resolvedHistoryId.slice(3)
          : assessment.submissionId,
      }

      if (resolvedHistoryId) {
        updateHistoryAttempt(resolvedHistoryId, nextState, {
          bumpRevision: changedFlag,
        })
        setEditingAttemptId(resolvedHistoryId)
      } else {
        update(nextState)
      }

      setReviewBaselineFingerprint(
        buildWizardProfileFingerprint(
          finalAnswers,
          finalCog,
          scores,
          aspiration,
          displayedCognitiveQuestions,
        ),
      )

      if (navigateAfter === "dashboard") {
        navigate("/dashboard")
      } else if (navigateAfter === "close") {
        setSessionStarted(false)
      }
    } catch (err) {
      setSaveEditError(
        err instanceof Error && err.message
          ? err.message
          : "Chưa lưu được thay đổi vào CSDL. Vui lòng thử lại.",
      )
    } finally {
      submittingRef.current = false
      setSubmitting(false)
    }
  }

  const handleCompleteAssessment = async (skipAspiration = false) => {
    if (submittingRef.current) return
    if (!completeness.isComplete) {
      const firstMissing = completeness.missingSteps[0]
      if (firstMissing) {
        setStep(firstMissing)
        update({ step: firstMissing })
        window.scrollTo({ top: 0, behavior: "smooth" })
      }
      return
    }
    if (Object.values(scores).some(value => !Number.isFinite(value) || value < 0 || value > 10)) { setStep(3); return }
    submittingRef.current = true
    setSubmitting(true)
    const finalAnswers: Record<string, number> = {}
    CANONICAL_30_CODES.forEach((code, idx) => {
      const value = getValidRiasecAnswer(assessment.answers, code, idx)
      if (value !== undefined) finalAnswers[code] = value
    })

    const normalizedScores: SubjectGrade[] = Object.entries(scores)
      .filter(([, score]) => Number.isFinite(score) && score >= 0 && score <= 10)
      .map(([subject, score]) => ({ subject, score, zScore: null }))

    const effectiveAspiration = skipAspiration
      ? {
          dreamJob: "",
          desiredField: "",
          workValues: [],
          preferredEnvironment: "",
          scoreStrategy: "FLEXIBLE_PATHWAY" as const,
        }
      : aspiration

    const localAttempt = recordCompletedAttempt({
      ...assessment,
      answers: finalAnswers,
      step: 3,
      scores: normalizedScores,
      aspiration: skipAspiration ? undefined : effectiveAspiration,
      completed: true,
      syncStatus: "LOCAL_ONLY",
      submissionId: undefined,
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

    const aspirationPayload = {
      dream_job: effectiveAspiration.dreamJob || "",
      desired_field: effectiveAspiration.desiredField || "",
      work_values: effectiveAspiration.workValues || [],
      preferred_environment: effectiveAspiration.preferredEnvironment || "",
      score_strategy: effectiveAspiration.scoreStrategy || "FLEXIBLE_PATHWAY",
    }

    // Local storage is already durable; server success requires a returned snapshot ID.
    const controller = new AbortController()
    const timeout = window.setTimeout(() => controller.abort(), 15000)
    let result: { submission_id?: string } | null = null
    try {
      result = await apiRequest<{ submission_id?: string } | null>("/assessment/submit", null, {
        method: "POST",
        signal: controller.signal,
        body: JSON.stringify({
          riasec_answers: riasecMap,
          cognitive_answers: cogMap,
          aspiration: aspirationPayload,
          grades_by_subject: Object.fromEntries(normalizedScores.map(({ subject, score }) => [subject, score])),
          score_context: { kind: "TRANSCRIPT", scale: 10 },
        }),
      })
    } catch {
      result = null
    } finally {
      window.clearTimeout(timeout)
      submittingRef.current = false
      setSubmitting(false)
    }
    if (currentToken() !== token) return
    if (result?.submission_id) {
      linkHistoryAttemptSubmission(localAttempt.id, result.submission_id)
      update({ syncStatus: "SYNCED", submissionId: result.submission_id })
      confetti({ particleCount: 75, spread: 65, origin: { y: 0.6 } })
    } else {
      update({ syncStatus: "LOCAL_ONLY", submissionId: undefined })
    }
    navigate("/dashboard")
  }

  // 1. CỔNG XÁC THỰC: Chưa đăng nhập => Tuyệt đối không cho phép làm bài trắc nghiệm
  if (!user || !token) {
    return (
      <section className="relative flex min-h-[75vh] items-center justify-center py-12 overflow-x-clip">
        <PageContainer className="relative z-10 max-w-lg">
          <div className="rounded-3xl border border-white/80 bg-white/70 p-8 text-center shadow-[0_20px_50px_rgba(14,165,233,0.12)] backdrop-blur-2xl">
            <div className="mx-auto mb-5 grid size-16 place-items-center rounded-2xl border border-sky-200 bg-sky-50 text-sky-600 shadow-inner">
              <LockKeyhole className="size-8" />
            </div>
            <span className="inline-block rounded-full border border-sky-200 bg-sky-50/80 px-3 py-1 text-[11px] font-extrabold uppercase tracking-wider text-sky-700">
              Yêu cầu đăng nhập tài khoản
            </span>
            <h2 className="mt-3 text-2xl font-black text-slate-900 sm:text-3xl">
              Đăng nhập để làm bài trắc nghiệm
            </h2>
            <p className="mt-3 text-sm font-medium leading-relaxed text-slate-600">
              Để hệ thống AI lưu trữ kết quả, đối chiếu học lực Z-Score chuẩn Bộ GD&ĐT và đồng bộ hồ sơ hướng nghiệp, bạn cần đăng nhập tài khoản trước khi thực hiện.
            </p>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row">
              <Button
                type="button"
                className="flex-1"
                icon={ArrowRight}
                onClick={() => navigate("/login")}
              >
                Đăng nhập ngay
              </Button>
              <button
                type="button"
                onClick={() => navigate("/login?tab=register")}
                className="flex-1 rounded-xl border border-slate-200 bg-white/80 py-3 text-xs font-bold text-slate-700 backdrop-blur-md transition hover:border-sky-300 hover:bg-slate-50 hover:text-sky-700"
              >
                Đăng ký tài khoản
              </button>
            </div>
          </div>
        </PageContainer>
      </section>
    )
  }

  // 2. CỔNG CHỌN ĐỐI VỚI TÀI KHOẢN ĐÃ CÓ BÀI TRẮC NGHIỆM:
  const hasCompletedAttempt = Boolean(assessment.completed || history.length > 0)
  if (hasCompletedAttempt && !sessionStarted) {
    if (showHistoryPicker && history.length > 0) {
      return (
        <section className="relative flex min-h-[72vh] items-center justify-center overflow-x-clip py-6 sm:py-10">
          <PageContainer className="relative z-10 w-full max-w-4xl xl:max-w-5xl">
            <div className="mb-6 flex items-center justify-between">
              <button
                type="button"
                onClick={() => setShowHistoryPicker(false)}
                className="inline-flex items-center gap-2 rounded-2xl border border-white/90 bg-white/75 px-4 py-2.5 text-xs sm:text-sm font-extrabold text-slate-700 shadow-xs backdrop-blur-md transition hover:bg-white hover:text-sky-700 hover:shadow-md"
              >
                <ArrowLeft className="size-4 text-sky-600" />
                <span>Quay lại</span>
              </button>
            </div>

            <div className="rounded-3xl border border-white/85 bg-white/85 p-6 sm:p-10 shadow-[0_24px_60px_rgba(14,165,233,0.14)] backdrop-blur-2xl">
              <div className="flex items-center gap-4">
                <div className="grid size-13 sm:size-14 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-sky-500 to-cyan-500 text-white shadow-md">
                  <History className="size-6 sm:size-7" />
                </div>
                <div>
                  <h1 className="text-xl sm:text-2xl lg:text-3xl font-black tracking-tight text-slate-900">
                    Chọn bài trắc nghiệm muốn xem lại
                  </h1>
                  <p className="mt-1.5 text-sm font-medium text-slate-600">
                    Bạn có {history.length} lần làm bài đã lưu. Chọn một bài bên dưới để xem lại toàn bộ câu trả lời và điểm số.
                  </p>
                </div>
              </div>

              <div className="mt-7 space-y-3.5">
                {history.map((item, idx) => {
                  const attemptNumber = history.length - idx
                  const riasecCount = Object.keys(item.answers || {}).filter((k) =>
                    /^[RIASEC][1-5]$/i.test(k),
                  ).length
                  const isLegacyItem =
                    Object.keys(item.cognitive || {}).some((k) =>
                      /^COG_[1-8]$/.test(k) ||
                      /^(learning_style|work_environment|problem_solving|interaction_target|gardner_intelligence|pressure_tolerance|output_preference|team_role)$/.test(k),
                    ) &&
                    !Object.keys(item.cognitive || {}).some((k) => k.startsWith("COG_V2_"))
                  const cogTotalForAttempt = isLegacyItem ? 8 : 10
                  const cogCount = isLegacyItem
                    ? legacyCognitiveQuestions.filter(
                        (q) =>
                          item.cognitive?.[q.code] ||
                          (q.dimension ? item.cognitive?.[q.dimension] : undefined),
                      ).length
                    : defaultCognitiveQuestions.filter(
                        (q) =>
                          item.cognitive?.[q.code] ||
                          (q.dimension ? item.cognitive?.[q.dimension] : undefined),
                      ).length
                  const dateLabel = formatAttemptDateTime(item.createdAt)

                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => openHistoryAttemptForReview(item, false)}
                      className="group flex w-full flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-slate-200/90 bg-white/95 p-5 text-left shadow-2xs transition-all hover:-translate-y-0.5 hover:border-sky-400 hover:bg-sky-50/40 hover:shadow-md cursor-pointer"
                    >
                      <div className="min-w-0 flex-1 space-y-2">
                        <div className="flex flex-wrap items-center gap-2.5">
                          <span className="inline-flex items-center gap-1.5 rounded-xl bg-sky-600 px-3 py-1 text-xs font-black text-white shadow-2xs">
                            Lần {attemptNumber}
                          </span>
                          {idx === 0 && (
                            <span className="rounded-full border border-sky-200 bg-sky-50 px-2.5 py-0.5 text-[11px] font-bold text-sky-700">
                              Mới nhất
                            </span>
                          )}
                          {dateLabel && (
                            <span className="inline-flex items-center gap-1 text-xs font-semibold text-slate-500">
                              <Clock className="size-3.5 text-slate-400" />
                              <span>{dateLabel}</span>
                            </span>
                          )}
                        </div>

                        <div className="flex flex-wrap items-center gap-2 text-xs font-semibold text-slate-600">
                          <span className="rounded-lg bg-slate-100 px-2.5 py-1">
                            {riasecCount}/30 câu sở thích
                          </span>
                          <span className="rounded-lg bg-slate-100 px-2.5 py-1">
                            {cogCount}/{cogTotalForAttempt} câu tư duy
                          </span>
                          {item.bestBlock && item.bestBlock !== "Chưa đủ tổ hợp môn" && (
                            <span className="rounded-lg bg-sky-50 px-2.5 py-1 text-sky-800">
                              Khối mạnh nhất: {item.bestBlock}
                            </span>
                          )}
                          {item.hollandCode && (
                            <span className="rounded-lg bg-sky-50 px-2.5 py-1 text-sky-800">
                              Holland: {item.hollandCode}
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="inline-flex shrink-0 items-center gap-1.5 text-sm font-black text-sky-700 group-hover:translate-x-0.5 transition">
                        <span>Xem bài này</span>
                        <ArrowRight className="size-4" />
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          </PageContainer>
        </section>
      )
    }

    return (
      <section className="relative flex min-h-[72vh] items-center justify-center overflow-x-clip py-6 sm:py-10">
        <PageContainer className="relative z-10 w-full max-w-4xl xl:max-w-5xl">
          {/* Nút quay lại trang phía ngoài (Dashboard) */}
          <div className="mb-6 flex items-center justify-between">
            <button
              type="button"
              onClick={() => navigate("/dashboard")}
              className="inline-flex items-center gap-2 rounded-2xl border border-white/90 bg-white/75 px-4 py-2.5 text-xs sm:text-sm font-extrabold text-slate-700 shadow-xs backdrop-blur-md transition hover:bg-white hover:text-sky-700 hover:shadow-md"
            >
              <ArrowLeft className="size-4 text-sky-600" />
              <span>Quay lại Dashboard</span>
            </button>
          </div>

          <div className="rounded-3xl border border-white/85 bg-white/85 p-8 sm:p-12 shadow-[0_24px_60px_rgba(14,165,233,0.14)] backdrop-blur-2xl">
            {/* Header chào mừng phóng to rõ ràng */}
            <div className="flex items-center gap-4 sm:gap-5">
              <div className="grid size-14 sm:size-16 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-sky-500 to-cyan-500 text-white shadow-md">
                <Sparkles className="size-7 sm:size-8" />
              </div>
              <div>
                <h1 className="text-2xl sm:text-3xl lg:text-4xl font-black tracking-tight text-slate-900">
                  Chào {user.name || "bạn"}, bạn muốn làm gì tiếp theo?
                </h1>
                <p className="mt-2 text-sm sm:text-base font-semibold text-slate-600">
                  Hệ thống đã lưu bài trắc nghiệm của bạn. Bạn có thể xem lại các câu hỏi đã trả lời hoặc bắt đầu bài trắc nghiệm mới.
                </p>
              </div>
            </div>

            {/* 2 Lựa chọn Lớn, Trực quan, Rõ Ràng */}
            <div className="mt-8 sm:mt-10 grid grid-cols-1 gap-5 sm:grid-cols-2">
              <button
                type="button"
                onClick={() => {
                  if (history.length > 1) {
                    setShowHistoryPicker(true)
                    return
                  }
                  if (history[0]) {
                    openHistoryAttemptForReview(history[0], false)
                    return
                  }
                  const nextScores: Record<string, number> = {}
                  assessment.scores.forEach((item) => {
                    if (item.subject && typeof item.score === "number" && Number.isFinite(item.score)) {
                      nextScores[item.subject] = item.score
                    }
                  })
                  setScores(nextScores)
                  setEditingAttemptId(
                    assessment.submissionId ? `db-${assessment.submissionId}` : null,
                  )
                  setReviewBaselineFingerprint(
                    buildWizardProfileFingerprint(
                      assessment.answers || {},
                      assessment.cognitive || {},
                      nextScores,
                      assessment.aspiration,
                      resolveCogQuestionsForAttempt(
                        assessment.cognitive,
                        cognitiveQuestions,
                      ),
                    ),
                  )
                  setSaveEditError(null)
                  setIsReviewMode(true)
                  setStep1Mode("list")
                  setStep2Mode("list")
                  setStep(1)
                  setCardIndex(0)
                  setCogIndex(0)
                  setSessionStarted(true)
                }}
                className="group flex flex-col justify-between rounded-3xl border border-sky-200/90 bg-gradient-to-br from-white via-sky-50/50 to-sky-100/40 p-6 sm:p-8 text-left shadow-sm transition-all duration-200 hover:-translate-y-1 hover:border-sky-400 hover:shadow-lg"
              >
                <div>
                  <div className="mb-5 flex items-center justify-between gap-2">
                    <div className="grid size-14 place-items-center rounded-2xl bg-sky-600 text-white shadow-md transition group-hover:scale-110">
                      <ClipboardCheck className="size-7" />
                    </div>
                    {history.length > 1 && (
                      <span className="inline-flex items-center gap-1.5 rounded-full border border-sky-200 bg-white/90 px-3 py-1 text-xs font-extrabold text-sky-700 shadow-2xs">
                        <History className="size-3.5" />
                        <span>{history.length} bài đã lưu</span>
                      </span>
                    )}
                  </div>
                  <h3 className="text-lg sm:text-xl font-black text-slate-900 group-hover:text-sky-700">
                    Xem các câu hỏi đã trả lời
                  </h3>
                  <p className="mt-2 text-sm font-medium leading-relaxed text-slate-600">
                    Xem lại toàn bộ 30 câu hỏi sở thích O*NET, các tình huống tư duy và mức điểm mà bạn đã lựa chọn.
                  </p>
                </div>
                <div className="mt-6 flex items-center gap-2 text-sm font-black text-sky-700">
                  <span>{history.length > 1 ? "Chọn bài để xem lại" : "Xem lại câu trả lời"}</span>
                  <ArrowRight className="size-4 transition group-hover:translate-x-1.5" />
                </div>
              </button>

              <button
                type="button"
                onClick={() => {
                  reset()
                  setScores({})
                  setStep1Mode("swipe")
                  setStep2Mode("swipe")
                  setStep(1)
                  setCardIndex(0)
                  setCogIndex(0)
                  setShowHistoryPicker(false)
                  setIsReviewMode(false)
                  setEditingAttemptId(null)
                  setReviewBaselineFingerprint(null)
                  setSaveEditError(null)
                  setSessionStarted(true)
                }}
                className="group flex flex-col justify-between rounded-3xl border border-slate-200/90 bg-white/90 p-6 sm:p-8 text-left shadow-sm transition-all duration-200 hover:-translate-y-1 hover:border-sky-300 hover:bg-slate-50/90 hover:shadow-lg"
              >
                <div>
                  <div className="mb-5 grid size-14 place-items-center rounded-2xl border border-slate-200 bg-slate-100 text-slate-700 shadow-sm transition group-hover:border-sky-200 group-hover:bg-sky-50 group-hover:text-sky-700 group-hover:scale-110">
                    <RotateCcw className="size-7" />
                  </div>
                  <h3 className="text-lg sm:text-xl font-black text-slate-900 group-hover:text-sky-700">
                    Bắt đầu làm trắc nghiệm mới
                  </h3>
                  <p className="mt-2 text-sm font-medium leading-relaxed text-slate-600">
                    Làm lại từ đầu bộ câu hỏi đánh giá hành vi O*NET để cập nhật lại thiên hướng sở thích và định hướng mới nhất.
                  </p>
                </div>
                <div className="mt-6 flex items-center gap-2 text-sm font-black text-slate-700 group-hover:text-sky-700">
                  <span>Bắt đầu làm bài mới</span>
                  <ArrowRight className="size-4 transition group-hover:translate-x-1.5" />
                </div>
              </button>
            </div>
          </div>
        </PageContainer>
      </section>
    )
  }

  return (
    <section className="relative overflow-x-clip py-2.5 sm:py-4">
      {/* Ambient Animated Liquid Glass Background Orbs */}
      <motion.div
        animate={{
          x: [0, 20, -10, 0],
          y: [0, -14, 10, 0],
          scale: [1, 1.05, 0.96, 1],
        }}
        transition={{ duration: 14, repeat: Infinity, ease: "easeInOut" }}
        className="pointer-events-none absolute left-1/4 top-10 h-64 w-64 rounded-full bg-sky-300/25 blur-3xl"
      />
      <motion.div
        animate={{
          x: [0, -24, 14, 0],
          y: [0, 18, -12, 0],
          scale: [1, 0.95, 1.06, 1],
        }}
        transition={{ duration: 16, repeat: Infinity, ease: "easeInOut" }}
        className="pointer-events-none absolute right-1/4 top-28 h-72 w-72 rounded-full bg-cyan-300/20 blur-3xl"
      />

      {/* Spacious Container: Default wide responsive stage aligned across monitors */}
      <PageContainer className="relative z-10 max-w-4xl xl:max-w-5xl">
        {/* Top Rows: Back Button row + History Switcher (in review) + Liquid Glass Step Bar row */}
        <div className="mb-3 flex flex-col gap-2.5">
          <div className="flex flex-wrap items-center justify-between gap-2.5">
            <button
              type="button"
              onClick={() => {
                if (hasCompletedAttempt) {
                  const targetId = editingAttemptId || activeHistoryId
                  if (isReviewMode && hasReviewChanges && targetId) {
                    selectHistoryAttempt(targetId)
                  }
                  setSaveEditError(null)
                  setIsReviewMode(false)
                  setSessionStarted(false)
                  setShowHistoryPicker(isReviewMode && history.length > 1)
                  window.scrollTo({ top: 0, behavior: "smooth" })
                } else {
                  navigate("/dashboard")
                }
              }}
              className="inline-flex shrink-0 items-center gap-2 rounded-2xl border border-white/90 bg-white/75 px-4 py-2.5 text-xs font-extrabold text-slate-700 shadow-xs backdrop-blur-md transition hover:bg-white hover:text-sky-700 hover:shadow-sm sm:text-sm"
            >
              <ArrowLeft className="size-4 text-sky-600" />
              <span>Quay lại</span>
            </button>

            {isReviewMode && history.length > 1 && (
              <div className="flex flex-wrap items-center gap-1.5 rounded-2xl border border-white/90 bg-white/70 px-2.5 py-1.5 shadow-xs backdrop-blur-xl">
                <span className="inline-flex items-center gap-1 px-1.5 text-xs font-bold text-slate-500">
                  <History className="size-3.5 text-sky-600" />
                  <span>Bài làm:</span>
                </span>
                {history.map((item, idx) => {
                  const attemptNumber = history.length - idx
                  const isCurrent =
                    item.id === (activeHistoryId || history[0]?.id)
                  const shortTime = formatAttemptDateTime(item.createdAt)
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => openHistoryAttemptForReview(item, true)}
                      title={shortTime || undefined}
                      className={`inline-flex items-center gap-1.5 rounded-xl px-3 py-1 text-xs font-extrabold transition cursor-pointer ${
                        isCurrent
                          ? "bg-sky-600 text-white shadow-xs"
                          : "bg-white/80 text-slate-600 hover:bg-white hover:text-sky-700"
                      }`}
                    >
                      <span>Lần {attemptNumber}</span>
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          {/* Top Liquid Glass Step Bar (separate full-width row) */}
          <div className="flex w-full min-w-0 flex-wrap items-center justify-between gap-2 rounded-2xl border border-white/85 bg-white/60 px-3.5 py-2 shadow-[inset_0_1px_1px_rgba(255,255,255,0.9),0_10px_28px_rgba(14,165,233,0.08)] backdrop-blur-2xl">
          {/* 3 Main Steps */}
          <div className="flex flex-wrap items-center gap-1.5">
            {[
              {
                id: 1,
                label: "1. Sở thích",
                done: completeness.riasecComplete,
                hint: `${completeness.riasecAnswered}/${completeness.riasecTotal}`,
              },
              {
                id: 2,
                label: "2. Tư duy",
                done: completeness.cognitiveComplete,
                hint: `${completeness.cognitiveAnswered}/${completeness.cognitiveTotal}`,
              },
              {
                id: 3,
                label: "3. Điểm số",
                done: completeness.scoresComplete,
                hint: completeness.hasInvalidScores
                  ? "Lỗi điểm"
                  : `${completeness.completeBlocks.length} khối`,
              },
            ].map((s) => {
              const active = step === s.id
              return (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => {
                    setStep(s.id)
                    update({ step: s.id })
                    window.scrollTo({ top: 0, behavior: "smooth" })
                  }}
                  className={`relative flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs sm:text-sm font-extrabold transition cursor-pointer ${
                    active
                      ? "bg-gradient-to-r from-sky-500 to-cyan-500 text-white shadow-[0_6px_16px_rgba(14,165,233,0.28)]"
                      : s.done
                        ? "border border-sky-200/80 bg-white/80 text-sky-700 hover:bg-white"
                        : "bg-white/45 text-slate-600 hover:bg-white/75"
                  }`}
                >
                  {s.done && !active && (
                    <Check className="size-3.5 text-sky-600" />
                  )}
                  <span>{s.label}</span>
                  {!s.done && (
                    <span
                      className={`rounded-md px-1.5 py-0.5 text-[10px] font-bold tabular-nums ${
                        active
                          ? "bg-white/20 text-white"
                          : "bg-slate-200/70 text-slate-600"
                      }`}
                    >
                      {s.hint}
                    </span>
                  )}
                </button>
              )
            })}
          </div>

          {/* Right Utilities: View Mode Switch + Reset */}
          <div className="flex items-center gap-1.5">
            {step === 1 && (
              <div className="flex items-center rounded-xl border border-white/80 bg-white/60 p-0.5 backdrop-blur-xl">
                <button
                  type="button"
                  onClick={() => setStep1Mode("swipe")}
                  className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-extrabold transition ${
                    step1Mode === "swipe"
                      ? "bg-sky-600 text-white shadow-sm"
                      : "text-slate-600 hover:text-sky-700"
                  }`}
                >
                  <Layers className="size-3.5" />
                  <span>Thẻ</span>
                </button>
                <button
                  type="button"
                  onClick={() => setStep1Mode("list")}
                  className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-extrabold transition ${
                    step1Mode === "list"
                      ? "bg-sky-600 text-white shadow-sm"
                      : "text-slate-600 hover:text-sky-700"
                  }`}
                >
                  <ListChecks className="size-3.5" />
                  <span>Danh sách</span>
                </button>
                <button
                  type="button"
                  onClick={() => setStep1Mode("radar")}
                  className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-extrabold transition ${
                    step1Mode === "radar"
                      ? "bg-sky-600 text-white shadow-sm"
                      : "text-slate-600 hover:text-sky-700"
                  }`}
                >
                  <Sliders className="size-3.5" />
                  <span>Radar</span>
                </button>
              </div>
            )}

            {step === 2 && (
              <div className="flex items-center rounded-xl border border-white/80 bg-white/60 p-0.5 backdrop-blur-xl">
                <button
                  type="button"
                  onClick={() => setStep2Mode("swipe")}
                  className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-extrabold transition ${
                    step2Mode === "swipe"
                      ? "bg-sky-600 text-white shadow-sm"
                      : "text-slate-600 hover:text-sky-700"
                  }`}
                >
                  <Layers className="size-3.5" />
                  <span>Thẻ</span>
                </button>
                <button
                  type="button"
                  onClick={() => setStep2Mode("list")}
                  className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-extrabold transition ${
                    step2Mode === "list"
                      ? "bg-sky-600 text-white shadow-sm"
                      : "text-slate-600 hover:text-sky-700"
                  }`}
                >
                  <ListChecks className="size-3.5" />
                  <span>Danh sách</span>
                </button>
              </div>
            )}

            {(totalRiasecAnswered > 0 || totalCognitiveAnswered > 0) && (
              <button
                type="button"
                onClick={resetAllAnswers}
                title="Làm lại"
                className="grid size-8 place-items-center rounded-xl border border-white/85 bg-white/60 text-slate-600 backdrop-blur-xl transition hover:border-sky-300 hover:bg-white hover:text-sky-700"
              >
                <RotateCcw className="size-3.5" />
              </button>
            )}
          </div>
          </div>
        </div>

        {loading && step < 3 && (
          <div className="mb-3 flex items-center justify-center gap-2 text-sky-700/70">
            <Loader2 className="size-4 animate-spin" />
          </div>
        )}

        {isReviewMode && (hasReviewChanges || saveEditError) && (
          <div
            role="status"
            className={`mb-3 flex flex-wrap items-center justify-between gap-2.5 rounded-2xl border px-4 py-2.5 text-xs sm:text-sm backdrop-blur-md ${
              saveEditError
                ? "border-rose-200 bg-rose-50/95 text-rose-900"
                : "border-sky-200 bg-sky-50/95 text-sky-900"
            }`}
          >
            <span className="font-semibold">
              {saveEditError
                ? saveEditError
                : "Hồ sơ đã lưu có thay đổi. Bấm lưu để cập nhật CSDL, tính lại đề xuất và làm mới giải thích AI."}
            </span>
            <Button
              icon={Check}
              className="px-3.5 py-1.5 text-xs font-extrabold"
              disabled={submitting || !completeness.isComplete}
              onClick={() => handleSaveReviewChanges("dashboard")}
            >
              {submitting ? "Đang cập nhật…" : "Lưu thay đổi & Phân tích lại"}
            </Button>
          </div>
        )}

        {/* ==================== STEP 1: VERTICAL QUESTION CARD + ILLUSTRATION + 5 EMOTICONS ==================== */}
        {step === 1 && (
          <div className="space-y-2.5 sm:space-y-3">
            {step1Mode === "swipe" && (
              <>
                {/* Compact Progress Track */}
                <div className="mx-auto flex w-full items-center gap-3 px-1 transition-all duration-200">
                  <div className="h-2.5 flex-1 overflow-hidden rounded-full border border-white/80 bg-white/55 p-0.5 backdrop-blur-md">
                    <motion.div
                      animate={{
                        width: `${Math.round(
                          (totalRiasecAnswered / 30) * 100
                        )}%`,
                      }}
                      transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
                      className="h-full rounded-full bg-gradient-to-r from-sky-400 via-sky-500 to-cyan-500"
                    />
                  </div>
                  <span className="text-xs sm:text-sm font-black tabular-nums text-sky-900">
                    {totalRiasecAnswered}/30
                  </span>
                </div>

                {/* Vertical Card Stage: Generous Responsive Stage */}
                <div className="relative mx-auto flex w-full items-center justify-center gap-2.5 sm:gap-4 transition-all duration-200">
                  {/* Left Arrow Button (Previous Question) */}
                  <motion.button
                    type="button"
                    whileHover={{ scale: 1.08 }}
                    whileTap={{ scale: 0.92 }}
                    disabled={cardIndex === 0}
                    onClick={goToPrevCard}
                    aria-label="Câu trước"
                    className="hidden sm:grid size-11 shrink-0 place-items-center rounded-full border border-white/90 bg-white/75 text-sky-700 shadow-[inset_0_1px_1px_rgba(255,255,255,0.9),0_6px_18px_rgba(14,165,233,0.12)] backdrop-blur-2xl transition hover:bg-white hover:scale-105 disabled:opacity-30 cursor-pointer"
                  >
                    <ChevronLeft className="size-5" />
                  </motion.button>

                  {/* Unified Vertical Bento Card (Illustration + Question + 5 Emoticon Ratings) */}
                  <div className="relative w-full max-w-3xl xl:max-w-4xl">
                    {/* Subtle Stacked Depth Card Behind */}
                    <div className="pointer-events-none absolute inset-x-4 -bottom-2 top-4 rounded-3xl border border-white/60 bg-white/35 backdrop-blur-xl" />

                    <AnimatePresence mode="wait" custom={slideDirection}>
                      <VerticalQuestionCard
                        key={currentCard.code}
                        item={currentCard}
                        index={cardIndex}
                        total={ONET_MINI_IP_ITEMS.length}
                        selectedValue={currentCardValue}
                        direction={slideDirection}
                        onRate={rateCurrentCard}
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
                    className="hidden sm:grid size-11 shrink-0 place-items-center rounded-full border border-white/90 bg-white/75 text-sky-700 shadow-[inset_0_1px_1px_rgba(255,255,255,0.9),0_6px_18px_rgba(14,165,233,0.12)] backdrop-blur-2xl transition hover:bg-white hover:scale-105 disabled:opacity-30 cursor-pointer"
                  >
                    <ChevronRight className="size-5" />
                  </motion.button>
                </div>
              </>
            )}

            {/* Read-only summary derived from questionnaire answers. */}
            {step1Mode === "radar" && (
              <div className="grid gap-4 rounded-3xl border border-white/90 bg-white/65 p-5 shadow-[inset_0_1px_1px_rgba(255,255,255,0.95),0_18px_44px_rgba(14,165,233,0.12)] backdrop-blur-2xl md:grid-cols-[1.2fr_0.8fr]">
                <div className="space-y-2.5">
                  <p className="mb-3 text-sm text-slate-600">Biểu đồ tự cập nhật theo câu trả lời trắc nghiệm. Chỉnh câu trả lời ở chế độ Thẻ hoặc Danh sách.</p>
                  {RIASEC_ORDER.map((dim) => {
                    const meta = RIASEC_META[dim]
                    const avg = riasecGroupAvg[dim]
                    return (
                      <div
                        key={dim}
                        className="flex items-center justify-between gap-2.5 rounded-2xl border border-white/80 bg-white/75 px-3.5 py-2.5 backdrop-blur-xl"
                      >
                        <span className="text-sm sm:text-base font-extrabold text-slate-900">
                          {meta.label}
                        </span>
                        <div className="shrink-0 text-right">
                          <span className="text-sm font-semibold tabular-nums text-sky-800">
                            {riasecGroupCounts[dim] ? `${avg.toFixed(1)} / 5` : "Chưa có dữ liệu"}
                          </span>
                          <p className="text-xs text-slate-500">{riasecGroupCounts[dim]}/5 câu</p>
                        </div>
                      </div>
                    )
                  })}
                </div>

                <div className="flex flex-col items-center justify-center rounded-2xl border border-white/80 bg-sky-50/45 p-4 backdrop-blur-xl">
                  <LiveRiasecHexagon scores={riasecGroupPct} />
                </div>
              </div>
            )}

            {/* MODE C: FULL 30-QUESTION LIST VIEW */}
            {step1Mode === "list" && (
              <RiasecQuestionsListView
                items={ONET_MINI_IP_ITEMS}
                answers={assessment.answers}
                onRate={handleRateByCode}
              />
            )}
          </div>
        )}

        {/* ==================== STEP 2: RELATABLE COGNITIVE SCENARIO CARDS ==================== */}
        {step === 2 && currentCog && (
          <div className="space-y-2.5 sm:space-y-3">
            {step2Mode === "swipe" && (
              <>
                {/* Compact Step 2 Progress Track */}
                <div className="mx-auto flex w-full items-center gap-3 px-1 transition-all duration-200">
                  <div className="h-2.5 flex-1 overflow-hidden rounded-full border border-white/80 bg-white/55 p-0.5 backdrop-blur-md">
                    <motion.div
                      animate={{
                        width: `${Math.round(
                          (totalCognitiveAnswered /
                            Math.max(1, displayedCognitiveQuestions.length)) *
                            100
                        )}%`,
                      }}
                      transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
                      className="h-full rounded-full bg-gradient-to-r from-sky-400 via-sky-500 to-cyan-500"
                    />
                  </div>
                  <span className="text-xs font-black tabular-nums text-sky-900 sm:text-sm">
                    {totalCognitiveAnswered}/{displayedCognitiveQuestions.length}
                  </span>
                </div>

                <div className="relative mx-auto flex w-full items-center justify-center gap-2.5 sm:gap-4 transition-all duration-200">
                  <motion.button
                    type="button"
                    whileHover={{ scale: 1.08 }}
                    whileTap={{ scale: 0.92 }}
                    disabled={safeCogIndex === 0}
                    onClick={goToPrevCog}
                    aria-label="Câu trước"
                    className="hidden sm:grid size-11 shrink-0 place-items-center rounded-full border border-white/90 bg-white/75 text-sky-700 shadow-md backdrop-blur-2xl transition hover:bg-white hover:scale-105 disabled:opacity-30 cursor-pointer"
                  >
                    <ChevronLeft className="size-5" />
                  </motion.button>

                  <AnimatePresence mode="wait" custom={cogDirection}>
                    <motion.div
                      key={currentCog.code}
                      custom={cogDirection}
                      initial={{ opacity: 0, x: cogDirection * 48, scale: 0.98 }}
                      animate={{ opacity: 1, x: 0, scale: 1 }}
                      exit={{ opacity: 0, x: cogDirection * -48, scale: 0.98 }}
                      transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
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
                      className="mx-auto w-full max-w-3xl xl:max-w-4xl rounded-3xl border border-white/90 bg-white/75 p-4 sm:p-6 lg:p-7 shadow-[inset_0_1px_1px_rgba(255,255,255,0.95),0_18px_44px_rgba(14,165,233,0.12)] backdrop-blur-2xl"
                    >
                      {/* Top Header Pill + Mobile Nav */}
                      <div className="mb-3.5 sm:mb-4 flex items-center justify-between gap-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="rounded-full border border-sky-200/80 bg-white/90 px-3 py-1 text-xs font-black tabular-nums text-sky-800 shadow-2xs">
                            {safeCogIndex + 1} / {displayedCognitiveQuestions.length}
                          </span>
                        </div>

                        <div className="flex items-center gap-1 sm:hidden">
                          <button
                            type="button"
                            disabled={safeCogIndex === 0}
                            onClick={goToPrevCog}
                            aria-label="Câu trước"
                            className="grid size-9 place-items-center rounded-full border border-white/80 bg-white/80 text-sky-700 disabled:opacity-30"
                          >
                            <ChevronLeft className="size-4" />
                          </button>
                          <button
                            type="button"
                            disabled={safeCogIndex >= displayedCognitiveQuestions.length - 1}
                            onClick={goToNextCog}
                            aria-label="Câu tiếp theo"
                            className="grid size-9 place-items-center rounded-full border border-white/80 bg-white/80 text-sky-700 disabled:opacity-30"
                          >
                            <ChevronRight className="size-4" />
                          </button>
                        </div>
                      </div>

                      {/* Relatable Scenario Question */}
                      <h2 className="mb-4 sm:mb-5 text-base sm:text-lg lg:text-xl font-bold leading-snug text-slate-900">
                        {currentCog.subtitle}
                      </h2>

                      {/* Option Cards (compact by default; toggle button reveals details) */}
                      <div
                        className={`grid grid-cols-1 gap-2.5 sm:gap-3 ${
                          currentCog.options.length === 3 ? "sm:grid-cols-3" : "sm:grid-cols-2"
                        }`}
                      >
                        {currentCog.options.map((opt) => {
                          const isSelected =
                            String(currentCogValue) === opt.option_key
                          const expandKey = `${currentCog.code}:${opt.option_key}`
                          const isExpanded = Boolean(expandedCogOptions[expandKey])
                          return (
                            <motion.div
                              key={opt.option_key}
                              role="button"
                              tabIndex={0}
                              data-testid={`cognitive-${currentCog.code}-${opt.option_key}`}
                              whileHover={{ y: -2, scale: 1.01 }}
                              whileTap={{ scale: 0.98 }}
                              onClick={(e) => {
                                e.stopPropagation()
                                handleSelectCognitive(opt.option_key)
                              }}
                              onKeyDown={(e) => {
                                if (e.key === "Enter" || e.key === " ") {
                                  e.preventDefault()
                                  handleSelectCognitive(opt.option_key)
                                }
                              }}
                              className={`group relative flex min-h-[56px] items-start gap-3.5 rounded-2xl border p-4 sm:p-4.5 text-left backdrop-blur-xl transition-all cursor-pointer active:scale-[0.98] ${
                                isSelected
                                  ? "border-sky-500 bg-sky-50/90 ring-2 ring-sky-500/25 shadow-sm"
                                  : "border-slate-200/90 bg-white/90 hover:border-sky-300 hover:bg-sky-50/40"
                              }`}
                            >
                              <span
                                className={`flex size-10 shrink-0 items-center justify-center rounded-xl transition-colors ${
                                  isSelected
                                    ? "bg-sky-500 text-white shadow-xs"
                                    : "bg-slate-100 text-slate-600 group-hover:bg-sky-100 group-hover:text-sky-600"
                                }`}
                              >
                                <CognitiveOptionIcon
                                  name={opt.icon}
                                  className="size-5 stroke-[2]"
                                />
                              </span>

                              <div className="min-w-0 flex-1">
                                <div className="flex items-center justify-between gap-2">
                                  <h3 className="text-sm sm:text-base font-bold leading-snug text-slate-800">
                                    {opt.label}
                                  </h3>
                                  <div className="flex shrink-0 items-center gap-1.5">
                                    {isSelected && (
                                      <span className="inline-flex items-center gap-1 rounded-full bg-sky-600 px-2 py-0.5 text-[10px] font-black text-white shadow-xs">
                                        <Check className="size-3 stroke-[2.5]" />
                                        <span>Đã chọn</span>
                                      </span>
                                    )}
                                    {opt.description && (
                                      <button
                                        type="button"
                                        aria-expanded={isExpanded}
                                        aria-label={isExpanded ? "Ẩn chi tiết đáp án" : "Xem chi tiết đáp án"}
                                        title={isExpanded ? "Ẩn chi tiết" : "Xem chi tiết"}
                                        onClick={(e) => {
                                          e.stopPropagation()
                                          setExpandedCogOptions((prev) => ({
                                            ...prev,
                                            [expandKey]: !prev[expandKey],
                                          }))
                                        }}
                                        className={`grid size-7 place-items-center rounded-full border transition cursor-pointer ${
                                          isExpanded
                                            ? "border-sky-300 bg-sky-100 text-sky-700"
                                            : "border-slate-200 bg-white text-slate-500 hover:border-sky-300 hover:bg-sky-50 hover:text-sky-700"
                                        }`}
                                      >
                                        <ChevronDown
                                          className={`size-4 transition-transform duration-150 ${
                                            isExpanded ? "rotate-180" : ""
                                          }`}
                                        />
                                      </button>
                                    )}
                                  </div>
                                </div>
                                {isExpanded && opt.description && (
                                  <p className="mt-2 text-xs sm:text-sm leading-relaxed text-slate-600">
                                    {opt.description}
                                  </p>
                                )}
                              </div>
                            </motion.div>
                          )
                        })}
                      </div>
                    </motion.div>
                  </AnimatePresence>

                  <motion.button
                    type="button"
                    whileHover={{ scale: 1.08 }}
                    whileTap={{ scale: 0.92 }}
                    disabled={safeCogIndex >= displayedCognitiveQuestions.length - 1}
                    onClick={goToNextCog}
                    aria-label="Câu tiếp theo"
                    className="hidden sm:grid size-11 shrink-0 place-items-center rounded-full border border-white/90 bg-white/75 text-sky-700 shadow-md backdrop-blur-2xl transition hover:bg-white hover:scale-105 disabled:opacity-30 cursor-pointer"
                  >
                    <ChevronRight className="size-5" />
                  </motion.button>
                </div>
              </>
            )}

            {step2Mode === "list" && (
              <CognitiveQuestionsListView
                questions={displayedCognitiveQuestions}
                answers={assessment.cognitive}
                answeredCount={totalCognitiveAnswered}
                onSelect={handleSelectCognitiveByIndex}
              />
            )}
          </div>
        )}

        {/* ==================== STEP 3: ACADEMIC SCORES (10 HIGH SCHOOL SUBJECTS) ==================== */}
        {step === 3 && (
          <div className="space-y-3">
            <div className="rounded-3xl border border-white/90 bg-white/65 p-5 sm:p-6 shadow-[inset_0_1px_1px_rgba(255,255,255,0.95),0_18px_44px_rgba(14,165,233,0.12)] backdrop-blur-2xl">
              <AcademicInputForm
                scores={scores}
                onChange={(subject, value) => {
                  const next = { ...scores }
                  if (value === undefined) delete next[subject]
                  else next[subject] = value
                  setScores(next)
                  const persistedScores: SubjectGrade[] = Object.entries(next)
                    .filter(([, score]) => Number.isFinite(score) && score >= 0 && score <= 10)
                    .map(([subj, score]) => ({ subject: subj, score, zScore: null }))
                  update({ scores: persistedScores })
                }}
              />
            </div>

            {!completeness.isComplete && (
              <div
                role="status"
                className="rounded-2xl border border-amber-200 bg-amber-50/95 p-4 sm:p-5 text-amber-900 shadow-xs backdrop-blur-md"
              >
                <div className="flex items-start gap-3">
                  <AlertTriangle className="mt-0.5 size-5 shrink-0 text-amber-600" />
                  <div className="min-w-0 flex-1">
                    <h3 className="text-sm sm:text-base font-extrabold text-amber-950">
                      Chưa đủ dữ liệu để phân tích ngành phù hợp
                    </h3>
                    <p className="mt-1 text-xs sm:text-sm font-medium text-amber-800">
                      Bạn vẫn có thể xem tự do cả 3 phần trắc nghiệm, nhưng cần hoàn thành đủ các yêu cầu sau trước khi hệ thống phân tích ngành học:
                    </p>
                    <ul className="mt-3 space-y-2">
                      {completeness.missingItems.map((item) => (
                        <li
                          key={item.step}
                          className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber-200/80 bg-white/80 px-3.5 py-2 text-xs sm:text-sm"
                        >
                          <div className="min-w-0 flex-1">
                            <span className="font-extrabold text-slate-900">{item.label}:</span>{" "}
                            <span className="font-medium text-slate-700">{item.detail}</span>
                          </div>
                          {item.step !== 3 && (
                            <button
                              type="button"
                              onClick={() => {
                                setStep(item.step)
                                update({ step: item.step })
                                window.scrollTo({ top: 0, behavior: "smooth" })
                              }}
                              className="inline-flex shrink-0 items-center gap-1 rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-extrabold text-white transition hover:bg-amber-700 cursor-pointer"
                            >
                              <span>Làm phần này</span>
                              <ArrowRight className="size-3.5" />
                            </button>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Clean Bottom Action Bar */}
        <div className="mt-3 flex items-center justify-between gap-3 sm:mt-4">
          <Button
            variant="ghost"
            icon={ArrowLeft}
            className="text-sm sm:text-base px-4 py-2.5"
            disabled={step === 1 && (step1Mode === "radar" || cardIndex === 0)}
            onClick={() => {
              if (step === 1 && step1Mode === "swipe" && cardIndex > 0) {
                goToPrevCard()
                return
              }
              if (step === 2 && step2Mode === "swipe" && cogIndex > 0) {
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
                className="text-sm sm:text-base px-5 py-2.5"
                onClick={() => {
                  update({ step: 2 })
                  setStep(2)
                  window.scrollTo({ top: 0, behavior: "smooth" })
                }}
              >
                {isReviewMode
                  ? "Xem tiếp: Tư duy nhận thức"
                  : completeness.riasecComplete
                    ? "Tiếp tục"
                    : "Xem phần Tư duy"}
              </Button>
            )}

            {step === 2 && (
              <Button
                icon={ArrowRight}
                className="text-sm sm:text-base px-5 py-2.5"
                onClick={() => {
                  setStep(3)
                  update({ step: 3 })
                  window.scrollTo({ top: 0, behavior: "smooth" })
                }}
              >
                {isReviewMode
                  ? "Xem tiếp: Điểm số học tập"
                  : completeness.cognitiveComplete
                    ? "Tiếp tục"
                    : "Xem phần Điểm số"}
              </Button>
            )}

            {step === 3 && (
              <div className="flex flex-wrap items-center justify-end gap-2.5 sm:gap-3">
                {isReviewMode ? (
                  <>
                    <Button
                      variant="secondary"
                      className="border-slate-300 px-4 py-2.5 text-xs font-bold text-slate-700 hover:bg-slate-100 sm:text-sm"
                      disabled={submitting}
                      onClick={() => {
                        const targetId = editingAttemptId || activeHistoryId
                        if (hasReviewChanges && targetId) {
                          selectHistoryAttempt(targetId)
                        }
                        setSaveEditError(null)
                        setSessionStarted(false)
                      }}
                    >
                      {hasReviewChanges ? "Hủy thay đổi" : "Đóng xem lại"}
                    </Button>
                    {hasReviewChanges ? (
                      <Button
                        icon={Check}
                        className="bg-sky-600 px-5 py-2.5 text-xs font-black text-white shadow-md hover:bg-sky-700 sm:text-sm"
                        disabled={submitting || !completeness.isComplete}
                        title={
                          !completeness.isComplete
                            ? "Cần hoàn thành đủ 3 phần trước khi lưu thay đổi"
                            : undefined
                        }
                        onClick={() => handleSaveReviewChanges("dashboard")}
                      >
                        {submitting ? "Đang cập nhật…" : "Lưu thay đổi & Phân tích lại"}
                      </Button>
                    ) : (
                      <Button
                        icon={LayoutDashboard}
                        className="bg-sky-600 px-5 py-2.5 text-xs font-black text-white shadow-md hover:bg-sky-700 sm:text-sm"
                        onClick={() => navigate("/dashboard")}
                      >
                        Mở Dashboard kết quả
                      </Button>
                    )}
                  </>
                ) : (
                  <Button
                    icon={Check}
                    className="px-5 py-2.5 text-xs font-extrabold sm:text-sm"
                    disabled={submitting || !completeness.isComplete}
                    title={
                      !completeness.isComplete
                        ? "Cần hoàn thành đủ 3 phần trắc nghiệm trước khi phân tích ngành"
                        : undefined
                    }
                    onClick={() => handleCompleteAssessment(false)}
                  >
                    {submitting ? "Đang đồng bộ…" : "Hoàn tất & Phân tích ngành"}
                  </Button>
                )}
              </div>
            )}
          </div>
        </div>
      </PageContainer>
    </section>
  )
}

function RiasecQuestionsListView({
  items,
  answers,
  onRate,
}: {
  items: OnetMiniIpItem[]
  answers: Record<string, number>
  onRate: (code: string, value: number) => void
}) {
  const [filterDim, setFilterDim] = useState<string>("ALL")

  const filteredItems = useMemo(() => {
    if (filterDim === "ALL") return items
    return items.filter((item) => item.dimension === filterDim)
  }, [items, filterDim])

  return (
    <div className="space-y-4 rounded-3xl border border-white/90 bg-white/70 p-5 sm:p-7 shadow-[inset_0_1px_1px_rgba(255,255,255,0.95),0_18px_44px_rgba(14,165,233,0.12)] backdrop-blur-2xl">
      {/* Dimension Filter Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            onClick={() => setFilterDim("ALL")}
            className={`rounded-xl px-3 py-1.5 text-xs font-black transition ${
              filterDim === "ALL"
                ? "bg-sky-600 text-white shadow-xs"
                : "bg-white/80 text-slate-600 hover:bg-white hover:text-sky-700"
            }`}
          >
            Tất cả (30 câu)
          </button>
          {RIASEC_ORDER.map((dim) => {
            const meta = RIASEC_META[dim]
            const active = filterDim === dim
            return (
              <button
                key={dim}
                type="button"
                onClick={() => setFilterDim(dim)}
                className={`rounded-xl px-3 py-1.5 text-xs font-extrabold transition ${
                  active
                    ? "bg-sky-600 text-white shadow-xs"
                    : "bg-white/80 text-slate-600 hover:bg-white hover:text-sky-700"
                }`}
              >
                {meta.label}
              </button>
            )
          })}
        </div>
        <span className="text-xs font-bold text-slate-500">
          Đang hiển thị {filteredItems.length} câu hỏi
        </span>
      </div>

      {/* List of 30 Questions */}
      <div className="space-y-3">
        {filteredItems.map((item) => {
          const canonicalIdx = CANONICAL_30_CODES.indexOf(item.code)
          const chosenVal = answers[item.code] ?? answers[`1-${canonicalIdx}`]

          return (
            <div
              key={item.code}
              data-testid={`riasec-${item.code}`}
              className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3.5 rounded-2xl border p-4 backdrop-blur-md transition ${
                chosenVal
                  ? "border-sky-200/90 bg-white/95 shadow-2xs"
                  : "border-slate-200/70 bg-white/60"
              }`}
            >
              <div className="flex items-start gap-3 min-w-0 flex-1">
                <span className="grid size-8 shrink-0 place-items-center rounded-xl bg-sky-100 text-xs font-black text-sky-800">
                  {item.code}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-black text-slate-600 uppercase">
                      {RIASEC_META[item.dimension]?.tag}
                    </span>
                    {!chosenVal && (
                      <span className="text-[11px] font-bold text-amber-600">
                        Chưa trả lời
                      </span>
                    )}
                  </div>
                  <h4 className="mt-1 text-sm sm:text-base font-extrabold text-slate-900 leading-snug">
                    {item.titleVi}
                  </h4>
                </div>
              </div>

              {/* 5-Level Reaction Emoticon Pills with 48px min-h tap targets */}
              <div className="flex items-center justify-between sm:justify-end gap-1.5 sm:gap-2 shrink-0 pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-100">
                {ONET_REACTION_SCALE.map((s) => {
                  const isPicked = chosenVal === s.value
                  return (
                    <button
                      key={s.value}
                      type="button"
                      onClick={() => onRate(item.code, s.value)}
                      title={`${s.label} (${s.value}/5)`}
                      className={`flex min-h-[48px] min-w-[48px] flex-col items-center justify-center rounded-xl px-2.5 py-1.5 text-center transition-all duration-150 cursor-pointer active:scale-95 ${
                        isPicked
                          ? "bg-sky-500 text-white shadow-xs ring-2 ring-sky-500/25 scale-105"
                          : "bg-slate-100/90 text-slate-700 hover:bg-sky-50 hover:text-sky-800"
                      }`}
                    >
                      <span className="text-xl sm:text-2xl leading-none">{s.emoji}</span>
                      <span className="text-[10px] font-bold mt-0.5">
                        {s.label}
                      </span>
                    </button>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function CognitiveQuestionsListView({
  questions,
  answers,
  answeredCount,
  onSelect,
}: {
  questions: CognitiveQuestionItem[]
  answers: Record<string, string | number>
  answeredCount: number
  onSelect: (code: string, index: number, optionKey: string) => void
}) {
  const [expandedOptions, setExpandedOptions] = useState<Record<string, boolean>>({})

  return (
    <div className="space-y-4 rounded-3xl border border-white/90 bg-white/70 p-5 sm:p-7 shadow-[inset_0_1px_1px_rgba(255,255,255,0.95),0_18px_44px_rgba(14,165,233,0.12)] backdrop-blur-2xl">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3.5">
        <span className="text-xs sm:text-sm font-black text-slate-800">
          Tất cả câu hỏi tư duy ({questions.length} câu)
        </span>
        <span className="text-xs font-bold tabular-nums text-sky-800">
          {answeredCount}/{questions.length} đã trả lời
        </span>
      </div>

      <div className="space-y-4">
        {questions.map((q, idx) => {
          const picked =
            answers[q.code] ??
            (q.dimension ? answers[q.dimension] : undefined) ??
            answers[`2-${idx}`]
          const hasAnswer = picked !== undefined && picked !== null && String(picked).trim() !== ""

          return (
            <div
              key={q.code || idx}
              data-testid={`cognitive-list-${q.code}`}
              className={`rounded-2xl border p-4 sm:p-5 backdrop-blur-md transition ${
                hasAnswer
                  ? "border-sky-200/90 bg-white/95 shadow-2xs"
                  : "border-slate-200/80 bg-white/75"
              }`}
            >
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="rounded-xl bg-sky-100 px-2.5 py-1 text-xs font-black tabular-nums text-sky-800">
                  Câu {idx + 1}
                </span>
                {!hasAnswer && (
                  <span className="text-[11px] font-bold text-amber-600">
                    Chưa trả lời
                  </span>
                )}
              </div>

              <h3 className="mb-3.5 text-sm sm:text-base font-extrabold leading-snug text-slate-900">
                {q.subtitle}
              </h3>

              <div
                className={`grid grid-cols-1 gap-2.5 ${
                  q.options.length === 3 ? "sm:grid-cols-3" : "sm:grid-cols-2"
                }`}
              >
                {q.options.map((opt) => {
                  const isSelected = String(picked) === opt.option_key
                  const expandKey = `${q.code}:${opt.option_key}`
                  const isExpanded = Boolean(expandedOptions[expandKey])
                  return (
                    <div
                      key={opt.option_key}
                      role="button"
                      tabIndex={0}
                      data-testid={`cognitive-${q.code}-${opt.option_key}`}
                      onClick={() => onSelect(q.code, idx, opt.option_key)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault()
                          onSelect(q.code, idx, opt.option_key)
                        }
                      }}
                      className={`group flex items-start gap-3 rounded-2xl border p-3.5 text-left transition-all cursor-pointer active:scale-[0.99] ${
                        isSelected
                          ? "border-sky-500 bg-sky-50/90 ring-2 ring-sky-500/25 shadow-xs"
                          : "border-slate-200/90 bg-white/90 hover:border-sky-300 hover:bg-sky-50/40"
                      }`}
                    >
                      <span
                        className={`flex size-9 shrink-0 items-center justify-center rounded-xl transition-colors ${
                          isSelected
                            ? "bg-sky-500 text-white shadow-xs"
                            : "bg-slate-100 text-slate-600 group-hover:bg-sky-100 group-hover:text-sky-600"
                        }`}
                      >
                        <CognitiveOptionIcon
                          name={opt.icon}
                          className="size-4.5 stroke-[2]"
                        />
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs sm:text-sm font-bold leading-snug text-slate-800">
                            {opt.label}
                          </span>
                          <div className="flex shrink-0 items-center gap-1.5">
                            {isSelected && (
                              <span className="inline-flex items-center gap-1 rounded-full bg-sky-600 px-2 py-0.5 text-[10px] font-black text-white">
                                <Check className="size-3 stroke-[2.5]" />
                                <span>Đã chọn</span>
                              </span>
                            )}
                            {opt.description && (
                              <button
                                type="button"
                                aria-expanded={isExpanded}
                                aria-label={isExpanded ? "Ẩn chi tiết đáp án" : "Xem chi tiết đáp án"}
                                title={isExpanded ? "Ẩn chi tiết" : "Xem chi tiết"}
                                onClick={(e) => {
                                  e.stopPropagation()
                                  setExpandedOptions((prev) => ({
                                    ...prev,
                                    [expandKey]: !prev[expandKey],
                                  }))
                                }}
                                className={`grid size-6.5 place-items-center rounded-full border transition cursor-pointer ${
                                  isExpanded
                                    ? "border-sky-300 bg-sky-100 text-sky-700"
                                    : "border-slate-200 bg-white text-slate-500 hover:border-sky-300 hover:bg-sky-50 hover:text-sky-700"
                                }`}
                              >
                                <ChevronDown
                                  className={`size-3.5 transition-transform duration-150 ${
                                    isExpanded ? "rotate-180" : ""
                                  }`}
                                />
                              </button>
                            )}
                          </div>
                        </div>
                        {isExpanded && opt.description && (
                          <p className="mt-1.5 text-xs leading-relaxed text-slate-600">
                            {opt.description}
                          </p>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function formatAttemptDateTime(iso?: string): string {
  if (!iso) return ""
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ""
  return d.toLocaleString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  })
}

function VerticalQuestionCard({
  item,
  index,
  total,
  selectedValue,
  direction,
  onRate,
  onNext,
  onPrev,
}: {
  item: OnetMiniIpItem
  index: number
  total: number
  selectedValue?: number
  direction: number
  onRate: (value: number) => void
  onNext: () => void
  onPrev: () => void
}) {
  const x = useMotionValue(0)
  const rotate = useTransform(x, [-200, 200], [-4, 4])
  const scaleDrag = useTransform(x, [-200, 0, 200], [0.98, 1, 0.98])

  return (
    <motion.div
      custom={direction}
      style={{ x, rotate, scale: scaleDrag }}
      drag="x"
      dragConstraints={{ left: 0, right: 0 }}
      dragElastic={0.38}
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
        x: direction >= 0 ? 56 : -56,
        scale: 0.96,
        filter: "blur(3px)",
      }}
      animate={{
        opacity: 1,
        x: 0,
        scale: 1,
        filter: "blur(0px)",
      }}
      exit={{
        opacity: 0,
        x: direction >= 0 ? -56 : 56,
        scale: 0.96,
        filter: "blur(3px)",
      }}
      transition={{
        duration: 0.25,
        ease: [0.22, 1, 0.36, 1],
      }}
      className="relative flex flex-col cursor-grab active:cursor-grabbing select-none overflow-hidden rounded-3xl border border-white/90 bg-white/75 p-4 sm:p-6 shadow-[inset_0_1px_1px_rgba(255,255,255,0.95),0_20px_48px_rgba(14,165,233,0.14)] backdrop-blur-2xl"
    >
      {/* Specular Top Reflection */}
      <div className="pointer-events-none absolute inset-x-8 top-0 h-px bg-gradient-to-r from-transparent via-white to-transparent" />

      {/* 1. Visual Illustration Frame for the Question with Responsive Aspect Ratio */}
      <QuestionIllustrationFrame item={item} index={index} total={total} />

      {/* 2. Question Content (Balanced Typography & Generous Spacing) */}
      <div className="my-2.5 sm:my-4 text-center px-1">
        <h2 className="text-lg sm:text-xl lg:text-2xl font-black tracking-tight text-slate-900 leading-snug">
          {item.titleVi}
        </h2>
      </div>

      {/* 3. 5-Level Rating Emoticons with 48px+ Comfortable Tap Targets */}
      <div className="border-t border-sky-100/80 pt-3">
        <div className="grid grid-cols-5 gap-2 sm:gap-2.5">
        {ONET_REACTION_SCALE.map((btn) => {
          const active = selectedValue === btn.value
          return (
            <motion.button
              key={btn.value}
              type="button"
              whileHover={{ y: -2, scale: 1.05 }}
              whileTap={{ scale: 0.94 }}
              transition={{ duration: 0.16, ease: [0.22, 1, 0.36, 1] }}
              onClick={(e) => {
                e.stopPropagation()
                onRate(btn.value)
              }}
              className={`flex min-h-[48px] sm:min-h-[56px] flex-col items-center justify-center rounded-2xl border px-1.5 py-2.5 text-center transition-all duration-150 cursor-pointer sm:px-2 sm:py-3 ${
                active
                  ? "border-sky-400 bg-gradient-to-b from-sky-500 to-cyan-500 text-white shadow-[0_8px_20px_rgba(14,165,233,0.3)] scale-[1.03]"
                  : "border-white/90 bg-white/80 text-slate-700 shadow-xs hover:border-sky-300 hover:bg-white active:scale-95"
              }`}
            >
              <span className="text-xl sm:text-2xl leading-none">
                {btn.emoji}
              </span>
              <span className="mt-1 text-xs sm:text-sm font-extrabold tracking-tight leading-tight">
                {btn.label}
              </span>
            </motion.button>
          )
        })}
        </div>
      </div>
    </motion.div>
  )
}
