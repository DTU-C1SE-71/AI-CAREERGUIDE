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
    <Card className="rounded-3xl p-5">
      <div className="flex gap-3">
        <span className="grid size-10 shrink-0 place-items-center rounded-2xl bg-sky-500/12 text-sky-600">
          {icon}
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="flex items-center gap-2 text-sm font-extrabold text-slate-900">
            {title}
            {loading && <Loader2 size={13} className="animate-spin text-sky-500" />}
          </h3>
          <div className="mt-1 text-xs leading-5 text-slate-600">{children}</div>
        </div>
      </div>
    </Card>
  )
}

function BulletList({ items, max = 4 }: { items: string[]; max?: number }) {
  return (
    <ul className="mt-1.5 space-y-1">
      {items.slice(0, max).map((item) => (
        <li key={item} className="flex gap-1.5">
          <span className="mt-1.5 size-1 shrink-0 rounded-full bg-sky-400" />
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
    <>
      <InfoCard
        icon={<GraduationCap size={19} />}
        title="Nội dung đào tạo"
        loading={loading}
      >
        {training ? (
          <>
            <p>{training.overview}</p>
            {training.core_knowledge.length > 0 && (
              <>
                <p className="mt-2 font-bold text-slate-700">Kiến thức cốt lõi</p>
                <BulletList items={training.core_knowledge} />
              </>
            )}
            {training.practical_skills.length > 0 && (
              <>
                <p className="mt-2 font-bold text-slate-700">Kỹ năng thực hành</p>
                <BulletList items={training.practical_skills} />
              </>
            )}
            {training.study_duration && (
              <p className="mt-2 text-[11px] font-semibold text-slate-500">
                Thời gian đào tạo: {training.study_duration}
              </p>
            )}
          </>
        ) : (
          <p>
            Chương trình đào tạo kết hợp kiến thức nền tảng, kỹ năng thực hành và dự
            án thực tế.
          </p>
        )}
      </InfoCard>

      <InfoCard
        icon={<BriefcaseBusiness size={19} />}
        title="Vị trí nghề nghiệp"
        loading={loading}
      >
        {careers.length > 0 ? (
          <ul className="mt-0.5 space-y-1.5">
            {careers.slice(0, 6).map((career) => (
              <li key={career.title}>
                <span className="font-bold text-slate-700">{career.title}</span>
                {career.description ? (
                  <span className="block text-slate-600">{career.description}</span>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p>Kỹ sư chuyên môn, Chuyên viên phân tích, R&D, Quản lý dự án.</p>
        )}
      </InfoCard>

      <InfoCard icon={<BookOpenCheck size={19} />} title="Tổ hợp xét tuyển">
        <p>{subjectBlocks}</p>
      </InfoCard>
    </>
  )
}
