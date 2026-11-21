import { AnimatePresence, motion } from "framer-motion"
import {
  ChevronDown,
  ChevronRight,
  ChevronUp,
  GraduationCap,
  Layers,
  Sparkles,
  Target,
} from "lucide-react"
import { useState } from "react"
import { Link } from "react-router"
import type { FunnelRecommendationData, Major } from "../../types/major"
import { formatBlockWithSubjects } from "../../utils"
import { Card } from "../common/Card"
import { FeasibilityBadge } from "./FeasibilityBadge"
import { TrendBadge } from "./TrendBadge"

interface TwoTierFunnelProps {
  funnelData: FunnelRecommendationData
  isLoading?: boolean
  activeGradeLevel?: string
  activeGender?: string
  weightsApplied?: {
    w_riasec?: number
    w_academic?: number
    w_preference?: number
  }
}

export function TwoTierFunnelRecommendation({
  funnelData,
  isLoading = false,
  activeGradeLevel,
  activeGender,
  weightsApplied,
}: TwoTierFunnelProps) {
  const fields = funnelData.tier1_fields || []
  const [selectedFieldIndex, setSelectedFieldIndex] = useState<number | "ALL">(
    0,
  )
  const [expandedMajorIds, setExpandedMajorIds] = useState<Record<string, boolean>>({})

  const toggleMajorDetails = (id: string) => {
    setExpandedMajorIds((prev) => ({
      ...prev,
      [id]: !prev[id],
    }))
  }

  if (isLoading) {
    return (
      <div className="space-y-5 animate-pulse">
        <div>
          <div className="mb-3 flex items-center justify-between">
            <div className="h-5 w-36 rounded-lg bg-sky-100" />
            <div className="h-5 w-20 rounded-lg bg-slate-100" />
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="rounded-3xl border border-slate-200/80 bg-white/60 p-4"
              >
                <div className="mb-2 flex items-center justify-between">
                  <div className="size-8 rounded-xl bg-slate-200" />
                  <div className="h-6 w-12 rounded-lg bg-sky-100" />
                </div>
                <div className="h-4 w-28 rounded-md bg-slate-200" />
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-3 pt-2">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="rounded-3xl border border-slate-200/80 bg-white/70 p-6"
            >
              <div className="flex gap-4">
                <div className="size-11 rounded-2xl bg-slate-200" />
                <div className="flex-1 space-y-2.5">
                  <div className="h-5 w-48 rounded-md bg-slate-200" />
                  <div className="h-4 w-72 rounded-md bg-slate-100" />
                  <div className="h-7 w-full rounded-xl bg-slate-100" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (fields.length === 0) {
    return (
      <div className="rounded-3xl border border-dashed border-slate-200/90 bg-white/70 p-8 text-center sm:p-12">
        <div className="mx-auto mb-3.5 grid size-13 place-items-center rounded-2xl bg-sky-50 text-sky-600">
          <Layers className="size-7" />
        </div>
        <h4 className="text-base font-bold text-slate-800">
          Chưa có dữ liệu đề xuất ngành
        </h4>
        <p className="mx-auto mt-1.5 max-w-md text-sm text-slate-500">
          Hệ thống sẽ tổng hợp hồ sơ 3 trụ cột (Sở thích, Học lực, Nhận thức) và đề xuất các nhóm ngành phù hợp nhất cho bạn.
        </p>
      </div>
    )
  }

  const displayedFields =
    selectedFieldIndex === "ALL"
      ? fields
      : [fields[selectedFieldIndex] || fields[0]].filter(Boolean)

  const grade = activeGradeLevel?.trim() || ""
  const gender = activeGender?.trim() || ""
  const stage = grade.includes("10")
    ? { label: "Định hướng sớm & tích lũy — Lớp 10", reason: "khám phá nhiều hướng ngành, tìm hiểu sở thích và xây nền tảng môn học; bạn còn thời gian trải nghiệm trước khi chốt lựa chọn tuyển sinh" }
    : grade.includes("11")
      ? { label: "Thu hẹp trọng tâm — Lớp 11", reason: "thu hẹp nhóm ngành theo sở thích và các môn học thế mạnh, đồng thời bổ sung kiến thức cho những hướng bạn muốn theo đuổi" }
      : grade.includes("12")
        ? { label: "Ưu tiên đối chiếu tuyển sinh — Lớp 12", reason: "đối chiếu học lực hiện tại với tổ hợp môn và điều kiện tuyển sinh tham chiếu, giúp phân biệt lựa chọn vừa sức và lựa chọn cần cải thiện" }
        : /tốt nghiệp|tot nghiep/i.test(grade)
          ? { label: "Hướng học tập & nghề nghiệp thực tế", reason: "đối chiếu học lực hiện có với các chương trình đào tạo và hướng ứng dụng, thực hành phù hợp mục tiêu nghề nghiệp" }
          : null
  const profileIntroduction = stage
    ? `Vì bạn ${/tốt nghiệp|tot nghiep/i.test(grade) ? "đã tốt nghiệp THPT" : `đang học ${grade.toLocaleLowerCase("vi-VN")}`}${gender ? ` và hồ sơ ghi nhận giới tính ${gender.toLocaleLowerCase("vi-VN")}` : ""}, hệ thống ưu tiên đề xuất để ${stage.reason}.`
    : `Hồ sơ chưa có khối lớp${gender ? ` (giới tính đã ghi nhận: ${gender})` : " và giới tính"}. Bạn hãy cập nhật hồ sơ cá nhân để hệ thống giải thích đề xuất theo đúng thông tin của bạn.`
  const genderExplanation = gender === "Nam"
    ? "Với thông tin giới tính nam, hệ thống có thể bổ sung gợi ý khám phá Giáo dục/Y tế khi phù hợp sở thích của bạn."
    : gender === "Nữ"
      ? "Với thông tin giới tính nữ, hệ thống có thể mở rộng gợi ý STEM/Công nghệ khi phù hợp sở thích hoặc học lực của bạn."
      : gender
        ? "Thông tin giới tính được dùng để bổ sung góc nhìn về cơ hội khám phá và môi trường học tập đa dạng."
        : stage ? "Hồ sơ chưa có giới tính; bạn có thể bổ sung trong hồ sơ cá nhân. Hệ thống chưa áp dụng gợi ý mở rộng theo giới tính." : ""
  const hasAppliedWeights = stage && [weightsApplied?.w_riasec, weightsApplied?.w_academic, weightsApplied?.w_preference]
    .every(value => typeof value === "number" && Number.isFinite(value))
  const percent = (value: number | undefined) => ((value || 0) * 100).toLocaleString("vi-VN", { maximumFractionDigits: 1 })

  return (
    <div className="space-y-6">
      <section aria-label="Giải thích đề xuất theo hồ sơ" data-testid="profile-recommendation-context" className="rounded-3xl border border-sky-200/80 bg-white/80 p-4 shadow-xs backdrop-blur-xl sm:p-5">
        <div className="space-y-2.5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-sky-100/90 px-2.5 py-0.5 text-[11px] font-extrabold uppercase tracking-wider text-sky-800">
              <Sparkles size={12} className="text-sky-600" />
              Đề xuất theo hồ sơ của bạn
            </span>
            {stage && <span className="text-xs font-bold text-slate-800">{stage.label}</span>}
          </div>
          <p className="text-sm leading-relaxed text-slate-700">{profileIntroduction}</p>
          {genderExplanation && <p className="text-xs leading-relaxed text-slate-600">{genderExplanation} Giới tính không giới hạn ngành học hay quyết định năng lực của bạn.</p>}
          {hasAppliedWeights && (
            <p className="text-xs text-slate-600">
              Trọng số đang áp dụng: <strong className="font-semibold text-sky-700">{percent(weightsApplied?.w_riasec)}% Sở thích</strong>
              {" · "}<strong className="font-semibold text-sky-700">{percent(weightsApplied?.w_academic)}% Học lực</strong>
              {" · "}<strong className="font-semibold text-cyan-700">{percent(weightsApplied?.w_preference)}% Tự khai</strong>
            </p>
          )}
        </div>
      </section>

      <p className="text-xs leading-relaxed text-slate-500">Điểm gợi ý được tính theo quy tắc tham khảo, không phải xác suất trúng tuyển. Dấu — là chưa đủ dữ liệu; phong cách tự khai không đo mức thành thạo kỹ năng.</p>
      {/* TIER 1 SELECTOR: Top 3 Fields */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-sky-700">
            <Layers size={15} />
            <span>Lĩnh vực để tìm hiểu</span>
          </p>
          <button
            type="button"
            onClick={() =>
              setSelectedFieldIndex(selectedFieldIndex === "ALL" ? 0 : "ALL")
            }
            className="text-xs font-semibold text-sky-600 transition hover:text-sky-800"
          >
            {selectedFieldIndex === "ALL" ? "Thu gọn về Top 1" : "Xem tất cả"}
          </button>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3">
          {fields.map((field, idx) => {
            const isPrimary = selectedFieldIndex === idx

            return (
              <button
                key={field.field_name}
                type="button"
                onClick={() => setSelectedFieldIndex(idx)}
                className={`relative flex min-w-0 flex-col justify-between rounded-2xl border p-4 text-left transition-all duration-200 sm:rounded-3xl ${
                  isPrimary
                    ? "border-sky-500/80 bg-white shadow-md shadow-sky-600/10 ring-2 ring-sky-500/20"
                    : "border-slate-200/85 bg-white/75 hover:border-sky-300 hover:bg-white"
                }`}
              >
                <div className="mb-2.5 flex items-center justify-between gap-2">
                  <span className="shrink-0 text-xl sm:text-2xl">{field.icon || "🎓"}</span>
                  <span className="whitespace-nowrap text-xl font-black tabular-nums text-sky-600 sm:text-2xl">
                    {field.match == null ? "—" : `${field.match}/100`}
                  </span>
                </div>
                <h4 className="line-clamp-2 min-h-[2.5rem] text-sm font-bold leading-snug text-slate-900">
                  {field.field_name}
                </h4>
              </button>
            )
          })}
        </div>
      </div>

      {/* TIER 2: Specific Majors in selected field(s) */}
      <div className="space-y-4 pt-1">
        <div className="flex items-center justify-between">
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-500">
            <Target size={15} className="text-sky-600" />
            <span>Ngành đào tạo đề xuất</span>
          </p>
        </div>

        {displayedFields.map((fieldSection, fIdx) => (
          <div key={fieldSection.field_name} className="space-y-3.5">
            {selectedFieldIndex === "ALL" && (
              <div className="flex items-center gap-2 pt-2">
                <span className="text-lg">{fieldSection.icon || "🎓"}</span>
                <h3 className="text-sm font-bold text-slate-800">
                  {fieldSection.field_name}{" "}
                  <span className="font-semibold text-sky-600">
                    ({fieldSection.match == null ? "chưa đủ dữ liệu" : `${fieldSection.match}/100`})
                  </span>
                </h3>
              </div>
            )}

            <div className="space-y-3.5">
              {(fieldSection.majors || []).map((major: Major, mIdx: number) => {
                const globalRank = `${fIdx + 1}.${mIdx + 1}`
                const majorKey = String(major.id || major.code)
                const isExpanded = !!expandedMajorIds[majorKey]

                const hasExtraDetails =
                  !!major.admission_tactic ||
                  !!major.nudge_badge ||
                  (major.constraint_violations && major.constraint_violations.length > 0) ||
                  !!major.advisory_note ||
                  (!!major.best_matching_block && major.best_block_score != null)

                return (
                  <motion.div
                    key={majorKey}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.22, delay: mIdx * 0.03 }}
                  >
                    <Card className="group overflow-hidden rounded-2xl p-4 sm:rounded-3xl sm:p-5 xl:p-6">
                      <div className="flex flex-col gap-3">
                        {/* Header: Rank + Title + Score */}
                        <div className="flex items-start gap-3 sm:gap-4">
                          <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-sky-600 text-xs font-bold text-white shadow-xs sm:size-11 sm:rounded-2xl sm:text-sm">
                            #{globalRank}
                          </span>

                          <div className="flex min-w-0 flex-1 items-start justify-between gap-2.5 sm:gap-3">
                            <h4 className="min-w-0 flex-1 break-words text-base font-bold leading-snug text-slate-900 transition-colors group-hover:text-sky-700 sm:text-lg xl:text-xl">
                              {major.name}
                            </h4>

                            <div className="shrink-0 text-right">
                              <span className="block whitespace-nowrap text-2xl font-black tabular-nums text-sky-600 sm:text-3xl xl:text-4xl">
                                {major.match == null ? "—" : `${major.match}/100`}
                              </span>
                              <span className="block text-[10px] font-semibold text-slate-400 sm:text-[11px]">
                                Điểm gợi ý
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="min-w-0 sm:pl-[3.75rem]">
                          {/* Primary Essential Badges */}
                          <div className="flex max-w-full flex-wrap items-center gap-1.5 sm:gap-2">
                            <FeasibilityBadge
                              readiness={major.readiness}
                              value={major.feasibility}
                              label={major.feasibility_label}
                            />
                            {major.best_matching_block &&
                              major.best_block_score != null && (
                                <span className="inline-flex items-center gap-1 rounded-full border border-sky-200/90 bg-sky-50/90 px-2.5 py-1 text-xs font-semibold text-sky-800">
                                  <GraduationCap
                                    size={13}
                                    className="text-sky-600"
                                  />
                                  {formatBlockWithSubjects(
                                    major.best_matching_block,
                                    {
                                      short: true,
                                      includePrefix: false,
                                    },
                                  )}
                                  : {major.best_block_score}đ
                                  {major.benchmark_cutoff
                                    ? ` (Chuẩn ~${major.benchmark_cutoff}đ)`
                                    : ""}
                                </span>
                              )}
                            {major.admission_tactic &&
                              major.admission_tactic !==
                                "Đối chiếu phương thức tuyển sinh" && (
                                <span
                                  className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ${
                                    major.admission_tactic.includes("NV1-2")
                                      ? "border border-amber-200 bg-amber-50 text-amber-800"
                                      : major.admission_tactic.includes(
                                            "NV6+",
                                          )
                                        ? "border border-emerald-200 bg-emerald-50 text-emerald-800"
                                        : "border border-sky-200 bg-sky-50/80 text-sky-800"
                                  }`}
                                >
                                  <Target size={12} />
                                  {major.admission_tactic}
                                </span>
                              )}
                            {major.nudge_badge && (
                              <span className="inline-flex items-center gap-1 rounded-full border border-cyan-200 bg-cyan-50/90 px-2.5 py-1 text-xs font-semibold text-cyan-800">
                                <Sparkles
                                  size={12}
                                  className="text-cyan-600"
                                />
                                {major.nudge_badge}
                              </span>
                            )}
                            <TrendBadge
                              tier={major.trend_tier}
                              isTrending={major.is_trending}
                              reason={major.trend_reason}
                            />
                            <span className="rounded-full border border-slate-200/90 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-600">
                              Mã {major.code}
                            </span>
                          </div>

                          {/* 3 Pillars Score Breakdown */}
                          {major.fit && (
                            <div className="mt-4 grid grid-cols-1 gap-3 rounded-2xl border border-slate-200/80 bg-white/70 p-3.5 sm:grid-cols-3 sm:gap-4 sm:p-4">
                              <div>
                                <div className="mb-1.5 flex justify-between text-xs font-semibold text-slate-600">
                                  <span>Sở thích</span>
                                  <span className="font-bold tabular-nums text-sky-700">
                                    {major.fit.interest == null ? "—" : `${major.fit.interest}/100`}
                                  </span>
                                </div>
                                <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                                  <motion.div
                                    className="h-full rounded-full bg-sky-600"
                                    initial={{ width: 0 }}
                                    animate={{ width: `${major.fit.interest ?? 0}%` }}
                                    transition={{ duration: 0.4, ease: "easeOut" }}
                                  />
                                </div>
                              </div>

                              <div>
                                <div className="mb-1.5 flex justify-between text-xs font-semibold text-slate-600">
                                  <span>Học lực</span>
                                  <span className="font-bold tabular-nums text-sky-700">
                                    {major.fit.academic == null ? "—" : `${major.fit.academic}/100`}
                                  </span>
                                </div>
                                <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                                  <motion.div
                                    className="h-full rounded-full bg-sky-500"
                                    initial={{ width: 0 }}
                                    animate={{ width: `${major.fit.academic ?? 0}%` }}
                                    transition={{ duration: 0.4, ease: "easeOut" }}
                                  />
                                </div>
                              </div>

                              <div>
                                <div className="mb-1.5 flex justify-between text-xs font-semibold text-slate-600">
                                  <span>Tự khai</span>
                                  <span className="font-bold tabular-nums text-cyan-700">
                                    {major.fit.cognitive == null ? "—" : `${major.fit.cognitive}/100`}
                                  </span>
                                </div>
                                <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                                  <motion.div
                                    className="h-full rounded-full bg-cyan-500"
                                    initial={{ width: 0 }}
                                    animate={{ width: `${major.fit.cognitive ?? 0}%` }}
                                    transition={{ duration: 0.4, ease: "easeOut" }}
                                  />
                                </div>
                              </div>
                            </div>
                          )}

                          {/* Personalized XAI Explanation by Grade Level & Gender */}
                          {major.explanation && (
                            <p className="mt-3 rounded-2xl border border-slate-200/70 bg-slate-50/70 px-3.5 py-2.5 text-xs leading-relaxed text-slate-700">
                              {major.explanation}
                            </p>
                          )}

                          {/* Progressive Disclosure: Collapsible Admissions & Strategy Section */}
                          {hasExtraDetails && (
                            <div className="mt-3">
                              <AnimatePresence initial={false}>
                                {isExpanded && (
                                  <motion.div
                                    initial={{ opacity: 0, height: 0 }}
                                    animate={{ opacity: 1, height: "auto" }}
                                    exit={{ opacity: 0, height: 0 }}
                                    transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
                                    className="overflow-hidden"
                                  >
                                    <div className="space-y-2 rounded-2xl border border-sky-100 bg-sky-50/60 p-3.5 text-xs text-slate-700 sm:p-4">
                                      <div className="flex flex-wrap items-center gap-2">
                                        {major.best_matching_block && major.best_block_score != null && (
                                          <span className="inline-flex items-center gap-1 rounded-lg border border-sky-200 bg-white px-2.5 py-1 font-semibold text-sky-800">
                                            <GraduationCap size={14} className="text-sky-600" />
                                            {formatBlockWithSubjects(major.best_matching_block, {
                                              short: true,
                                              includePrefix: false,
                                            })}
                                            : {major.best_block_score}đ
                                            {major.benchmark_cutoff
                                              ? ` (Điểm sàn ~${major.benchmark_cutoff}đ)`
                                              : ""}
                                          </span>
                                        )}

                                        {major.admission_tactic && (
                                          <span
                                            className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1 font-semibold ${
                                              major.admission_tactic.includes("NV1-2")
                                                ? "border border-amber-200 bg-amber-50 text-amber-800"
                                                : major.admission_tactic.includes("NV6+")
                                                ? "border border-emerald-200 bg-emerald-50 text-emerald-800"
                                                : "border border-sky-200 bg-white text-sky-800"
                                            }`}
                                          >
                                            <Target size={13} />
                                            {major.admission_tactic}
                                          </span>
                                        )}

                                        {major.nudge_badge && (
                                          <span className="inline-flex items-center gap-1 rounded-lg border border-sky-200 bg-white px-2.5 py-1 font-semibold text-sky-700">
                                            <Sparkles size={13} className="text-sky-600" />
                                            {major.nudge_badge}
                                          </span>
                                        )}
                                      </div>

                                      {major.constraint_violations &&
                                        major.constraint_violations.length > 0 && (
                                          <p className="rounded-xl border border-rose-200/80 bg-rose-50 px-3 py-2 font-medium text-rose-700">
                                            {major.constraint_violations[0]}
                                          </p>
                                        )}

                                      {major.advisory_note && (
                                        <p className="rounded-xl border border-sky-200/70 bg-white px-3 py-2 font-medium leading-relaxed text-slate-700">
                                          <strong className="font-bold text-sky-800">
                                            Ghi chú định hướng:
                                          </strong>{" "}
                                          {major.advisory_note}
                                        </p>
                                      )}
                                    </div>
                                  </motion.div>
                                )}
                              </AnimatePresence>
                            </div>
                          )}

                          {/* Footer Actions: Toggle Details & Major Link */}
                          <div className="mt-3.5 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3">
                            {hasExtraDetails ? (
                              <button
                                type="button"
                                onClick={() => toggleMajorDetails(majorKey)}
                                className="inline-flex items-center gap-1 text-xs font-semibold text-slate-500 transition hover:text-sky-700"
                              >
                                <span>
                                  {isExpanded ? "Ẩn bớt thông tin" : "Chi tiết tuyển sinh & ghi chú"}
                                </span>
                                {isExpanded ? (
                                  <ChevronUp size={14} />
                                ) : (
                                  <ChevronDown size={14} />
                                )}
                              </button>
                            ) : (
                              <div />
                            )}

                            <Link
                              to={`/majors/${major.id || major.code}`}
                              className="inline-flex items-center gap-1 text-xs font-bold text-sky-600 transition hover:gap-1.5 hover:text-sky-800"
                            >
                              <span>Xem chi tiết ngành</span>
                              <ChevronRight size={15} />
                            </Link>
                          </div>
                        </div>
                      </div>
                    </Card>
                  </motion.div>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
