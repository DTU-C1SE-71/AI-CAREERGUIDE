import { motion } from "framer-motion"
import {
  ArrowRight,
  BarChart3,
  BookOpenCheck,
  Brain,
  Check,
  Compass,
  Database,
  Eye,
  GraduationCap,
  Sparkles,
  Target,
} from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { Link } from "react-router"
import { Button } from "../components/common/Button"
import { Card } from "../components/common/Card"
import { PageContainer } from "../components/layout/PageContainer"
import { requestJSON } from "../services/api"

const pillars = [
  {
    icon: Compass,
    weight: "Trụ cột 1 · Hệ số động",
    category: "Sở thích nghề nghiệp",
    title: "Holland RIASEC",
    text: "30 câu hỏi thực tế định vị 6 nhóm xu hướng nghề nghiệp: Kỹ thuật, Nghiên cứu, Nghệ thuật, Xã hội, Quản lý và Nghiệp vụ.",
    actionText: "Làm bài trắc nghiệm RIASEC",
  },
  {
    icon: BarChart3,
    weight: "Trụ cột 2 · Hệ số động",
    category: "Năng lực học tập",
    title: "Chuẩn hóa Z-Score",
    text: "Đối chiếu điểm số theo các tổ hợp môn xét tuyển và chuẩn hóa độ lệch điểm để ước lượng mức độ khả thi mang tính tham khảo.",
    actionText: "Nhập điểm và kiểm tra",
  },
  {
    icon: Brain,
    weight: "Trụ cột 3 · Hệ số động",
    category: "Phong cách nhận thức",
    title: "Tư duy & Thích ứng",
    text: "8 chiều đánh giá phương thức tiếp thu, ra quyết định và thích ứng với môi trường học thuật đại học lẫn thị trường việc làm.",
    actionText: "Khám phá phong cách",
  },
]

const heroImages = [
  {
    src: "/images/hero/vn-dtu-overview.jpg",
    alt: "Toàn cảnh khuôn viên Đại học Duy Tân tại Đà Nẵng",
    label: "ĐH Duy Tân · Đà Nẵng",
  },
  {
    src: "/images/hero/vn-dtu-library.jpg",
    alt: "Thư viện hiện đại Đại học Duy Tân",
    label: "Thư viện ĐH Duy Tân",
  },
  {
    src: "/images/hero/vn-hust-campus.jpg",
    alt: "Khuôn viên Đại học Bách khoa Hà Nội",
    label: "ĐH Bách khoa Hà Nội",
  },
  {
    src: "/images/hero/vn-dtu-campus.jpg",
    alt: "Khu giảng đường Đại học Duy Tân",
    label: "Cơ sở ĐH Duy Tân",
  },
  {
    src: "/images/hero/vn-vnuhcm-campus.jpg",
    alt: "Nhà điều hành Đại học Quốc gia TP. Hồ Chí Minh",
    label: "ĐH Quốc gia TP.HCM",
  },
]

const capabilities = [
  {
    id: "catalog",
    icon: Database,
    title: "ngành đào tạo chuẩn hóa",
    desc: "Cập nhật đồng bộ theo danh mục đào tạo của Bộ GD&ĐT cùng xu hướng tuyển dụng thị trường lao động.",
  },
  {
    id: "xai",
    icon: Eye,
    title: "Giải thích minh bạch (XAI)",
    desc: "Bóc tách rõ ràng tỷ trọng đóng góp từ sở thích, điểm số tổ hợp và phong cách tư duy trong từng gợi ý.",
  },
  {
    id: "advisor",
    icon: BookOpenCheck,
    title: "Giáo viên Cố vấn AI",
    desc: "Đối chiếu nghề mơ ước với hồ sơ năng lực, phân tích kỹ năng và hỏi đáp trực tiếp cùng Giáo viên Cố vấn AI.",
  },
  {
    id: "universities",
    icon: GraduationCap,
    title: "Bản đồ trường đại học",
    desc: "Tra cứu điểm sàn, phương thức xét tuyển và cơ hội học bổng của các cơ sở đào tạo uy tín toàn quốc.",
  },
]

