import { AnimatePresence, motion } from "framer-motion"
import {
  ArrowLeft,
  BookOpen,
  Check,
  ChevronDown,
  ChevronRight,
  Clock3,
  Compass,
  GraduationCap,
  Layers,
  Loader2,
  Save,
  Sparkles,
  Target,
  X,
} from "lucide-react"
import { useEffect, useMemo, useState, useRef } from "react"
import Markdown from "react-markdown"
import { Link, useSearchParams } from "react-router"
import remarkGfm from "remark-gfm"
import { Badge } from "../components/common/Badge"
import { Button } from "../components/common/Button"
import { PageContainer } from "../components/layout/PageContainer"
import { RoadmapFlow } from "../components/visualization/RoadmapFlow"
import { useRoadmap } from "../hooks/useRoadmap"
import { ApiError, requestJSON } from "../services/api"
import { scheduleToWeeks } from "../utils/roadmapSchedule"
import type { GuidancePersonalization, SavedRoadmapProgress, RoadmapWeek } from "../types/roadmap"

const availableMajors = [
  { code: "7480101", name: "Khoa học máy tính" },
  { code: "7480103", name: "Kỹ thuật phần mềm" },
  { code: "7480107", name: "Trí tuệ nhân tạo" },
  { code: "7480201", name: "Công nghệ thông tin" },
  { code: "7460108", name: "Khoa học dữ liệu" },
  { code: "7340115", name: "Marketing" },
  { code: "7340101", name: "Quản trị kinh doanh" },
  { code: "7520216", name: "Kỹ thuật điều khiển và tự động hóa" },
]

function getTaskResourceChip(task: string): { label: string; tone: string } {
  const lower = task.toLowerCase()
  if (
    lower.includes("leetcode") ||
    lower.includes("hackerrank") ||
    lower.includes("bài tập") ||
    lower.includes("thực hành")
  ) {
    return {
      label: "Thực hành",
      tone: "border-amber-200/80 bg-amber-50 text-amber-700",
    }
  }
  if (
    lower.includes("dự án") ||
    lower.includes("project") ||
    lower.includes("mini-project") ||
    lower.includes("sản phẩm")
  ) {
    return {
      label: "Dự án",
      tone: "border-indigo-200/80 bg-indigo-50 text-indigo-700",
    }
  }
  if (
    lower.includes("video") ||
    lower.includes("youtube") ||
    lower.includes("coursera") ||
    lower.includes("khóa học")
  ) {
    return {
      label: "Khóa học",
      tone: "border-purple-200/80 bg-purple-50 text-purple-700",
    }
  }
  if (
    lower.includes("tài liệu") ||
    lower.includes("đọc") ||
    lower.includes("sách") ||
    lower.includes("nền tảng")
  ) {
    return {
      label: "Tài liệu",
      tone: "border-sky-200/80 bg-sky-50 text-sky-700",
    }
  }
  return {
    label: "Nhiệm vụ",
    tone: "border-slate-200/80 bg-slate-100 text-slate-700",
  }
}

function getTaskGuide(task: string, weekNumber: number): string {
  return `Dành khoảng 45–60 phút để hoàn thành nhiệm vụ này. Ghi chú các khái niệm cốt lõi, áp dụng trực tiếp vào bài tập hoặc dự án tuần ${weekNumber}.`
}

interface TaskItemProps {
  taskId: string
  taskTitle: string
  weekNumber: number
  isDone: boolean
  onToggle: () => void
}

