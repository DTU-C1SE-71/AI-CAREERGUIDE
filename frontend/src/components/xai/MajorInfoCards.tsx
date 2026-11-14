import {
  BookOpenCheck,
  BriefcaseBusiness,
  GraduationCap,
  Loader2,
} from "lucide-react"
import { Card } from "../common/Card"
import type { CareerPosition, TrainingContent } from "../../types/insight"

interface MajorInfoCardsProps {
  training: TrainingContent | null
  careers: CareerPosition[]
  subjectBlocks: string
  loading?: boolean
}

function InfoCard({
  icon,
  title,
  loading,
  children,
}: {
  icon: React.ReactNode
  title: string
  loading?: boolean
  children: React.ReactNode
}) {
  return (
    <Card className="rounded-2xl p-5 sm:rounded-3xl sm:p-6">
      <div className="flex gap-3.5">
        <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-sky-50 text-sky-600">
          {icon}
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="flex items-center gap-2 text-base font-bold text-slate-900">
            {title}
            {loading && <Loader2 size={14} className="animate-spin text-sky-600" />}
          </h3>
          <div className="mt-2 text-sm leading-relaxed text-slate-600">{children}</div>
        </div>
      </div>
    </Card>
  )
}

function BulletList({ items, max = 5 }: { items: string[]; max?: number }) {
  return (
    <ul className="mt-2 space-y-1.5">
      {items.slice(0, max).map((item) => (
        <li key={item} className="flex items-start gap-2 text-xs sm:text-sm text-slate-700">
          <span className="mt-2 size-1.5 shrink-0 rounded-full bg-sky-500" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  )
}

export function MajorInfoCards({
  training,
  careers,
  subjectBlocks,
  loading = false,
}: MajorInfoCardsProps) {
  return (
    <div className="space-y-4">
      <InfoCard
        icon={<GraduationCap size={20} />}
        title="Chương trình đào tạo"
        loading={loading}
      >
        {training ? (
          <>
            <p className="text-xs sm:text-sm text-slate-600">{training.overview}</p>
            {training.core_knowledge && training.core_knowledge.length > 0 && (
              <>
                <p className="mt-3 font-bold text-slate-800 text-xs sm:text-sm">
                  Kiến thức cốt lõi
                </p>
                <BulletList items={training.core_knowledge} />
              </>
            )}
            {training.practical_skills && training.practical_skills.length > 0 && (
              <>
                <p className="mt-3 font-bold text-slate-800 text-xs sm:text-sm">
                  Kỹ năng thực hành
                </p>
                <BulletList items={training.practical_skills} />
              </>
            )}
            {training.study_duration && (
              <p className="mt-3 text-xs font-semibold text-slate-500">
                Thời gian đào tạo: {training.study_duration}
              </p>
            )}
          </>
        ) : (
          <p className="text-xs sm:text-sm text-slate-500">
            Chương trình đào tạo kết hợp lý thuyết nền tảng, thực hành chuyên sâu và dự án hướng nghiệp.
          </p>
        )}
      </InfoCard>

      <InfoCard
        icon={<BriefcaseBusiness size={20} />}
        title="Vị trí nghề nghiệp"
        loading={loading}
      >
        {careers.length > 0 ? (
          <ul className="mt-1 space-y-2">
            {careers.slice(0, 5).map((career) => (
              <li key={career.title} className="rounded-xl border border-slate-100 bg-white/60 p-2.5">
                <span className="font-bold text-slate-800 text-xs sm:text-sm">
                  {career.title}
                </span>
                {career.description ? (
                  <span className="mt-0.5 block text-xs text-slate-600">
                    {career.description}
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs sm:text-sm text-slate-500">
            Kỹ sư chuyên môn, Chuyên viên phân tích, Quản lý dự án, R&D.
          </p>
        )}
      </InfoCard>

      <InfoCard icon={<BookOpenCheck size={20} />} title="Tổ hợp môn xét tuyển">
        <p className="text-xs sm:text-sm font-medium text-slate-700">{subjectBlocks}</p>
      </InfoCard>
    </div>
  )
}
