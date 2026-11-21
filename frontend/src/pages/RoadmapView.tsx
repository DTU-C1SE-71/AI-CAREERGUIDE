import {
  ArrowLeft,
  BookOpen,
  CheckCircle2,
  Clock3,
  Compass,
  GraduationCap,
  Sparkles,
  Target,
} from "lucide-react"
import { Link, useSearchParams } from "react-router"
import { Badge } from "../components/common/Badge"
import { PageContainer } from "../components/layout/PageContainer"

export function RoadmapView() {
  const [searchParams] = useSearchParams()
  const majorName = searchParams.get("name")?.trim() || ""

  return (
    <section className="py-6 sm:py-10 lg:py-12">
      <PageContainer size="narrow">
        <div className="mb-5">
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-2 rounded-2xl border border-white/90 bg-white/75 px-4 py-2 text-xs font-extrabold text-slate-700 shadow-xs backdrop-blur-md transition hover:bg-white hover:text-sky-700 sm:text-sm"
          >
            <ArrowLeft size={16} className="text-sky-600" />
            <span>Quay lại Khám phá ngành</span>
          </Link>
        </div>

        <div className="glass-card relative overflow-hidden rounded-3xl p-6 sm:p-10">
          <div className="pointer-events-none absolute -right-12 -top-12 size-56 rounded-full bg-sky-200/35 blur-3xl" />
          <div className="pointer-events-none absolute -bottom-16 -left-10 size-52 rounded-full bg-cyan-200/30 blur-3xl" />

          <div className="relative">
            <div className="flex flex-wrap items-center gap-2.5">
              <Badge tone="sky">
                <Clock3 size={13} />
                Lộ trình 4 tuần · Coming Soon
              </Badge>
              {majorName && (
                <span className="rounded-full border border-slate-200 bg-white/80 px-3 py-1 text-xs font-semibold text-slate-700">
                  Ngành đang xem: {majorName}
                </span>
              )}
            </div>

            <div className="mt-5 flex flex-col gap-4 sm:flex-row sm:items-start">
              <div className="grid size-14 shrink-0 place-items-center rounded-2xl bg-sky-600 text-white shadow-md shadow-sky-500/20">
                <Sparkles size={26} />
              </div>
              <div>
                <h1 className="text-2xl font-black tracking-tight text-slate-900 sm:text-3xl">
                  Lộ trình học tập 4 tuần — Coming Soon
                </h1>
                <p className="mt-2.5 max-w-2xl text-sm leading-relaxed text-slate-600 sm:text-base">
                  Tính năng lập kế hoạch học tập và rèn luyện 4 tuần cá nhân hóa đang được hoàn thiện cho phiên bản tiếp theo. Hiện tại, bạn có thể xem đầy đủ phân tích kỹ năng theo hồ sơ, đối chiếu nguyện vọng với AI và tra cứu danh mục 435 ngành đào tạo.
                </p>
              </div>
            </div>

            <div className="mt-7 grid gap-4 sm:grid-cols-3">
              {[
                {
                  icon: Target,
                  title: "Lộ trình theo khoảng trống kỹ năng",
                  desc: "Tự động chuyển đổi kỹ năng còn thiếu từ hồ sơ thành nhiệm vụ học tập theo từng tuần.",
                },
                {
                  icon: BookOpen,
                  title: "Tài liệu & bài tập chọn lọc",
                  desc: "Tổng hợp giáo trình nhập môn, bài thực hành và mini-project đúng chuẩn chương trình.",
                },
                {
                  icon: CheckCircle2,
                  title: "Theo dõi tiến độ 4 tuần",
                  desc: "Lưu trạng thái hoàn thành từng cột mốc để tự đánh giá mức độ sẵn sàng với ngành học.",
                },
              ].map((item) => {
                const Icon = item.icon
                return (
                  <div
                    key={item.title}
                    className="rounded-2xl border border-slate-200/80 bg-white/80 p-4 backdrop-blur-sm"
                  >
                    <span className="grid size-9 place-items-center rounded-xl bg-sky-50 text-sky-600">
                      <Icon size={18} />
                    </span>
                    <h2 className="mt-3 text-sm font-bold text-slate-900">
                      {item.title}
                    </h2>
                    <p className="mt-1.5 text-xs leading-relaxed text-slate-600">
                      {item.desc}
                    </p>
                  </div>
                )
              })}
            </div>

            <div className="mt-7 flex flex-wrap items-center gap-3 border-t border-slate-200/70 pt-6">
              <Link
                to="/dashboard"
                className="inline-flex items-center gap-2 rounded-2xl bg-sky-600 px-5 py-2.5 text-xs font-extrabold text-white shadow-sm transition hover:bg-sky-700 sm:text-sm"
              >
                <GraduationCap size={16} />
                <span>Xem Đề xuất &amp; Kỹ năng hồ sơ</span>
              </Link>
              <Link
                to="/majors"
                className="inline-flex items-center gap-2 rounded-2xl border border-sky-200 bg-white px-5 py-2.5 text-xs font-bold text-sky-700 transition hover:bg-sky-50 sm:text-sm"
              >
                <Compass size={16} />
                <span>Tra cứu Danh mục 435 ngành</span>
              </Link>
            </div>
          </div>
        </div>
      </PageContainer>
    </section>
  )
}