function TaskItem({
  taskId,
  taskTitle,
  weekNumber,
  isDone,
  onToggle,
}: TaskItemProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const chip = useMemo(() => getTaskResourceChip(taskTitle), [taskTitle])

  return (
    <div
      data-testid={`roadmap-task-${taskId}`}
      className={`rounded-2xl border p-3 sm:p-3.5 transition-all duration-200 ${
        isDone
          ? "border-emerald-200/90 bg-emerald-50/40"
          : "border-slate-200/80 bg-white/80 hover:border-sky-300 hover:shadow-2xs"
      }`}
    >
      <div className="flex items-start gap-3">
        {/* Satisfying animated completion checkbox */}
        <motion.button
          type="button"
          whileTap={{ scale: 0.88 }}
          onClick={onToggle}
          className={`mt-0.5 grid size-5 shrink-0 place-items-center rounded-lg border transition-colors ${
            isDone
              ? "border-emerald-500 bg-emerald-500 text-white shadow-2xs"
              : "border-slate-300 bg-white hover:border-sky-500"
          }`}
          aria-label={
            isDone ? "Đánh dấu chưa hoàn thành" : "Đánh dấu hoàn thành"
          }
        >
          <motion.div
            initial={false}
            animate={{ scale: isDone ? 1 : 0, opacity: isDone ? 1 : 0 }}
            transition={{ type: "spring", stiffness: 500, damping: 28 }}
          >
            <Check size={13} strokeWidth={3} />
          </motion.div>
        </motion.button>

        {/* Task Title & Upfront Resource Chip */}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5 mb-1">
            <span
              className={`rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${chip.tone}`}
            >
              {chip.label}
            </span>
          </div>

          <p
            onClick={onToggle}
            className={`cursor-pointer text-xs sm:text-sm leading-snug transition-colors ${
              isDone
                ? "font-medium text-slate-400 line-through"
                : "font-semibold text-slate-800 hover:text-sky-700"
            }`}
          >
            {taskTitle}
          </p>

          {/* Toggle Expandable Guide */}
          <button
            type="button"
            onClick={() => setIsExpanded((prev) => !prev)}
            className="mt-2 inline-flex items-center gap-1 text-[11px] font-bold text-sky-600 hover:text-sky-800 transition-colors"
          >
            <span>{isExpanded ? "Thu gọn gợi ý" : "Xem hướng dẫn chi tiết"}</span>
            <ChevronDown
              size={12}
              className={`transition-transform duration-200 ${
                isExpanded ? "rotate-180" : ""
              }`}
            />
          </button>

          {/* Expandable Task Detail */}
          <AnimatePresence>
            {isExpanded && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
                className="overflow-hidden"
              >
                <div className="mt-2.5 rounded-xl border border-sky-100 bg-sky-50/60 p-3 text-xs text-slate-600">
                  <p className="leading-relaxed font-medium text-slate-700">
                    {getTaskGuide(taskTitle, weekNumber)}
                  </p>
                  <div className="mt-2 flex items-center justify-between text-[11px] font-semibold text-slate-500 border-t border-sky-100 pt-1.5">
                    <span className="flex items-center gap-1">
                      <Clock3 size={11} />
                      Thời lượng: 45–60 phút
                    </span>
                    <span className="text-sky-700 font-bold">
                      Chuẩn đầu ra W{weekNumber}
                    </span>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}

export function RoadmapView() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialCode = searchParams.get("major") || "7480101"
  const initialName =
    searchParams.get("name") ||
    availableMajors.find((m) => m.code === initialCode)?.name ||
    "Khoa học máy tính"

  const [majorCode, setMajorCode] = useState(initialCode)
  const [majorName, setMajorName] = useState(initialName)
  const [weeks, setWeeks] = useState<RoadmapWeek[]>([])
  const [loading, setLoading] = useState(false)
  const [personalizing, setPersonalizing] = useState(false)
  const [savingProgress, setSavingProgress] = useState(false)
  const [savedNotice, setSavedNotice] = useState<string | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [operationError, setOperationError] = useState<string | null>(null)
  const [guidance, setGuidance] = useState<GuidancePersonalization | null>(null)
  const operationVersion = useRef(0)
  const currentMajor = useRef(majorCode)
  useEffect(() => { currentMajor.current = majorCode }, [majorCode])
  useEffect(() => () => { operationVersion.current += 1 }, [])

  // Mobile/Tablet Week Accordion State (week-1 open by default)
  const [openWeekAccordions, setOpenWeekAccordions] = useState<
    Record<string, boolean>
  >({ "week-1": true })

  const toggleWeekAccordion = (weekId: string) => {
    setOpenWeekAccordions((prev) => ({
      ...prev,
      [weekId]: !prev[weekId],
    }))
  }

  useEffect(() => {
    const paramMajor = searchParams.get("major")
    const paramName = searchParams.get("name")
    if (paramMajor && paramMajor !== majorCode) {
      setMajorCode(paramMajor)
      const matched = availableMajors.find((m) => m.code === paramMajor)
      setMajorName(paramName || matched?.name || `Mã ngành ${paramMajor}`)
    }
  }, [searchParams, majorCode])

  const totalTasks = useMemo(() => weeks.reduce((acc, week) => acc + week.tasks.length, 0), [weeks])
  const { completed, toggle, restoreCompleted, progress } = useRoadmap(majorCode, totalTasks)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setWeeks([]); setGuidance(null); setOperationError(null)
    Promise.all([
      requestJSON<RoadmapWeek[]>(`/roadmap/weeks/${majorCode}`, { signal: controller.signal }),
      requestJSON<SavedRoadmapProgress>(`/roadmap/progress/${majorCode}`, { signal: controller.signal }).catch(error => {
        if (error instanceof ApiError && error.status === 404) return null
        throw error
      }),
    ]).then(([baseWeeks, saved]) => {
      if (controller.signal.aborted) return
      const savedGuidance = saved?.personalized_schedule?.guidance
      const effectiveWeeks = savedGuidance ? scheduleToWeeks(savedGuidance, majorCode) : baseWeeks
      setWeeks(effectiveWeeks)
      setGuidance(savedGuidance || null)
      if (saved) {
        const savedTasks = saved.personalized_schedule?.completed_tasks
        const allowed = new Set(effectiveWeeks.flatMap(week => week.tasks.map((_, index) => `${week.id}-${index}`)))
        const finished = Array.isArray(savedTasks) ? savedTasks.filter(task => typeof task === "string" && allowed.has(task))
          : effectiveWeeks.filter(week => saved.completed_milestones.includes(week.week)).flatMap(week => week.tasks.map((_, index) => `${week.id}-${index}`))
        restoreCompleted(finished)
      }
    }).catch(error => {
      if (!controller.signal.aborted) setOperationError(error instanceof Error ? error.message : "Không tải được lộ trình và tiến độ.")
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [majorCode, restoreCompleted])

  const selectedWeek = weeks.find((item) => item.id === selected)

  const handleSelectMajor = (code: string) => {
    const found = availableMajors.find((m) => m.code === code)
    const name = found ? found.name : `Ngành ${code}`
    setMajorCode(code)
    setMajorName(name)
    setSearchParams({ major: code, name })
  }

  const handlePersonalizeByAI = async () => {
    if (personalizing) return
    setPersonalizing(true)
    setOperationError(null)
    const expectedMajor = majorCode
    const version = ++operationVersion.current
    try {
      const result = await requestJSON<GuidancePersonalization>(
        `/roadmap/roadmaps/${majorCode}/personalized?weekly_hours_available=10`, { method: "POST" },
      )
      if (version !== operationVersion.current || currentMajor.current !== expectedMajor) return
      setWeeks(scheduleToWeeks(result, expectedMajor))
      setGuidance(result)
      restoreCompleted([])
      setSavedNotice(result.is_fallback
        ? "Đã lập lịch theo hồ sơ từ mẫu khám phá. Cần đối chiếu chương trình của trường; bấm Lưu tiến độ để giữ lịch này."
        : "Đã lập lịch theo hồ sơ từ lộ trình có nguồn. Bấm Lưu tiến độ để giữ lịch này.")
      window.setTimeout(() => setSavedNotice(null), 3500)
    } catch (error) {
      if (version === operationVersion.current) setOperationError(error instanceof Error ? error.message : "Không cá nhân hóa được lộ trình.")
    } finally {
      if (version === operationVersion.current) setPersonalizing(false)
    }
  }

  const handleSaveProgress = async () => {
    if (savingProgress) return
    setSavingProgress(true); setOperationError(null)
    const expectedMajor = majorCode
    const version = ++operationVersion.current
    try {
      const finishedWeeks = weeks.filter(week => week.tasks.length > 0 && week.tasks.every((_, index) => completed.includes(`${week.id}-${index}`))).map(week => week.week)
      await requestJSON("/roadmap/progress", {
        method: "POST",
        body: JSON.stringify({ major_code: majorCode, current_step: weeks.find(week => !finishedWeeks.includes(week.week))?.week || weeks.length || 1,
          completed_milestones: finishedWeeks, personalized_schedule: { completed_tasks: completed, guidance } }),
      })
      if (version !== operationVersion.current || currentMajor.current !== expectedMajor) return
      setSavedNotice(`Đã lưu tiến độ (${progress}%) cho ngành ${majorName}.`)
    } catch (error) {
      if (version === operationVersion.current) setOperationError(error instanceof Error ? error.message : "Chưa lưu được tiến độ lên máy chủ.")
    } finally { if (version === operationVersion.current) setSavingProgress(false) }
  }

  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
      className="min-h-[calc(100vh-72px)] py-8 sm:py-10"
    >
      <PageContainer className="max-w-7xl">
        {operationError && <p role="alert" className="mb-5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{operationError}</p>}
        {!loading && weeks.length === 0 && <p className="mb-5 text-sm text-slate-600">Chưa có dữ liệu lộ trình cho ngành này.</p>}
        {guidance && <div role="status" data-testid="roadmap-provenance" className="mb-5 rounded-xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-900"><p className="font-semibold">{guidance.is_fallback ? "Mẫu khám phá cần đối chiếu" : "Lộ trình có nguồn tham khảo"}</p><p className="mt-2">{guidance.personalization_summary}</p><p className="mt-2">Lịch được dựng từ dữ liệu hồ sơ; không phải kết luận do LLM sinh.</p></div>}
        {/* Toast Notification */}
        {savedNotice && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="mb-5 flex items-center gap-2.5 rounded-2xl border border-emerald-200/90 bg-emerald-50/90 px-4 py-3 text-xs font-bold text-emerald-900 shadow-sm backdrop-blur-xl"
          >
            <Check size={16} className="text-emerald-600 shrink-0" />
            <span>{savedNotice}</span>
          </motion.div>
        )}

        {/* Top Header Bar & Progress Hero */}
        <div className="mb-7 flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
          <div>
            <div className="flex flex-wrap items-center gap-2.5 mb-2">
              <Link
                to={`/majors/${majorCode}`}
                className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200/80 bg-white/80 px-3 py-1.5 text-xs font-bold text-slate-600 shadow-2xs backdrop-blur-md transition-colors hover:border-sky-300 hover:text-sky-700"
              >
                <ArrowLeft size={13} />
                Chi tiết ngành
              </Link>
              <Badge tone="indigo">Lộ trình 4 tuần</Badge>
              <span className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-bold text-sky-800">
                Mã {majorCode}
              </span>
              {loading && (
                <Loader2 size={15} className="animate-spin text-sky-600" />
              )}
            </div>

            <h1 className="text-2xl font-black tracking-tight text-slate-900 sm:text-3xl lg:text-4xl">
              {majorName}
            </h1>

            {/* Interactive Major Selector & AI Personalize Trigger */}
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-2 rounded-xl border border-slate-200/80 bg-white/80 px-3.5 py-2 shadow-2xs backdrop-blur-md">
                <GraduationCap size={16} className="text-sky-600 shrink-0" />
                <select
                  value={majorCode}
                  onChange={(e) => handleSelectMajor(e.target.value)}
                  className="bg-transparent text-xs font-bold text-slate-800 outline-none cursor-pointer"
                >
                  {!availableMajors.some((m) => m.code === majorCode) && (
                    <option value={majorCode}>
                      {majorName} ({majorCode})
                    </option>
                  )}
                  {availableMajors.map((m) => (
                    <option key={m.code} value={m.code}>
                      {m.name} ({m.code})
                    </option>
                  ))}
                </select>
              </div>

              <Button
                variant="secondary"
                icon={Sparkles}
                disabled={personalizing || savingProgress || !weeks.length}
                loading={personalizing}
                onClick={handlePersonalizeByAI}
                className="text-xs"
              >
                Cá nhân hóa theo hồ sơ
              </Button>

              <Button
                variant="secondary"
                icon={Save}
                loading={savingProgress}
                onClick={handleSaveProgress}
                className="text-xs"
              >
                Lưu tiến độ
              </Button>
            </div>
          </div>

          {/* Progress Card */}
          <div className="glass-card w-full rounded-3xl border border-white/80 bg-white/80 p-5 shadow-sm backdrop-blur-xl lg:w-76">
            <div className="mb-2.5 flex items-center justify-between text-xs font-bold">
              <span className="text-slate-600">Tiến độ hoàn thành</span>
              <span className="text-base font-extrabold text-sky-600">
                {progress}%
              </span>
            </div>

            <div className="h-2.5 w-full rounded-full bg-slate-100 overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
                className="h-full rounded-full bg-sky-600"
              />
            </div>

            <div className="mt-3 flex items-center justify-between text-xs font-semibold text-slate-500">
              <span className="flex items-center gap-1.5">
                <Clock3 size={13} className="text-slate-400" />
                {weeks.length} tuần học tập
              </span>
              <span className="flex items-center gap-1.5">
                <Target size={13} className="text-sky-600" />
                <b className="text-slate-800">{completed.length}</b>/{totalTasks}{" "}
                mục
              </span>
            </div>
          </div>
        </div>

        {/* Section 1: Interactive Learning Flow Map */}
        <div className="mb-8">
          <div className="mb-3.5 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-black text-slate-900 sm:text-lg flex items-center gap-2">
                <Compass size={18} className="text-sky-600" />
                Bản đồ học tập trực quan
              </h2>
              <p className="text-xs text-slate-500">
                Nhấp vào bất kỳ tuần nào trên sơ đồ để xem giáo trình chi tiết và tài liệu hướng dẫn
              </p>
            </div>

            <div className="flex items-center gap-4 text-xs font-semibold text-slate-600">
              <span className="flex items-center gap-1.5">
                <span className="size-2.5 rounded-full bg-sky-500" />
                Đang học / Mở
              </span>
              <span className="flex items-center gap-1.5">
                <span className="size-2.5 rounded-full bg-emerald-500" />
                Đã hoàn thành
              </span>
            </div>
          </div>

          <RoadmapFlow
            weeks={weeks}
            completed={completed}
            onOpen={setSelected}
          />
        </div>

        {/* Section 2: Detailed 4-Week Milestone Cards (Responsive & Collapsible on Mobile/Tablet) */}
        <div>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-base font-black text-slate-900 sm:text-lg flex items-center gap-2">
                <Layers size={18} className="text-sky-600" />
                Chi tiết nhiệm vụ 4 tuần
              </h2>
              <p className="text-xs text-slate-500">
                Đánh dấu các mục tiêu đã làm xong để hệ thống tự động ghi nhận tiến độ
              </p>
            </div>
          </div>

          {/* 4 Weeks Grid - Collapsible cleanly on Mobile/Tablet */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5 items-start">
            {weeks.map((w) => {
              const weekTaskIds = w.tasks.map((_, idx) => `${w.id}-${idx}`)
              const completedCount = weekTaskIds.filter((tId) =>
                completed.includes(tId),
              ).length
              const isWeekDone =
                w.tasks.length > 0 && completedCount === w.tasks.length
              const isOpenOnMobile = Boolean(openWeekAccordions[w.id])

              return (
                <div
                  key={w.id}
                  className={`rounded-3xl border bg-white/80 backdrop-blur-xl shadow-xs transition-all duration-200 overflow-hidden ${
                    isWeekDone
                      ? "border-emerald-200/90 shadow-emerald-500/5"
                      : "border-slate-200/80 hover:border-sky-300"
                  }`}
                >
                  {/* Card Header (Clickable to toggle on mobile, opens drawer on desktop) */}
                  <div
                    onClick={() => toggleWeekAccordion(w.id)}
                    className="p-5 cursor-pointer md:cursor-default bg-gradient-to-b from-slate-50/60 to-transparent border-b border-slate-100"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span
                          className={`grid size-8 place-items-center rounded-xl text-xs font-black ${
                            isWeekDone
                              ? "bg-emerald-600 text-white"
                              : "bg-sky-100 text-sky-700"
                          }`}
                        >
                          {isWeekDone ? (
                            <Check size={16} strokeWidth={2.5} />
                          ) : (
                            `W${w.week}`
                          )}
                        </span>
                        <span className="text-xs font-bold uppercase tracking-wider text-sky-700">
                          {w.eyebrow}
                        </span>
                      </div>

                      {/* Accordion Indicator on Mobile */}
                      <span className="md:hidden grid size-7 place-items-center rounded-lg bg-slate-100 text-slate-600">
                        <ChevronDown
                          size={15}
                          className={`transition-transform duration-200 ${
                            isOpenOnMobile ? "rotate-180" : ""
                          }`}
                        />
                      </span>

                      <span className="hidden md:inline-flex rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-bold text-slate-600">
                        {completedCount}/{w.tasks.length} xong
                      </span>
                    </div>

                    <h3 className="mt-3 text-sm font-black text-slate-900 leading-snug">
                      {w.title}
                    </h3>
                    <p className="mt-1 text-xs text-slate-500 line-clamp-2">
                      {w.description}
                    </p>
                  </div>

                  {/* Tasks Container (Always visible on md+, collapsible on mobile) */}
                  <div
                    className={`p-4 sm:p-5 space-y-3 ${
                      isOpenOnMobile ? "block" : "hidden md:block"
                    }`}
                  >
                    {w.tasks.map((task, tIndex) => {
                      const taskId = `${w.id}-${tIndex}`
                      const isDone = completed.includes(taskId)
                      return (
                        <TaskItem
                          key={taskId}
                          taskId={taskId}
                          taskTitle={task}
                          weekNumber={w.week}
                          isDone={isDone}
                          onToggle={() => toggle(taskId)}
                        />
                      )
                    })}

                    {/* Open Drawer / Syllabus Button */}
                    <button
                      type="button"
                      onClick={() => setSelected(w.id)}
                      className="mt-3 flex w-full items-center justify-center gap-1.5 rounded-xl border border-slate-200/90 bg-slate-50/80 py-2.5 text-xs font-bold text-slate-700 transition-colors hover:border-sky-300 hover:bg-sky-50/60 hover:text-sky-700"
                    >
                      <BookOpen size={14} />
                      Xem giáo trình & tài liệu tuần {w.week}
                      <ChevronRight size={14} />
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </PageContainer>

      {/* Week Deep-Dive Drawer */}
      <AnimatePresence>
        {selectedWeek && (
          <>
            <motion.button
              aria-label="Đóng"
              className="fixed inset-0 z-[60] bg-slate-950/40 backdrop-blur-sm"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
              onClick={() => setSelected(null)}
            />
            <motion.aside
              className="fixed bottom-0 right-0 top-0 z-[70] w-full max-w-lg overflow-y-auto bg-white p-6 shadow-2xl sm:p-8"
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <Badge tone="indigo">
                    Tuần {selectedWeek.week} · {selectedWeek.eyebrow}
                  </Badge>
                  <h2 className="mt-3 text-xl sm:text-2xl font-black text-slate-900 leading-tight">
                    {selectedWeek.title}
                  </h2>
                  <p className="mt-2 text-xs sm:text-sm leading-relaxed text-slate-600">
                    {selectedWeek.description}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setSelected(null)}
                  className="grid size-9 shrink-0 place-items-center rounded-xl bg-slate-100 text-slate-600 hover:bg-slate-200 transition"
                  aria-label="Đóng bảng chi tiết"
                >
                  <X size={18} />
                </button>
              </div>

              <div className="my-6 h-px bg-slate-200/80" />

              {/* Syllabus / Content Markdown */}
              <div className="markdown text-xs sm:text-sm leading-relaxed text-slate-700">
                <Markdown remarkPlugins={[remarkGfm]}>
                  {selectedWeek.content}
                </Markdown>
              </div>

              {/* Tasks List */}
              <div className="mt-8">
                <div className="mb-3.5 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <BookOpen size={16} className="text-sky-600" />
                    <h3 className="text-sm font-extrabold text-slate-900">
                      Nhiệm vụ tuần này
                    </h3>
                  </div>
                  <span className="text-xs font-semibold text-slate-500">
                    {
                      selectedWeek.tasks.filter((_, idx) =>
                        completed.includes(`${selectedWeek.id}-${idx}`),
                      ).length
                    }
                    /{selectedWeek.tasks.length} xong
                  </span>
                </div>

                <div className="space-y-3">
                  {selectedWeek.tasks.map((task, index) => {
                    const taskId = `${selectedWeek.id}-${index}`
                    const isDone = completed.includes(taskId)
                    return (
                      <TaskItem
                        key={taskId}
                        taskId={taskId}
                        taskTitle={task}
                        weekNumber={selectedWeek.week}
                        isDone={isDone}
                        onToggle={() => toggle(taskId)}
                      />
                    )
                  })}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="mt-8 space-y-2.5">
                <Button
                  className="w-full justify-center text-xs sm:text-sm"
                  loading={savingProgress}
                  onClick={handleSaveProgress}
                >
                  Lưu tiến độ học tập vào CSDL
                </Button>
                <Button
                  variant="secondary"
                  className="w-full justify-center text-xs"
                  onClick={() => setSelected(null)}
                >
                  Đóng chi tiết
                </Button>
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </motion.section>
  )
}
