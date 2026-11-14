import { AnimatePresence, motion } from "framer-motion"
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
import { useEffect, useState } from "react"
import { Link } from "react-router"
import { Button } from "../components/common/Button"
import { Card } from "../components/common/Card"
import { PageContainer } from "../components/layout/PageContainer"

const pillars = [
  {
    icon: Compass,
    weight: "45% trọng số",
    category: "Sở thích nghề nghiệp",
    title: "Holland RIASEC",
    text: "30 câu hỏi thực tế định vị 6 nhóm xu hướng nghề nghiệp: Kỹ thuật, Nghiên cứu, Nghệ thuật, Xã hội, Quản lý và Nghiệp vụ.",
    actionText: "Làm bài trắc nghiệm RIASEC",
  },
  {
    icon: BarChart3,
    weight: "35% trọng số",
    category: "Năng lực học tập",
    title: "Chuẩn hóa Z-Score",
    text: "Đối chiếu điểm số học bạ và thi cử theo các tổ hợp môn xét tuyển, chuẩn hóa độ lệch điểm để dự báo chính xác cơ hội trúng tuyển.",
    actionText: "Nhập điểm và kiểm tra",
  },
  {
    icon: Brain,
    weight: "20% trọng số",
    category: "Phong cách nhận thức",
    title: "Tư duy & Thích ứng",
    text: "8 chiều đánh giá phương thức tiếp thu, ra quyết định và thích ứng với môi trường học thuật đại học lẫn thị trường việc làm.",
    actionText: "Khám phá phong cách",
  },
]

const heroImages = [
  {
    src: "https://images.unsplash.com/photo-1598981457915-aea220950616?crop=entropy&cs=tinysrgb&fit=crop&fm=jpg&q=85&w=1200",
    alt: "Học sinh đang tập trung học tập",
    label: "Khám phá tiềm năng",
  },
  {
    src: "https://images.unsplash.com/photo-1758270705290-62b6294dd044?crop=entropy&cs=tinysrgb&fit=crop&fm=jpg&q=85&w=1200",
    alt: "Nhóm sinh viên trao đổi thảo luận",
    label: "Đối chiếu dữ liệu",
  },
  {
    src: "https://images.unsplash.com/photo-1782388713336-fcb8aa6db8f0?crop=entropy&cs=tinysrgb&fit=crop&fm=jpg&q=85&w=1200",
    alt: "Sinh viên hợp tác dự án công nghệ",
    label: "Kiến tạo tương lai",
  },
]

const capabilities = [
  {
    icon: Database,
    title: "435 ngành đào tạo chuẩn hóa",
    desc: "Cập nhật đồng bộ theo danh mục đào tạo của Bộ GD&ĐT cùng xu hướng tuyển dụng thị trường lao động.",
  },
  {
    icon: Eye,
    title: "Giải thích minh bạch (XAI)",
    desc: "Bóc tách rõ ràng tỷ trọng đóng góp từ sở thích, điểm số tổ hợp và phong cách tư duy trong từng gợi ý.",
  },
  {
    icon: BookOpenCheck,
    title: "Lộ trình 4 tuần hành động",
    desc: "Kế hoạch tuần tự từ củng cố học lực môn thi đến tích lũy kỹ năng thực tế cần thiết cho ngành mục tiêu.",
  },
  {
    icon: GraduationCap,
    title: "Bản đồ trường đại học",
    desc: "Tra cứu điểm sàn, phương thức xét tuyển và cơ hội học bổng của các cơ sở đào tạo uy tín toàn quốc.",
  },
]

