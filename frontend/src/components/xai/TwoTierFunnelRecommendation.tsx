import { motion } from "framer-motion"
import { ChevronRight, Layers, Target } from "lucide-react"
import { useState } from "react"
import { Link } from "react-router"
import type { FunnelRecommendationData, Major } from "../../types/major"
import { Card } from "../common/Card"
import { FeasibilityBadge } from "./FeasibilityBadge"
import { TrendBadge } from "./TrendBadge"

interface TwoTierFunnelProps {
  funnelData: FunnelRecommendationData
}

export function TwoTierFunnelRecommendation({
  funnelData,
}: TwoTierFunnelProps) {
  const fields = funnelData.tier1_fields || []
  const [selectedFieldIndex, setSelectedFieldIndex] = useState<number | "ALL">(
    0,
  )

  const displayedFields =
    selectedFieldIndex === "ALL"
      ? fields
      : [fields[selectedFieldIndex] || fields[0]].filter(Boolean)

  return (
    <div className="space-y-5">
      {/* TIER 1 SELECTOR: Top 3 Fields (Liquid Glass) */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <p className="flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-widest text-sky-600">
            <Layers size={14} />
            Lĩnh vực phù hợp
          </p>
          <button
            type="button"
            onClick={() =>
              setSelectedFieldIndex(selectedFieldIndex === "ALL" ? 0 : "ALL")
            }
            className="text-xs font-bold text-sky-600 transition-colors hover:text-sky-800"
          >
            {selectedFieldIndex === "ALL" ? "Thu gọn" : "Xem tất cả"}
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
                className={`relative cursor-pointer rounded-3xl border p-4 text-left backdrop-blur-xl transition-all duration-200 ${
                  isPrimary
                    ? "border-sky-400/90 bg-white/80 shadow-[0_12px_36px_rgba(14,165,233,0.14)]"
                    : "border-white/80 bg-white/45 hover:bg-white/70"
                }`}
              >
                <div className="mb-2 flex items-center justify-between gap-1">
                  <span className="text-xl">{field.icon || "🎓"}</span>
                  <span className="text-xl font-black text-sky-600">
                    {field.match}%
                  </span>
                </div>
                <h4 className="line-clamp-1 text-xs font-extrabold text-slate-900 sm:text-sm">
                  {field.field_name}
                </h4>
              </button>
            )
          })}
        </div>
      </div>

      {/* TIER 2: Specific Majors in selected field(s) */}
      <div className="space-y-3.5 pt-1">
        <div className="flex items-center justify-between">
          <p className="flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-widest text-slate-500">
            <Target size={14} className="text-sky-600" />
            Ngành đề xuất
          </p>
        </div>

        {displayedFields.map((fieldSection, fIdx) => (
          <div key={fieldSection.field_name} className="space-y-3">
            {selectedFieldIndex === "ALL" && (
              <div className="flex items-center gap-2 pt-1">
                <span className="text-base">{fieldSection.icon || "🎓"}</span>
                <h3 className="text-xs font-black text-slate-700">
                  {fieldSection.field_name} ({fieldSection.match}%)
                </h3>
              </div>
            )}

            <div className="space-y-3">
              {(fieldSection.majors || []).map((major: Major, mIdx: number) => {
                const globalRank = `${fIdx + 1}.${mIdx + 1}`

                return (
                  <motion.div
                    key={major.id || major.code}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2, delay: mIdx * 0.04 }}
                  >
                    <Card className="group overflow-hidden rounded-3xl p-5">
                      <div className="flex gap-4">
                        <span className="grid size-10 shrink-0 place-items-center rounded-2xl bg-sky-600 text-xs font-black text-white shadow-xs">
                          #{globalRank}
                        </span>

                        <div className="min-w-0 flex-1">
                          {/* Title & Match % */}
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <div className="flex flex-wrap items-center gap-1.5">
                                <span className="rounded-lg border border-white/80 bg-white/70 px-2 py-0.5 text-[10px] font-bold text-slate-600">
                                  Mã {major.code}
                                </span>
                                <FeasibilityBadge
                                  value={major.feasibility}
                                  label={major.feasibility_label}
                                />
                                <TrendBadge
                                  tier={major.trend_tier}
                                  isTrending={major.is_trending}
                                  reason={major.trend_reason}
                                />
                                {major.best_matching_block && major.best_block_score != null && (
                                  <span className="rounded-lg border border-sky-200/80 bg-sky-50/80 px-2 py-0.5 text-[10px] font-extrabold text-sky-700">
                                    {major.best_matching_block}: {major.best_block_score}đ
                                    {major.benchmark_cutoff ? ` / ~${major.benchmark_cutoff}đ` : ""}
                                  </span>
                                )}
                              </div>
                              {major.constraint_violations && major.constraint_violations.length > 0 && (
                                <p className="mt-1 text-[11px] font-semibold text-slate-600">
                                  {major.constraint_violations[0]}
                                </p>
                              )}
                              <h4 className="mt-1.5 text-base font-extrabold text-slate-900 transition-colors group-hover:text-sky-700 sm:text-lg">
                                {major.name}
                              </h4>
                            </div>

                            <span className="shrink-0 text-2xl font-black text-sky-600 sm:text-3xl">
                              {major.match}%
                            </span>
                          </div>

                          {/* 3 Pillars Score Breakdown (Unified Sky/Cyan Palette) */}
                          {major.fit && (
                            <div className="mt-3.5 grid grid-cols-3 gap-2.5 rounded-2xl border border-white/80 bg-white/50 p-3 backdrop-blur-md">
                              <div>
                                <div className="mb-1 flex justify-between text-[10px] font-bold text-slate-600">
                                  <span>Sở thích</span>
                                  <span className="text-sky-700">
                                    {major.fit.interest}%
                                  </span>
                                </div>
                                <div className="h-1.5 rounded-full bg-slate-200/70">
                                  <div
                                    className="h-full rounded-full bg-sky-600"
                                    style={{ width: `${major.fit.interest}%` }}
                                  />
                                </div>
                              </div>
                              <div>
                                <div className="mb-1 flex justify-between text-[10px] font-bold text-slate-600">
                                  <span>Học lực</span>
                                  <span className="text-sky-700">
                                    {major.fit.academic}%
                                  </span>
                                </div>
                                <div className="h-1.5 rounded-full bg-slate-200/70">
                                  <div
                                    className="h-full rounded-full bg-sky-500"
                                    style={{ width: `${major.fit.academic}%` }}
                                  />
                                </div>
                              </div>
                              <div>
                                <div className="mb-1 flex justify-between text-[10px] font-bold text-slate-600">
                                  <span>Nhận thức</span>
                                  <span className="text-cyan-700">
                                    {major.fit.cognitive}%
                                  </span>
                                </div>
                                <div className="h-1.5 rounded-full bg-slate-200/70">
                                  <div
                                    className="h-full rounded-full bg-cyan-500"
                                    style={{ width: `${major.fit.cognitive}%` }}
                                  />
                                </div>
                              </div>
                            </div>
                          )}

                          {/* Action Link */}
                          <div className="mt-3 flex justify-end">
                            <Link
                              to={`/majors/${major.id || major.code}`}
                              className="inline-flex items-center gap-1 text-xs font-extrabold text-sky-600 transition-all hover:gap-1.5 hover:text-sky-800"
                            >
                              Chi tiết & Lộ trình <ChevronRight size={14} />
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
