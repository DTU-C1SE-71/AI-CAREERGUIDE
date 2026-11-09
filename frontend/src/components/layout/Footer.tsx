import { BrainCircuit } from "lucide-react"
import { PageContainer } from "./PageContainer"

export function Footer() {
  return (
    <footer className="border-t border-white/75 bg-white/35 py-6 backdrop-blur-2xl">
      <PageContainer className="flex flex-col items-center justify-between gap-2 text-center sm:flex-row sm:text-left">
        <div className="flex items-center gap-2 text-sm font-extrabold text-slate-800">
          <BrainCircuit size={18} className="text-sky-600" />
          AI CareerGuide
        </div>
        <p className="text-xs font-medium text-slate-400">
          © 2026 AI CareerGuide
        </p>
      </PageContainer>
    </footer>
  )
}
