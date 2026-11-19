import { ArrowUpRight, Compass, Edit3, Loader2, X } from "lucide-react"
import { useRef, useState } from "react"
import { Link } from "react-router"
import type { AspirationAnalysisPayload, AspirationMajorBrief, CareerAspirationInput } from "../../types/assessment"
import { formatBlockWithSubjects } from "../../utils"
import { QUICK_DREAM_JOBS } from "../assessment/aspirationOptions"
import { HollandInterestSummary } from "../assessment/HollandInterestSummary"
import { TrendBadge } from "./TrendBadge"

function MajorBriefTile({ major, current, verified = true }: { major: AspirationMajorBrief; current?: boolean; verified?: boolean }) {
  const readiness = verified ? major.readiness : undefined
  const status = readiness?.status ?? "UNKNOWN"
  return <Link to={`/majors/${major.major_code}`} className="group block min-w-0 rounded-2xl border border-slate-200 bg-white/80 p-4 transition hover:border-sky-300 hover:shadow-md">
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <span className="font-semibold text-sky-700">Mã {major.major_code}</span>
      <TrendBadge tier={major.trend_tier} isTrending={major.is_trending} />
      <span className="rounded-full bg-slate-100 px-2 py-1 text-slate-700">{current && status === "READY_REFERENCE" ? "Đạt mốc tham chiếu" : status === "NEEDS_IMPROVEMENT" ? "Cần cải thiện theo mốc" : status === "READY_REFERENCE" ? "Đạt mốc tham chiếu" : "Chưa đủ cơ sở đối chiếu"}</span>
    </div>
    <h4 className="mt-2 font-bold text-slate-900">{major.major_name}</h4>
    {verified && major.relation_reason && <p className="mt-2 text-xs text-slate-600">{major.relation_reason}</p>}
    <p className="mt-2 text-xs leading-relaxed text-slate-600">{readiness?.message || "Kết quả cũ chưa có bằng chứng đối chiếu. Hãy phân tích lại nguyện vọng."}</p>
    {readiness?.block && <p className="mt-2 text-xs text-slate-700">{formatBlockWithSubjects(readiness.block, { short: true })} · Điểm hiện có: {readiness.block_score ?? "chưa đủ"}{readiness.benchmark_cutoff != null && ` · Mốc: ${readiness.benchmark_cutoff}`}</p>}
    {!!readiness?.missing_subjects?.length && <p className="mt-2 text-xs text-amber-800">Cần bổ sung điểm: {readiness.missing_subjects.join(", ")}</p>}
    {!!readiness?.violations?.length && <p className="mt-2 text-xs text-amber-800">{readiness.violations.join("; ")}</p>}
    {!!readiness?.gaps?.length && <ul className="mt-2 space-y-1 text-xs text-amber-800" aria-label="Điểm cần cải thiện">{readiness.gaps.map((gap, index) => {
      if (gap.kind === "SUBJECT_SCORE" && gap.subject && gap.required != null && gap.delta != null) return <li key={index}>Môn {gap.subject}: cần tăng ít nhất {Number(gap.delta.toPrecision(6))} điểm để đạt {gap.required} điểm{gap.actual != null && ` (hiện có ${gap.actual})`}.</li>
      if (gap.kind === "TOTAL_SCORE" && gap.amount != null) return <li key={index}>Tổng điểm tổ hợp cần tăng ít nhất {Number(gap.amount.toPrecision(6))} điểm để đạt mốc tham chiếu.</li>
      return null
    })}</ul>}
    {status === "READY_REFERENCE" && <p className="mt-2 text-xs text-slate-500">Mốc tham chiếu {readiness?.reference_method === "SUM_THREE_SUBJECTS" ? "theo tổng ba môn" : "đã xác minh"}; không bảo đảm trúng tuyển hoặc thay thế điều kiện từng trường.</p>}
    <span className="mt-3 flex items-center justify-between border-t border-slate-100 pt-2 text-xs font-semibold text-sky-700">Xem ngành và lộ trình <ArrowUpRight className="size-4" /></span>
  </Link>
}

interface AspirationAlignmentCardProps {
  analysis: AspirationAnalysisPayload | null
  currentAspiration?: CareerAspirationInput
  onUpdateAspiration: (next: CareerAspirationInput) => Promise<void>
  isAnalyzing?: boolean
  readOnly?: boolean
}

