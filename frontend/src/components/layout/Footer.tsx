import { BrainCircuit } from "lucide-react"
import { PageContainer } from "./PageContainer"

export function Footer() {
  return (
    <footer className="mt-auto border-t border-slate-200/70 bg-white/55 py-4 backdrop-blur-xl">
      <PageContainer className="flex flex-col items-center justify-between gap-2 text-center sm:flex-row sm:text-left">
        <div className="flex items-center gap-2 text-sm font-bold text-slate-700">
          <BrainCircuit size={18} className="text-sky-600" />
          <span>AI CareerGuide</span>
        </div>
        <p className="text-xs font-medium text-slate-500">
          © 2026 AI CareerGuide · Định hướng ngành học cá nhân hóa
        </p>
      </PageContainer>
    </footer>
  )
}