export function Home() {
  const [activeImage, setActiveImage] = useState(0)

  useEffect(() => {
    const timer = window.setInterval(
      () => setActiveImage((current) => (current + 1) % heroImages.length),
      4800,
    )
    return () => window.clearInterval(timer)
  }, [])

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
              Không chỉ chọn ngành.
              <span className="mt-1 block text-sky-600">
                Chọn đúng tương lai.
              </span>
            </h1>

            <p className="mt-5 max-w-xl text-base leading-relaxed text-slate-600 sm:text-lg">
              Kết nối sở thích nghề nghiệp, học lực chuẩn hóa và phong cách tư
              duy để định vị chính xác ngành học tương thích cùng lộ trình hành
              động rõ ràng.
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
              <Link to="/dashboard" className="w-full sm:w-auto">
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
                "435 ngành chuẩn hóa",
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

          {/* Right Column: Hero Visual Showcase */}
          <motion.div
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.08, duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
            className="relative lg:col-span-5"
          >
            <div className="relative h-[400px] overflow-hidden rounded-3xl border border-slate-200/90 bg-slate-900 shadow-xl shadow-sky-950/10 sm:h-[460px] lg:h-[490px] xl:h-[530px]">
              <AnimatePresence mode="popLayout">
                <motion.img
                  key={heroImages[activeImage].src}
                  src={heroImages[activeImage].src}
                  alt={heroImages[activeImage].alt}
                  initial={{ opacity: 0, scale: 1.04 }}
                  animate={{ opacity: 0.88, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.98 }}
                  transition={{
                    opacity: { duration: 0.7 },
                    scale: { duration: 4.8 },
                  }}
                  className="absolute inset-0 h-full w-full object-cover"
                />
              </AnimatePresence>

              {/* Contrast scrim */}
              <div className="absolute inset-0 bg-gradient-to-t from-slate-950/90 via-slate-950/25 to-transparent" />

              {/* Image context badge */}
              <div className="absolute left-5 top-5 rounded-full border border-white/20 bg-slate-900/60 px-3.5 py-1.5 text-xs font-bold uppercase tracking-wider text-white backdrop-blur-md">
                {heroImages[activeImage].label}
              </div>

              {/* Bottom statistics and indicators */}
              <div className="absolute bottom-0 left-0 right-0 p-6 sm:p-7 text-white">
                <div className="flex items-end justify-between">
                  <div>
                    <span className="text-3xl sm:text-4xl font-black tabular-nums tracking-tight">
                      435
                    </span>
                    <span className="ml-2 text-xs sm:text-sm font-medium text-sky-200">
                      ngành đào tạo đại học
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    {heroImages.map((image, index) => (
                      <button
                        key={image.src}
                        type="button"
                        onClick={() => setActiveImage(index)}
                        aria-label={`Xem ảnh ${index + 1}`}
                        className={`h-2 rounded-full transition-all duration-200 ${
                          activeImage === index
                            ? "w-8 bg-white"
                            : "w-2 bg-white/40 hover:bg-white/70"
                        }`}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Floating accuracy highlight badge */}
            <div className="glass-panel absolute -left-4 sm:-left-6 top-6 sm:top-8 rounded-2xl border border-slate-200/80 p-3.5 sm:p-4 shadow-lg shadow-sky-950/5">
              <div className="flex items-center gap-3">
                <span className="grid size-11 place-items-center rounded-xl bg-sky-50 text-sky-600 border border-sky-100">
                  <Target size={22} />
                </span>
                <div>
                  <p className="text-xs font-semibold text-slate-500">
                    Độ tương thích đề xuất
                  </p>
                  <p className="text-sm sm:text-base font-black text-slate-900 tabular-nums">
                    94% chuẩn xác
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
              Mô hình đánh giá 3 chiều kết hợp khoa học tâm lý học, kết quả học
              tập và phong cách nhận thức để đưa ra lựa chọn vững chắc nhất.
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
                  ngành học đều giải trình rõ lý do, đối chiếu điểm chuẩn thực
                  tế và lộ trình học tập cụ thể để bạn tự tin ra quyết định.
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
                {capabilities.map((cap) => (
                  <div
                    key={cap.title}
                    className="group rounded-2xl border border-slate-200/80 bg-white/90 p-5 shadow-xs transition-all duration-200 hover:-translate-y-0.5 hover:border-sky-300 hover:shadow-md hover:shadow-sky-500/5 sm:p-6"
                  >
                    <span className="grid size-11 place-items-center rounded-xl border border-sky-100 bg-sky-50 text-sky-600 transition-colors group-hover:bg-sky-600 group-hover:text-white">
                      <cap.icon size={22} />
                    </span>
                    <h3 className="mt-4 text-base font-bold text-slate-900">
                      {cap.title}
                    </h3>
                    <p className="mt-1.5 text-xs sm:text-sm leading-relaxed text-slate-500">
                      {cap.desc}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </PageContainer>
      </section>
    </div>
  )
}
