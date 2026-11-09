import { Loader2, Sparkles } from "lucide-react"
import Markdown from "react-markdown"
import remarkGfm from "remark-gfm"

export function ExplanationBox({
  content,
  loading = false,
}: {
  content: string
  loading?: boolean
}) {
  return (
    <div className="glass-card rounded-3xl p-6">
      <div className="mb-3 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-extrabold text-sky-700">
          <Sparkles size={16} />
          Phân tích XAI
        </div>
        {loading && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-white/75 px-2.5 py-1 text-[10px] font-bold text-sky-700 ring-1 ring-white/90">
            <Loader2 size={12} className="animate-spin text-sky-600" />
            Đang phân tích...
          </span>
        )}
      </div>
      <div className="markdown text-sm leading-7 text-slate-700">
        <Markdown remarkPlugins={[remarkGfm]}>{content}</Markdown>
      </div>
    </div>
  )
}
