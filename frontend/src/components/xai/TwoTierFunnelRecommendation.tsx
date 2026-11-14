import { AnimatePresence, motion } from "framer-motion"
import {
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Compass,
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
}

export function TwoTierFunnelRecommendation({
  funnelData,
  isLoading = false,
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

  return (
    <div className="space-y-6">
      {/* TIER 1 SELECTOR: Top 3 Fields */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-sky-700">
            <Layers size={15} />
            <span>Lĩnh vực phù hợp</span>
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

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {fields.map((field, idx) => {
            const isPrimary = selectedFieldIndex === idx

            return (
              <button
                key={field.field_name}
                type="button"
                onClick={() => setSelectedFieldIndex(idx)}
                className={`relative flex flex-col justify-between rounded-2xl border p-4 text-left transition-all duration-200 sm:rounded-3xl ${
                  isPrimary
                    ? "border-sky-500/80 bg-white shadow-md shadow-sky-600/10 ring-2 ring-sky-500/20"
                    : "border-slate-200/85 bg-white/75 hover:border-sky-300 hover:bg-white"
                }`}
              >
                <div className="mb-2.5 flex items-center justify-between gap-2">
                  <span className="text-2xl">{field.icon || "🎓"}</span>
                  <span className="text-2xl font-black tabular-nums text-sky-600">
                    {field.match}%
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
                    ({fieldSection.match}%)
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
                    <Card className="group overflow-hidden rounded-2xl p-5 sm:rounded-3xl sm:p-6">
                      <div className="flex items-start gap-4">
                        {/* Rank Badge */}
                        <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-sky-600 text-sm font-bold text-white shadow-xs">
                          #{globalRank}
                        </span>

                        <div className="min-w-0 flex-1">
                          {/* Header: Title + Match % */}
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <h4 className="text-base font-bold text-slate-900 transition-colors group-hover:text-sky-700 sm:text-xl">
                                {major.name}
                              </h4>
                              {/* Primary Essential Badges */}
                              <div className="mt-2 flex flex-wrap items-center gap-2">
                                <FeasibilityBadge
                                  value={major.feasibility}
                                  label={major.feasibility_label}
                                />
                                <TrendBadge
                                  tier={major.trend_tier}
                                  isTrending={major.is_trending}
                                  reason={major.trend_reason}
                                />
                                <span className="rounded-full border border-slate-200/90 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-600">
                                  Mã {major.code}
                                </span>
                              </div>
                            </div>

                            <div className="text-right shrink-0">
                              <span className="block text-3xl font-black tabular-nums text-sky-600 sm:text-4xl">
                                {major.match}%
                              </span>
                              <span className="block text-[11px] font-semibold text-slate-400">
                                Độ tương thích
                              </span>
                            </div>
                          </div>

                          {/* 3 Pillars Score Breakdown */}
                          {major.fit && (
                            <div className="mt-4 grid grid-cols-3 gap-2.5 rounded-2xl border border-slate-200/80 bg-white/70 p-3.5 sm:gap-4 sm:p-4">
                              <div>
                                <div className="mb-1.5 flex justify-between text-xs font-semibold text-slate-600">
                                  <span>Sở thích</span>
                                  <span className="font-bold tabular-nums text-sky-700">
                                    {major.fit.interest}%
                                  </span>
                                </div>
                                <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                                  <motion.div
                                    className="h-full rounded-full bg-sky-600"
                                    initial={{ width: 0 }}
                                    animate={{ width: `${major.fit.interest}%` }}
                                    transition={{ duration: 0.4, ease: "easeOut" }}
                                  />
                                </div>
                              </div>

                              <div>
                                <div className="mb-1.5 flex justify-between text-xs font-semibold text-slate-600">
                                  <span>Học lực</span>
                                  <span className="font-bold tabular-nums text-sky-700">
                                    {major.fit.academic}%
                                  </span>
                                </div>
                                <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                                  <motion.div
                                    className="h-full rounded-full bg-sky-500"
                                    initial={{ width: 0 }}
                                    animate={{ width: `${major.fit.academic}%` }}
                                    transition={{ duration: 0.4, ease: "easeOut" }}
                                  />
                                </div>
                              </div>

                              <div>
                                <div className="mb-1.5 flex justify-between text-xs font-semibold text-slate-600">
                                  <span>Nhận thức</span>
                                  <span className="font-bold tabular-nums text-cyan-700">
                                    {major.fit.cognitive}%
                                  </span>
                                </div>
                                <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                                  <motion.div
                                    className="h-full rounded-full bg-cyan-500"
                                    initial={{ width: 0 }}
                                    animate={{ width: `${major.fit.cognitive}%` }}
                                    transition={{ duration: 0.4, ease: "easeOut" }}
                                  />
                                </div>
                              </div>
                            </div>
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
                              <span>Khám phá chi tiết & lộ trình</span>
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
