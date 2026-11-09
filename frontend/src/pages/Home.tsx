import { AnimatePresence, motion } from "framer-motion"
import {
  ArrowRight,
  BarChart3,
  BookOpenCheck,
  Brain,
  Check,
  ChevronRight,
  Compass,
  Database,
  Eye,
  GraduationCap,
  ShieldCheck,
  Sparkles,
  Target,
} from "lucide-react"
import { useEffect, useState } from "react"
import { Link } from "react-router"
import { Button } from "../components/common/Button"
import { Card } from "../components/common/Card"
import { PageContainer } from "../components/layout/PageContainer"

const pillars = [
  {
    icon: Compass,
    label: "45% · Sở thích",
    title: "Holland RIASEC",
    text: "30 câu hỏi định vị 6 nhóm xu hướng nghề nghiệp.",
  },
  {
    icon: BarChart3,
    label: "35% · Học lực",
    title: "Chuẩn hóa Z-Score",
    text: "Đối chiếu điểm học tập theo tổ hợp môn xét tuyển.",
  },
  {
    icon: Brain,
    label: "20% · Nhận thức",
    title: "Phong cách tư duy",
    text: "8 chiều đánh giá cách tiếp thu và giải quyết vấn đề.",
  },
]

const heroImages = [
  {
    src: "https://images.unsplash.com/photo-1598981457915-aea220950616?crop=entropy&cs=tinysrgb&fit=crop&fm=jpg&q=85&w=1200",
    alt: "Học sinh đang tập trung học tập",
    label: "Khám phá năng lực",
  },
  {
    src: "https://images.unsplash.com/photo-1758270705290-62b6294dd044?crop=entropy&cs=tinysrgb&fit=crop&fm=jpg&q=85&w=1200",
    alt: "Nhóm sinh viên trao đổi",
    label: "Kết nối trải nghiệm",
  },
  {
    src: "https://images.unsplash.com/photo-1782388713336-fcb8aa6db8f0?crop=entropy&cs=tinysrgb&fit=crop&fm=jpg&q=85&w=1200",
    alt: "Sinh viên hợp tác dự án",
    label: "Kiến tạo tương lai",
  },
]

