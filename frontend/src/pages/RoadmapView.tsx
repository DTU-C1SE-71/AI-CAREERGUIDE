import { AnimatePresence, motion } from "framer-motion"
import {
  BookOpen,
  Check,
  CheckCircle2,
  Circle,
  Clock3,
  GraduationCap,
  Loader2,
  Sparkles,
  Target,
  X,
} from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import Markdown from "react-markdown"
import { useSearchParams } from "react-router"
import remarkGfm from "remark-gfm"
import { Badge } from "../components/common/Badge"
import { Button } from "../components/common/Button"
import { PageContainer } from "../components/layout/PageContainer"
import { RoadmapFlow } from "../components/visualization/RoadmapFlow"
import { useRoadmap } from "../hooks/useRoadmap"
import { apiRequest } from "../services/api"
import { roadmap as fallbackRoadmap } from "../services/mockData"
import type { RoadmapWeek } from "../types/roadmap"

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

export function RoadmapView() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialCode = searchParams.get("major") || "7480101"
  const initialName =
    searchParams.get("name") ||
    availableMajors.find((m) => m.code === initialCode)?.name ||
    "Khoa học máy tính"

  const [majorCode, setMajorCode] = useState(initialCode)
  const [majorName, setMajorName] = useState(initialName)
  const [weeks, setWeeks] = useState<RoadmapWeek[]>(fallbackRoadmap)
  const [loading, setLoading] = useState(false)
  const [personalizing, setPersonalizing] = useState(false)
  const [savedNotice, setSavedNotice] = useState<string | null>(null)
  const [selected, setSelected] = useState<string | null>(null)

  useEffect(() => {
    const paramMajor = searchParams.get("major")
    const paramName = searchParams.get("name")
    if (paramMajor && paramMajor !== majorCode) {
      setMajorCode(paramMajor)
      const matched = availableMajors.find((m) => m.code === paramMajor)
      setMajorName(paramName || matched?.name || `Mã ngành ${paramMajor}`)
    }
  }, [searchParams, majorCode])

  useEffect(() => {
    let mounted = true
    setLoading(true)
    apiRequest<RoadmapWeek[] | null>(`/roadmap/weeks/${majorCode}`, null)
      .then((res) => {
        if (!mounted) return
        if (res && Array.isArray(res) && res.length > 0) {
          setWeeks(res)
        } else {
          setWeeks(fallbackRoadmap)
        }
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [majorCode])

  const totalTasks = useMemo(
    () => weeks.reduce((acc, w) => acc + (w.tasks?.length || 0), 0) || 12,
    [weeks],
  )
  const { completed, toggle, progress } = useRoadmap(majorCode, totalTasks)
  const week = weeks.find((item) => item.id === selected)

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
    try {
      const res = await apiRequest<{
        personalized_milestones?: Array<{
          week?: number
          title: string
          description: string
          actions?: string[]
        }>
      } | null>(`/roadmap/roadmaps/${majorCode}/personalized?weekly_hours_available=10`, null, {
        method: "POST",
      })
      if (
        res &&
        res.personalized_milestones &&
        res.personalized_milestones.length > 0
      ) {
        const eyebrows = ["Nền tảng AI", "Thực hành sâu", "Dự án cá nhân", "Về đích"]
        const updated: RoadmapWeek[] = res.personalized_milestones
          .slice(0, 4)
          .map((m, idx) => ({
            id: `week-${idx + 1}`,
            week: idx + 1,
            eyebrow: eyebrows[idx] || `Tuần ${idx + 1}`,
            title: m.title,
            description: m.description,
            content: `## ${m.title}\n\n${m.description}\n\n### Hoạt động cá nhân hóa theo Competency Gaps:\n${(m.actions || []).map((a) => `- ${a}`).join("\n")}`,
            tasks:
              m.actions && m.actions.length > 0
                ? m.actions
                : weeks[idx]?.tasks || fallbackRoadmap[idx].tasks,
          }))
        setWeeks(updated)
      } else {
        setWeeks((current) =>
          current.map((w, idx) => ({
            ...w,
            eyebrow: `${w.eyebrow} · AI Tối ưu`,
            tasks: [
              ...w.tasks.slice(0, 2),
              idx === 0
                ? `Bù kỹ năng nền tảng ngành ${majorName} (45 phút/ngày)`
                : idx === 1
                  ? `Thực hành bài tập chuẩn hóa Z-Score cho ${majorName}`
                  : idx === 2
                    ? `Hoàn thiện mini-project thực tế ngành ${majorName}`
                    : `Tổng kết hồ sơ năng lực & phản tư định hướng ${majorCode}`,
            ],
          })),
        )
      }
      setSavedNotice("Đã cá nhân hóa lộ trình 4 tuần theo khoảng trống kỹ năng của bạn!")
      window.setTimeout(() => setSavedNotice(null), 3500)
    } finally {
      setPersonalizing(false)
    }
  }

  const handleSaveProgress = async () => {
    await apiRequest(
      "/roadmap/progress",
      null,
      {
        method: "POST",
        body: JSON.stringify({
          major_code: majorCode,
          completed_milestones: completed,
          completion_percentage: progress,
        }),
      },
    )
    setSelected(null)
    setSavedNotice(`Đã lưu tiến độ (${progress}%) cho ngành ${majorName}!`)
    window.setTimeout(() => setSavedNotice(null), 3000)
  }

  return (
    <section className="min-h-[calc(100vh-72px)] py-9 sm:py-12">
      <PageContainer>
        {savedNotice && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-5 flex items-center gap-2 rounded-2xl border border-white/85 bg-white/75 px-4 py-3 text-xs font-extrabold text-sky-800 shadow-xs backdrop-blur-xl"
          >
            <Check size={15} className="text-sky-600" />
            {savedNotice}
          </motion.div>
        )}

        <div className="mb-7 flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="indigo">Lộ trình 4 tuần</Badge>
              <span className="rounded-full border border-white/80 bg-white/65 px-2.5 py-1 text-[10px] font-extrabold text-sky-700">
                Mã {majorCode}
              </span>
              {loading && (
                <Loader2 size={14} className="animate-spin text-sky-600" />
              )}
            </div>
            <h1 className="mt-2.5 text-3xl font-black tracking-tight sm:text-4xl">
              {majorName}
            </h1>

            {/* Interactive Major Selector & AI Personalize Trigger */}
            <div className="mt-4 flex flex-wrap items-center gap-2.5">
              <div className="flex items-center gap-2 rounded-2xl border border-white/85 bg-white/65 px-3 py-2 shadow-2xs backdrop-blur-md">
                <GraduationCap size={16} className="text-sky-600 shrink-0" />
                <select
                  value={majorCode}
                  onChange={(e) => handleSelectMajor(e.target.value)}
                  className="bg-transparent text-xs font-extrabold text-slate-800 outline-none cursor-pointer"
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
                loading={personalizing}
                onClick={handlePersonalizeByAI}
                className="text-xs"
              >
                Tối ưu bằng AI
              </Button>
            </div>
          </div>

          <div className="glass-card w-full rounded-3xl p-4 lg:w-68">
            <div className="mb-2 flex justify-between text-xs font-bold">
              <span>Tiến độ</span>
              <span className="text-sky-600">{progress}%</span>
            </div>
            <div className="h-2 rounded-full bg-white/70">
              <div
                className="h-full rounded-full bg-sky-600 transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="mt-2.5 flex justify-between text-[10px] font-semibold text-slate-500">
              <span className="flex items-center gap-1">
                <Clock3 size={12} />
                {weeks.length} tuần
              </span>
              <span className="flex items-center gap-1">
                <Target size={12} />
                {completed.length}/{totalTasks} mục
              </span>
            </div>
          </div>
        </div>

        <div className="mb-3 flex items-center justify-between">
          <p className="text-xs font-bold uppercase tracking-widest text-sky-600">
            Bản đồ học tập tương tác
          </p>
          <div className="hidden gap-3 text-[10px] font-bold text-slate-500 sm:flex">
            <span className="flex items-center gap-1">
              <i className="size-2 rounded-full bg-sky-400" />
              Đang học
            </span>
            <span className="flex items-center gap-1">
              <i className="size-2 rounded-full bg-sky-600" />
              Hoàn thành
            </span>
          </div>
        </div>

        <RoadmapFlow
          weeks={weeks}
          completed={completed}
          onOpen={setSelected}
        />
      </PageContainer>

      <AnimatePresence>
        {week && (
          <>
            <motion.button
              aria-label="Đóng"
              className="fixed inset-0 z-[60] bg-slate-950/40 backdrop-blur-sm"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelected(null)}
            />
            <motion.aside
              className="fixed bottom-0 right-0 top-0 z-[70] w-full overflow-y-auto bg-white p-6 shadow-2xl sm:w-[480px] sm:p-8"
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", damping: 30, stiffness: 280 }}
            >
              <div className="flex items-start justify-between">
                <div>
                  <Badge tone="indigo">
                    Tuần {week.week} · {week.eyebrow}
                  </Badge>
                  <h2 className="mt-4 text-2xl font-black">{week.title}</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-600">
                    {week.description}
                  </p>
                </div>
                <button
                  onClick={() => setSelected(null)}
                  className="grid size-10 shrink-0 place-items-center rounded-xl bg-slate-100 hover:bg-slate-200"
                >
                  <X size={18} />
                </button>
              </div>
              <div className="my-7 h-px bg-slate-200" />
              <div className="markdown text-sm leading-7 text-slate-700">
                <Markdown remarkPlugins={[remarkGfm]}>{week.content}</Markdown>
              </div>
              <div className="mt-8">
                <div className="mb-4 flex items-center gap-2">
                  <BookOpen size={18} className="text-sky-600" />
                  <h3 className="text-sm font-extrabold">Nhiệm vụ tuần này</h3>
                </div>
                <div className="space-y-2">
                  {week.tasks.map((task, index) => {
                    const id = `${week.id}-${index}`
                    const done = completed.includes(id)
                    return (
                      <button
                        key={task}
                        onClick={() => toggle(id)}
                        className={`flex w-full items-center gap-3 rounded-xl border p-3 text-left text-sm font-semibold transition ${
                          done
                            ? "border-emerald-200 bg-emerald-50 text-emerald-900"
                            : "border-slate-200 hover:border-sky-300"
                        }`}
                      >
                        {done ? (
                          <CheckCircle2
                            size={19}
                            className="text-emerald-600 shrink-0"
                          />
                        ) : (
                          <Circle size={19} className="text-slate-300 shrink-0" />
                        )}
                        <span>{task}</span>
                      </button>
                    )
                  })}
                </div>
              </div>
              <Button className="mt-8 w-full" onClick={handleSaveProgress}>
                Lưu tiến độ vào CSDL
              </Button>
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </section>
  )
}
