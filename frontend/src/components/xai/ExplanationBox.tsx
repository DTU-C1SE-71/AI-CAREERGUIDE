import { useState } from "react"
import { ChevronDown, ChevronUp, Loader2, Sparkles } from "lucide-react"
import Markdown from "react-markdown"
import remarkGfm from "remark-gfm"

export function ExplanationBox({
  content,
  loading = false,
}: {
  content: string
  loading?: boolean
}) {
  const [expanded, setExpanded] = useState(false)
  const isLongContent = content && content.length > 600

  return (
    <div className="glass-card rounded-2xl p-5 sm:rounded-3xl sm:p-6">
      <div className="mb-3.5 flex items-center justify-between gap-2 border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2 text-sm font-bold text-sky-700">
          <Sparkles size={16} />
          <span>Giải thích Định hướng AI (XAI)</span>
        </div>
        {loading && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-sky-50 px-3 py-1 text-xs font-semibold text-sky-700">
            <Loader2 size={13} className="animate-spin text-sky-600" />
            Đang phân tích...
          </span>
        )}
      </div>

      <div
        className={`markdown text-sm leading-relaxed text-slate-700 ${
          isLongContent && !expanded ? "line-clamp-6" : ""
        }`}
      >
        <Markdown remarkPlugins={[remarkGfm]}>{content}</Markdown>
      </div>

      {isLongContent && (
        <div className="mt-3 border-t border-slate-100 pt-2.5">
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="inline-flex items-center gap-1 text-xs font-semibold text-sky-600 transition hover:text-sky-800"
          >
            <span>{expanded ? "Thu gọn bớt" : "Xem toàn bộ phân tích"}</span>
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>
      )}
    </div>
  )
}