export function Home() {
  const [activeImage, setActiveImage] = useState(0)
  const [isHovered, setIsHovered] = useState(false)
  const [majorCount, setMajorCount] = useState<number | null>(null)

  const loadCatalogStats = useCallback(async (signal?: AbortSignal) => {
    try {
      const stats = await requestJSON<{ total_majors?: number }>(
        "/v1/taxonomy/catalog-stats",
        { signal },
      )
      if (!signal?.aborted && typeof stats?.total_majors === "number") {
        setMajorCount(stats.total_majors)
      }
    } catch {
      // Keep previous or placeholder count on transient error
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    void loadCatalogStats(controller.signal)

    const refreshIfVisible = () => {
      if (document.visibilityState === "visible") {
        void loadCatalogStats()
      }
    }

    window.addEventListener("focus", refreshIfVisible)
    document.addEventListener("visibilitychange", refreshIfVisible)

    return () => {
      controller.abort()
      window.removeEventListener("focus", refreshIfVisible)
      document.removeEventListener("visibilitychange", refreshIfVisible)
    }
  }, [loadCatalogStats])

  useEffect(() => {
    if (isHovered) return
    const timer = window.setInterval(
      () => setActiveImage((current) => (current + 1) % heroImages.length),
      5200,
    )
    return () => window.clearInterval(timer)
  }, [isHovered])

  const majorCountText =
    majorCount !== null ? majorCount.toLocaleString("vi-VN") : "—"

  return (
    <div className="relative overflow-hidden">
      {/* Ambient background glows */}
      <div className="pointer-events-none absolute -left-32 top-0 size-96 rounded-full bg-sky-200/40 blur-3xl" />
      <div className="pointer-events-none absolute right-0 top-32 size-[420px] rounded-full bg-cyan-200/35 blur-3xl" />

      {/* Hero Section */}
      <section className="relative pb-16 pt-8 sm:pb-20 sm:pt-14 lg:pb-24 lg:pt-16">
        <PageContainer className="grid items-center gap-12 lg:grid-cols-12 lg:gap-12 xl:gap-16">
          {/* Left Column: Hero Copy & Value Proposition */}
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
            className="flex flex-col lg:col-span-7"
          >
            <h1 className="max-w-2xl text-4xl font-black leading-[1.12] tracking-[-0.035em] text-slate-900 sm:text-5xl lg:text-[56px] xl:text-[62px]">
              Hiểu rõ bản thân.
              <span className="mt-1 block text-sky-600">
                Gợi mở hướng đi phù hợp.
              </span>
            </h1>

            <p className="mt-5 max-w-xl text-base leading-relaxed text-slate-600 sm:text-lg">
              Kết hợp sở thích nghề nghiệp, điểm số học tập và phong cách tư duy
              để gợi ý các ngành học phù hợp cùng góc nhìn phân tích năng lực
              mang tính tham khảo.
            </p>

            <div className="mt-8 flex flex-col gap-3.5 sm:flex-row sm:items-center">
              <Link to="/assessment" className="w-full sm:w-auto">
                <Button
                  className="w-full sm:w-auto"
                  size="lg"
                  icon={ArrowRight}
                >
                  Bắt đầu đánh giá
                </Button>
              </Link>
              <Link to="/majors" className="w-full sm:w-auto">
                <Button
                  className="w-full sm:w-auto"
                  variant="secondary"
                  size="lg"
                  icon={Eye}
                >
                  Bản đồ ngành học
                </Button>
              </Link>
            </div>

            <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-2.5 pt-2 text-xs font-semibold text-slate-600 sm:text-sm">
              {[
                "10 phút thực hiện",
                `${majorCountText} ngành chuẩn hóa`,
                "Giải thích AI minh bạch",
              ].map((item) => (
                <div key={item} className="inline-flex items-center gap-2">
                  <span className="grid size-5 place-items-center rounded-full bg-sky-100 text-sky-700">
                    <Check size={13} strokeWidth={2.8} />
                  </span>
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Right Column: Interactive Stacked Photo Deck Showcase */}
          <motion.div
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.08, duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            className="relative mx-auto w-full max-w-[440px] py-4 sm:py-6 lg:col-span-5 lg:max-w-none"
          >
            <div className="relative mx-auto h-[400px] w-[88%] sm:h-[450px] sm:w-[86%] lg:h-[470px] xl:h-[500px]">
              {heroImages.map((image, index) => {
                const depth =
                  (index - activeImage + heroImages.length) % heroImages.length
                const isFront = depth === 0
                const isVisibleStackCard =
                  depth === 0 || depth === 1 || depth === heroImages.length - 1
                const stackStyle =
                  depth === 0
                    ? { x: 0, y: 0, rotate: 0, scale: 1, opacity: 1, zIndex: 30 }
                    : depth === 1
                      ? {
                          x: 26,
                          y: 14,
                          rotate: 5,
                          scale: 0.94,
                          opacity: 0.92,
                          zIndex: 20,
                        }
                      : depth === heroImages.length - 1
                        ? {
                            x: -22,
                            y: 22,
                            rotate: -5,
                            scale: 0.89,
                            opacity: 0.82,
                            zIndex: 10,
                          }
                        : {
                            x: 0,
                            y: 26,
                            rotate: 0,
                            scale: 0.84,
                            opacity: 0,
                            zIndex: 0,
                          }

                return (
                  <motion.div
                    key={image.src}
                    initial={false}
                    animate={stackStyle}
                    transition={{
                      type: "spring",
                      stiffness: 260,
                      damping: 26,
                    }}
                    onClick={() =>
                      setActiveImage(
                        isFront
                          ? (activeImage + 1) % heroImages.length
                          : index,
                      )
                    }
                    className={`absolute inset-0 overflow-hidden rounded-3xl border-4 border-white bg-slate-900 shadow-2xl shadow-sky-950/15 ${
                      isVisibleStackCard
                        ? "cursor-pointer"
                        : "pointer-events-none"
                    }`}
                  >
                    <img
                      src={image.src}
                      alt={image.alt}
                      className="h-full w-full object-cover object-center"
                    />

                    {/* Contrast scrim */}
                    <div
                      className={`absolute inset-0 transition-opacity duration-300 ${
                        isFront
                          ? "bg-gradient-to-t from-slate-950/85 via-slate-950/20 to-transparent"
                          : "bg-slate-950/20"
                      }`}
                    />

                    {isFront && (
                      <>
                        {/* Image context badge */}
                        <div className="absolute left-5 top-5 rounded-full border border-white/25 bg-slate-900/60 px-3.5 py-1.5 text-xs font-bold uppercase tracking-wider text-white backdrop-blur-md">
                          {image.label}
                        </div>

                        {/* Bottom statistics and indicators */}
                        <div className="absolute bottom-0 left-0 right-0 p-6 text-white sm:p-7">
                          <div className="flex items-end justify-between gap-3">
                            <div>
                              <span className="text-3xl font-black tabular-nums tracking-tight sm:text-4xl">
                                {majorCountText}
                              </span>
                              <span className="ml-2 text-xs font-medium text-sky-200 sm:text-sm">
                                ngành đào tạo đại học
                              </span>
                            </div>

                            <div className="flex items-center gap-2">
                              {heroImages.map((dotImage, dotIndex) => (
                                <button
                                  key={dotImage.src}
                                  type="button"
                                  onClick={(event) => {
                                    event.stopPropagation()
                                    setActiveImage(dotIndex)
                                  }}
                                  aria-label={`Xem ảnh ${dotIndex + 1}`}
                                  className={`h-2 rounded-full transition-all duration-200 cursor-pointer ${
                                    activeImage === dotIndex
                                      ? "w-8 bg-white"
                                      : "w-2 bg-white/40 hover:bg-white/70"
                                  }`}
                                />
                              ))}
                            </div>
                          </div>
                        </div>
                      </>
                    )}
                  </motion.div>
                )
              })}
            </div>

            {/* Floating accuracy highlight badge */}
            <div className="glass-panel pointer-events-none absolute -right-2 -top-2 z-40 rounded-2xl border border-slate-200/80 p-3 shadow-lg shadow-sky-950/5 sm:-right-4 sm:top-2 sm:p-3.5">
              <div className="flex items-center gap-3">
                <span className="grid size-10 place-items-center rounded-xl border border-sky-100 bg-sky-50 text-sky-600 sm:size-11">
                  <Target size={22} />
                </span>
                <div>
                  <p className="text-xs font-semibold text-slate-500">
                    Gợi ý đa tiêu chí
                  </p>
                  <p className="text-sm font-black tabular-nums text-slate-900 sm:text-base">
                    Minh bạch · Tham khảo
                  </p>
                </div>
              </div>
            </div>
          </motion.div>
        </PageContainer>
      </section>

      {/* Section 2: 3-Pillar Value Proposition */}
      <section id="about" className="py-16 sm:py-20 lg:py-24">
        <PageContainer>
          <div className="mx-auto mb-12 max-w-2xl text-center sm:mb-16">
            <h2 className="text-3xl font-black tracking-tight text-slate-900 sm:text-4xl lg:text-5xl">
              Hiểu mình trước khi chọn ngành
            </h2>
            <p className="mt-4 text-base leading-relaxed text-slate-600 sm:text-lg">
              Mô hình đánh giá 3 chiều kết hợp trắc nghiệm sở thích, kết quả học
              tập và phong cách nhận thức làm cơ sở tham khảo cho lựa chọn của bạn.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-3 lg:gap-8">
            {pillars.map((item) => (
              <Card
                key={item.title}
                className="group flex flex-col justify-between rounded-3xl border border-slate-200/80 bg-white/80 p-7 shadow-sm transition-all duration-200 hover:-translate-y-1 hover:border-sky-300 hover:bg-white hover:shadow-xl hover:shadow-sky-500/5 sm:p-8"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="grid size-12 place-items-center rounded-2xl border border-sky-100 bg-sky-50 text-sky-600 transition-colors group-hover:bg-sky-600 group-hover:text-white">
                      <item.icon size={24} />
                    </span>
                    <span className="rounded-full border border-sky-100 bg-sky-50/80 px-3 py-1 text-xs font-bold text-sky-700">
                      {item.weight}
                    </span>
                  </div>

                  <p className="mt-6 text-xs font-bold uppercase tracking-wider text-slate-400">
                    {item.category}
                  </p>

                  <h3 className="mt-1.5 text-xl font-bold text-slate-900 sm:text-2xl">
                    {item.title}
                  </h3>

                  <p className="mt-3 text-sm leading-relaxed text-slate-600">
                    {item.text}
                  </p>
                </div>

                <div className="mt-6 pt-2">
                  <Link
                    to="/assessment"
                    className="inline-flex items-center gap-1.5 text-sm font-bold text-sky-600 transition-colors hover:text-sky-700"
                  >
                    <span>{item.actionText}</span>
                    <ArrowRight
                      size={16}
                      className="transition-transform group-hover:translate-x-1"
                    />
                  </Link>
                </div>
              </Card>
            ))}
          </div>
        </PageContainer>
      </section>

      {/* Section 3: Explainable AI & Capabilities Showcase */}
      <section className="py-12 sm:py-16">
        <PageContainer>
          <div className="rounded-3xl border border-slate-200/90 bg-white/70 p-8 shadow-xl shadow-sky-950/5 backdrop-blur-2xl sm:p-12 lg:p-16">
            <div className="grid items-center gap-10 lg:grid-cols-12 lg:gap-14">
              {/* Left Column */}
              <div className="lg:col-span-5">
                <h2 className="text-3xl font-black leading-tight tracking-tight text-slate-900 sm:text-4xl">
                  AI gợi ý minh bạch.
                  <span className="mt-1 block text-sky-600">
                    Bạn là người quyết định.
                  </span>
                </h2>

                <p className="mt-4 text-base leading-relaxed text-slate-600">
                  Không hộp đen phán đoán, không thiên vị cảm tính. Từng đề xuất
                  ngành học đều giải trình rõ lý do, đối chiếu tổ hợp điểm thực
                  tế và phân tích kỹ năng cụ thể để bạn tự tin ra quyết định.
                </p>

                <div className="mt-8">
                  <Link to="/assessment">
                    <Button size="lg" icon={Sparkles}>
                      Khám phá ngành phù hợp
                    </Button>
                  </Link>
                </div>
              </div>

              {/* Right Column: 4 Capabilities Grid */}
              <div className="grid gap-4 sm:grid-cols-2 lg:col-span-7">
                {capabilities.map((cap) => {
                  const capTitle =
                    cap.id === "catalog"
                      ? `${majorCountText} ${cap.title}`
                      : cap.title
                  return (
                    <div
                      key={cap.id}
                      className="group rounded-2xl border border-slate-200/80 bg-white/90 p-5 shadow-xs transition-all duration-200 hover:-translate-y-0.5 hover:border-sky-300 hover:shadow-md hover:shadow-sky-500/5 sm:p-6"
                    >
                      <span className="grid size-11 place-items-center rounded-xl border border-sky-100 bg-sky-50 text-sky-600 transition-colors group-hover:bg-sky-600 group-hover:text-white">
                        <cap.icon size={22} />
                      </span>
                      <h3 className="mt-4 text-base font-bold text-slate-900">
                        {capTitle}
                      </h3>
                      <p className="mt-1.5 text-xs sm:text-sm leading-relaxed text-slate-500">
                        {cap.desc}
                      </p>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        </PageContainer>
      </section>
    </div>
  )
}
