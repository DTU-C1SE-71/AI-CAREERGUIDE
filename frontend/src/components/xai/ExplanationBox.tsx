import { useId, useMemo, useState } from "react"
import { ChevronDown, ChevronUp, Loader2, Sparkles } from "lucide-react"
import Markdown from "react-markdown"
import remarkGfm from "remark-gfm"

function stripMarkdown(text: string): string {
  return text
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/^[-*]\s+/gm, "")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/__([^_]+)__/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\s+/g, " ")
    .trim()
}

function shortenSentence(sentence: string, maxLength = 260): string {
  if (sentence.length <= maxLength) return sentence
  return `${sentence.slice(0, maxLength - 3).replace(/\s+\S*$/, "")}...`
}

function buildSummary(text: string): string[] {
  const plain = stripMarkdown(text.replace(/^#{1,6}\s+.*$/gm, ""))
  // Sentence boundaries preserve decimal scores such as 8.2 and whole caveats.
  const sentences = plain.split(/(?<=[.!?])\s+(?=[A-ZÀ-Ỹ])/u).filter(Boolean)
  if (sentences.length <= 3) return sentences.map((sentence) => shortenSentence(sentence))

  const selected = new Set<number>([0])
  const caution = sentences.findIndex((sentence) =>
    /tuy nhiên|chưa đủ|chưa có|chưa thể|không phải|không bảo đảm|cần cải thiện|cần củng cố/i.test(sentence),
  )
  const academic = sentences.findIndex((sentence, index) =>
    index > 0 && index !== caution && /học lực|điểm|học tập|củng cố|rèn luyện/i.test(sentence),
  )
  if (academic >= 0) selected.add(academic)
  if (caution >= 0) selected.add(caution)
  for (let index = 1; selected.size < 3 && index < sentences.length; index++) {
    selected.add(index)
  }
  return [...selected]
    .sort((a, b) => a - b)
    .map((index) => shortenSentence(sentences[index]))
}

export function ExplanationBox({
  content,
  loading = false,
}: {
  content: string
  loading?: boolean
}) {
  const [expandedContent, setExpandedContent] = useState<string | null>(null)
  const expanded = expandedContent === content
  const contentId = useId()
  const summary = useMemo(() => buildSummary(content), [content])
  const hasDetails = Boolean(content.trim())

  return (
    <div className="glass-card rounded-2xl p-5 sm:rounded-3xl sm:p-6">
      <div className="mb-3.5 flex items-center justify-between gap-2 border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2 text-sm font-bold text-sky-700">
          <Sparkles size={16} />
          <span>Vì sao ngành này phù hợp?</span>
        </div>
        {loading && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-sky-50 px-3 py-1 text-xs font-semibold text-sky-700">
            <Loader2 size={13} className="animate-spin text-sky-600" />
            Đang phân tích...
          </span>
        )}
      </div>

      <div
        id={contentId}
        aria-busy={loading}
        className="markdown text-base font-medium leading-8 text-slate-700 sm:text-lg"
      >
        {expanded ? (
          <Markdown remarkPlugins={[remarkGfm]}>{content}</Markdown>
        ) : (
          <>
            {summary.length > 0 ? (
              <ul className="space-y-3.5 pl-5 marker:text-sky-500">
                {summary.map((item, index) => (
                  <li key={`${item}-${index}`} className="pl-1">
                    {item}
                  </li>
                ))}
              </ul>
            ) : (
              <p>
                {loading
                  ? "Đang chuẩn bị bản tóm tắt..."
                  : "Chưa có đủ dữ liệu để tạo giải thích."}
              </p>
            )}
          </>
        )}
      </div>

      {hasDetails && (
        <div className="mt-3 border-t border-slate-100 pt-2.5">
          <button
            type="button"
            onClick={() => setExpandedContent(expanded ? null : content)}
            aria-expanded={expanded}
            aria-controls={contentId}
            className="inline-flex items-center gap-1 text-xs font-semibold text-sky-600 transition hover:text-sky-800"
          >
            <span>
              {expanded ? "Thu gọn về bản tóm tắt" : "Xem giải thích chi tiết"}
            </span>
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>
      )}
    </div>
  )
}