export function AspirationAlignmentCard({ analysis, currentAspiration, onUpdateAspiration, isAnalyzing = false, readOnly = false }: AspirationAlignmentCardProps) {
  const [editing, setEditing] = useState(false)
  const [draftJob, setDraftJob] = useState(currentAspiration?.dreamJob || analysis?.dream_job || "")
  const [saveError, setSaveError] = useState("")
  const [saving, setSaving] = useState(false)
  const editVersion = useRef(0)
  const setDraft = (value: string) => { editVersion.current += 1; setDraftJob(value); setSaveError("") }
  const apply = async (job: string) => {
    if (saving || readOnly) return
    const version = editVersion.current
    setSaving(true)
    setSaveError("")
    try {
      await onUpdateAspiration({ ...currentAspiration, dreamJob: job.trim(), desiredField: "" })
      if (version === editVersion.current) setEditing(false)
    } catch {
      setSaveError("Chưa lưu được nguyện vọng. Nội dung nháp vẫn được giữ; hãy thử lại.")
    } finally { setSaving(false) }
  }
  const modern = Boolean(analysis?.match_status)
  const goals = isAnalyzing ? [] : analysis?.dream_majors ?? []
  const current = modern && !isAnalyzing ? (analysis?.current_options ?? []).filter(m => m.readiness?.status === "READY_REFERENCE") : []
  const goalCodes = new Set(goals.map(m => m.major_code))
  const currentCodes = new Set(current.map(m => m.major_code))
  const exploration = (modern && !isAnalyzing ? analysis?.exploration_options ?? [] : []).filter(m => !goalCodes.has(m.major_code) && !currentCodes.has(m.major_code))
  return <section className="glass-card min-w-0 overflow-hidden rounded-2xl p-4 sm:rounded-3xl sm:p-6">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div><h2 className="flex items-center gap-2 text-lg font-bold text-slate-900"><Compass className="size-5 text-sky-600" /> Nguyện vọng và học lực hiện tại</h2>
        <p className="mt-1 break-words text-sm text-slate-700">{currentAspiration?.dreamJob || analysis?.dream_job || "Chưa chọn nghề mong muốn"}</p></div>
      {!readOnly && <button type="button" disabled={saving} onClick={() => { if (!editing) setDraft(currentAspiration?.dreamJob || analysis?.dream_job || ""); setEditing(!editing) }} className="inline-flex items-center gap-2 rounded-xl border border-sky-200 bg-white px-3 py-2 text-xs font-bold text-sky-700">{editing ? <X className="size-4" /> : <Edit3 className="size-4" />}{editing ? "Đóng" : "Đổi nghề mơ ước"}</button>}
    </div>
    {editing && <form className="mt-4 rounded-2xl border border-sky-200 bg-sky-50/50 p-4" onSubmit={event => { event.preventDefault(); void apply(draftJob) }}>
      <label htmlFor="aspiration-edit" className="text-sm font-semibold text-slate-800">Nghề mong muốn</label>
      <div className="mt-2 flex flex-col gap-2 sm:flex-row"><input id="aspiration-edit" name="dreamJob" disabled={saving} value={draftJob} onChange={e => setDraft(e.target.value)} className="min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm focus:outline-sky-500" placeholder="Ví dụ: Bác sĩ Y khoa" />
        <button type="submit" disabled={saving || isAnalyzing} className="flex items-center justify-center gap-2 rounded-xl bg-sky-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">{saving && <Loader2 className="size-4 animate-spin" />}{saveError ? "Thử lại" : "Lưu và phân tích lại"}</button></div>
      <div className="mt-3 flex flex-wrap gap-2">{QUICK_DREAM_JOBS.map(chip => <button key={chip.label} type="button" disabled={saving} onClick={() => setDraft(chip.dreamJob)} className="rounded-lg border border-sky-200 bg-white px-2 py-1 text-xs text-sky-800">{chip.label}</button>)}</div>
      {saveError && <p role="alert" className="mt-3 text-sm text-rose-700">{saveError}</p>}
    </form>}
    {!isAnalyzing && ((currentAspiration?.workValues?.length || analysis?.work_values?.length || currentAspiration?.preferredEnvironment || analysis?.preferred_environment)) && <p className="mt-3 rounded-xl bg-slate-50 p-3 text-xs leading-relaxed text-slate-600">
      {analysis?.preference_evidence?.work_values?.status === "USED" ? "Giá trị công việc đã được đối chiếu với thuộc tính khai báo của ngành mục tiêu." : "Giá trị công việc được giữ trong hồ sơ; chưa có đủ thuộc tính danh mục để xác nhận mức phù hợp với lựa chọn này."}
      {" Các lựa chọn này không bảo đảm thu nhập, thăng tiến hay điều kiện việc làm."}
      {(currentAspiration?.preferredEnvironment || analysis?.preferred_environment) && analysis?.preference_evidence?.environment?.status !== "USED" && " Môi trường mong muốn cũng chưa có đủ dữ liệu để đối chiếu."}
    </p>}
    {analysis?.interest_evidence && <div className="mt-4"><HollandInterestSummary evidence={analysis.interest_evidence} /></div>}
    <div className="mt-4 space-y-5">
      {isAnalyzing && <p role="status" className="text-sm text-slate-600">Đang đối chiếu hồ sơ…</p>}
      {!isAnalyzing && !modern && <p className="rounded-xl bg-amber-50 p-3 text-sm text-amber-900">Chưa có phân tích được xác minh cho nguyện vọng này. Kết nối lại và phân tích lại để đối chiếu dữ liệu.</p>}
      {!isAnalyzing && modern && analysis?.match_status === "UNRECOGNIZED" && <p className="text-sm text-slate-700">Chưa nhận diện được nghề trong danh mục. Hãy nhập một nghề cụ thể; điều này không có nghĩa bạn không thể theo đuổi nghề đó.</p>}
      {!isAnalyzing && modern && analysis?.match_status === "AMBIGUOUS" && <div className="rounded-xl bg-amber-50 p-4"><p className="text-sm text-amber-900">Có nhiều nghề trong nguyện vọng. Chọn một nghề để đối chiếu:</p><div className="mt-2 flex flex-wrap gap-2">{analysis.intent_candidates?.map(candidate => <button key={candidate.id} type="button" disabled={readOnly || saving || isAnalyzing} onClick={() => { setDraft(candidate.canonicalDreamJob); setEditing(true); void apply(candidate.canonicalDreamJob) }} className="rounded-lg border border-amber-200 bg-white px-3 py-2 text-sm disabled:opacity-50">{candidate.label}</button>)}</div></div>}
      <section><h3 className="font-bold text-slate-900">Mục tiêu của bạn</h3><p className="mt-1 text-xs text-slate-500">Nguyện vọng được giữ nguyên dù chưa đủ dữ liệu hoặc chưa đạt mốc tham chiếu.</p>
        {goals.length > 0 ? <div className="mt-3 grid gap-3 sm:grid-cols-2">{goals.map(major => <MajorBriefTile key={major.major_code} major={major} verified={modern} current={currentCodes.has(major.major_code)} />)}</div> : <p className="mt-2 text-sm text-slate-600">{isAnalyzing ? "Đang nhận diện ngành theo mục tiêu…" : "Chưa có ngành được ghép với mục tiêu này."}</p>}</section>
      <section><h3 className="font-bold text-slate-900">Lựa chọn đạt mốc tham chiếu hiện tại</h3>
        {isAnalyzing ? <p className="mt-2 text-sm text-slate-600">Đang đối chiếu bằng chứng học lực…</p> : current.length === 0 ? <p className="mt-2 text-sm leading-relaxed text-slate-600">Chưa có lựa chọn đủ bằng chứng để xếp vào nhóm này. Có thể thiếu mốc tuyển sinh cùng phương thức hoặc dữ liệu điểm; đây không phải kết luận bạn không phù hợp với nghề.</p> : <><p className="mt-2 text-xs text-slate-600">{current.filter(m => goalCodes.has(m.major_code)).map(m => m.major_name).join(", ")}{current.some(m => goalCodes.has(m.major_code)) && " — cũng là mục tiêu của bạn, xem thẻ phía trên."}</p><div className="mt-3 grid gap-3 sm:grid-cols-2">{current.filter(m => !goalCodes.has(m.major_code)).map(major => <MajorBriefTile key={major.major_code} major={major} current />)}</div></>}</section>
      {exploration.length > 0 && <section><h3 className="font-bold text-slate-900">Cần bổ sung dữ liệu để đối chiếu</h3><p className="mt-1 text-xs text-slate-500">Các ngành liên quan để tìm hiểu thêm; chưa được xác nhận đạt mốc hiện tại.</p><div className="mt-3 grid gap-3 sm:grid-cols-2">{exploration.map(major => <MajorBriefTile key={major.major_code} major={major} />)}</div></section>}
    </div>
  </section>
}
