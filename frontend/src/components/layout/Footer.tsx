import { BrainCircuit } from "lucide-react"
import { PageContainer } from "./PageContainer"

export function Footer() {
  return (
    <footer className="mt-auto border-t border-white/75 bg-white/40 py-5 backdrop-blur-2xl">
      <PageContainer className="flex flex-col items-center justify-between gap-2 text-center sm:flex-row sm:text-left">
        <div className="flex items-center gap-2 text-base font-extrabold text-slate-800">
          <BrainCircuit size={20} className="text-sky-600" />
          AI CareerGuide
        </div>
        <p className="text-sm font-medium text-slate-500">
          © 2026 AI CareerGuide
        </p>
      </PageContainer>
    </footer>
  )
}