export function Home() {
  const [activeImage, setActiveImage] = useState(0)

  useEffect(() => {
    const timer = window.setInterval(
      () => setActiveImage((current) => (current + 1) % heroImages.length),
      4500,
    )
    return () => window.clearInterval(timer)
  }, [])

  return (
    <>
      <section className="relative overflow-hidden bg-transparent pb-16 pt-10 sm:pt-16 lg:pb-22">
        <PageContainer className="relative grid items-center gap-10 lg:grid-cols-[1.05fr_.95fr]">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/85 bg-white/60 px-3.5 py-1.5 text-xs font-bold text-sky-700 backdrop-blur-md">
              <Sparkles size={14} />
              AI CareerGuide · XAI
            </div>
            <h1 className="max-w-2xl text-4xl font-black leading-[1.08] tracking-[-0.04em] text-slate-950 sm:text-5xl lg:text-[60px]">
              Không chỉ chọn ngành.
              <br />
              <span className="text-sky-600">Chọn đúng tương lai.</span>
            </h1>
            <p className="mt-4 max-w-lg text-base leading-7 text-slate-600">
              Kết nối sở thích, học lực và tư duy để gợi ý ngành học phù hợp với
              lộ trình minh bạch.
            </p>
            <div className="mt-7 flex flex-col gap-3 sm:flex-row">
              <Link to="/assessment">
                <Button className="w-full sm:w-auto" icon={ArrowRight}>
                  Bắt đầu đánh giá
                </Button>
              </Link>
              <Link to="/dashboard">
                <Button
                  className="w-full sm:w-auto"
                  variant="secondary"
                  icon={Eye}
                >
                  Bản đồ ngành học
                </Button>
              </Link>
            </div>
            <div className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-xs font-semibold text-slate-500">
              {["10 phút", "435 ngành chuẩn", "Giải thích minh bạch"].map(
                (item) => (
                  <span className="flex items-center gap-1.5" key={item}>
                    <Check size={14} className="text-sky-600" />
                    {item}
                  </span>
                ),
              )}
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.12, duration: 0.5 }}
            className="relative"
          >
            <div className="relative h-[430px] overflow-hidden rounded-[34px] border-4 border-white/80 bg-slate-900 shadow-[0_24px_80px_rgba(14,165,233,0.18)] backdrop-blur-xl">
              <AnimatePresence mode="popLayout">
                <motion.img
                  key={heroImages[activeImage].src}
                  src={heroImages[activeImage].src}
                  alt={heroImages[activeImage].alt}
                  initial={{ opacity: 0, scale: 1.05 }}
                  animate={{ opacity: 0.84, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.98 }}
                  transition={{
                    opacity: { duration: 0.8 },
                    scale: { duration: 4.5 },
                  }}
                  className="absolute inset-0 h-full w-full object-cover"
                />
              </AnimatePresence>
              <div className="absolute inset-0 bg-gradient-to-t from-slate-950/90 via-transparent to-transparent" />
              <div className="absolute left-5 top-5 rounded-full border border-white/40 bg-white/15 px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-white backdrop-blur-xl">
                {heroImages[activeImage].label}
              </div>
              <div className="absolute bottom-0 left-0 right-0 p-6 text-white">
                <div className="flex items-end justify-between">
                  <div>
                    <span className="text-4xl font-black">435</span>
                    <span className="ml-2 text-sm text-sky-100">
                      ngành đào tạo
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {heroImages.map((image, index) => (
                      <button
                        key={image.src}
                        onClick={() => setActiveImage(index)}
                        aria-label={`Xem ảnh ${index + 1}`}
                        className={`h-1.5 rounded-full transition-all ${
                          activeImage === index
                            ? "w-8 bg-white"
                            : "w-2 bg-white/35 hover:bg-white/60"
                        }`}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="glass-panel absolute -left-5 top-8 rounded-2xl p-3.5 shadow-xl">
              <div className="flex items-center gap-3">
                <span className="grid size-10 place-items-center rounded-xl bg-sky-500/15 text-sky-600">
                  <Target size={19} />
                </span>
                <div>
                  <p className="text-[10px] font-bold uppercase text-slate-400">
                    Độ tương thích
                  </p>
                  <p className="font-black text-slate-900">94% MATCH</p>
                </div>
              </div>
            </div>
          </motion.div>
        </PageContainer>
      </section>

      <section id="about" className="py-14">
        <PageContainer>
          <div className="mx-auto mb-10 max-w-xl text-center">
            <p className="text-xs font-extrabold uppercase tracking-[.2em] text-sky-600">
              Mô hình 3 trụ cột
            </p>
            <h2 className="mt-2 text-3xl font-black tracking-tight text-slate-950">
              Hiểu mình trước khi chọn ngành
            </h2>
          </div>
          <div className="grid gap-5 md:grid-cols-3">
            {pillars.map((item) => (
              <Card
                key={item.title}
                className="group rounded-3xl p-6 transition hover:-translate-y-1"
              >
                <span className="grid size-12 place-items-center rounded-2xl border border-white/85 bg-sky-500/12 text-sky-600">
                  <item.icon size={22} />
                </span>
                <p className="mt-5 text-xs font-extrabold uppercase tracking-widest text-sky-600">
                  {item.label}
                </p>
                <h3 className="mt-1.5 text-xl font-black text-slate-900">
                  {item.title}
                </h3>
                <p className="mt-2 text-sm leading-6 text-slate-500">
                  {item.text}
                </p>
                <Link
                  to="/assessment"
                  className="mt-4 inline-flex items-center gap-1 text-xs font-bold text-sky-600 hover:text-sky-800"
                >
                  Khám phá <ChevronRight size={14} />
                </Link>
              </Card>
            ))}
          </div>
        </PageContainer>
      </section>

      <section className="mx-4 my-6 rounded-[36px] border border-white/85 bg-white/40 py-14 text-slate-900 shadow-[0_20px_60px_rgba(14,165,233,0.12)] backdrop-blur-2xl">
        <PageContainer className="grid items-center gap-8 lg:grid-cols-2">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full border border-white/85 bg-white/60 px-3 py-1 text-xs font-bold text-sky-700">
              <ShieldCheck size={14} />
              Explainable AI
            </span>
            <h2 className="mt-4 text-3xl font-black tracking-tight">
              AI gợi ý minh bạch.
              <br />
              Bạn là người quyết định.
            </h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {[
              ["Dữ liệu chuẩn hóa", Database],
              ["Giải thích từng điểm số", Eye],
              ["Lộ trình 4 tuần", BookOpenCheck],
              ["435 ngành đào tạo", GraduationCap],
            ].map(([label, Icon]) => (
              <div
                key={String(label)}
                className="flex items-center gap-3 rounded-2xl border border-white/90 bg-white/60 p-4 text-slate-800 shadow-2xs backdrop-blur-xl transition hover:-translate-y-0.5 hover:bg-white/80"
              >
                <span className="grid size-10 place-items-center rounded-xl bg-sky-500/12 text-sky-600">
                  <Icon size={19} />
                </span>
                <span className="text-sm font-bold">{String(label)}</span>
              </div>
            ))}
          </div>
        </PageContainer>
      </section>
    </>
  )
}
