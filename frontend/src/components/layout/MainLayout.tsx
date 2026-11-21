import { AnimatePresence, motion } from "framer-motion"
import { MessageCircle } from "lucide-react"
import { lazy, Suspense, useEffect, useState } from "react"
import { Outlet, ScrollRestoration, useLocation } from "react-router"
const AIChatAdvisor = lazy(() => import("../../pages/AIChatAdvisor").then(module => ({ default: module.AIChatAdvisor })))
import { Footer } from "./Footer"
import { Sidebar } from "./Sidebar"

export function MainLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  const [desktop, setDesktop] = useState(() =>
    typeof window !== "undefined" ? window.innerWidth >= 1024 : true,
  )
  const location = useLocation()

  useEffect(() => {
    const query = window.matchMedia("(min-width: 1024px)")
    const update = () => setDesktop(query.matches)
    query.addEventListener("change", update)
    return () => query.removeEventListener("change", update)
  }, [])

  return (
    <div className="mesh-bg min-h-screen text-slate-900">
      <div className="mesh-blob mesh-blob-sky" />
      <div className="mesh-blob mesh-blob-blue" />
      <div className="mesh-blob mesh-blob-cyan" />

      <Sidebar
        collapsed={collapsed}
        mobileOpen={mobileOpen}
        onToggle={() => setCollapsed((value) => !value)}
        onMobileClose={() => setMobileOpen(false)}
        onMobileOpen={() => setMobileOpen(true)}
        onOpenChat={() => setChatOpen(true)}
      />

      <motion.div
        initial={false}
        animate={{ paddingLeft: desktop ? (collapsed ? 84 : 260) : 0 }}
        transition={{ duration: 0.26, ease: [0.22, 1, 0.36, 1] }}
        className="relative z-10 flex min-h-screen min-w-0 flex-col overflow-x-clip pt-18 lg:pt-0"
      >
        <AnimatePresence mode="wait">
          <motion.main
            key={location.pathname}
            className="min-w-0 flex-1 pb-20 lg:pb-0"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
          >
            <Outlet />
          </motion.main>
        </AnimatePresence>
        <Footer />
      </motion.div>

      {chatOpen && <Suspense fallback={<p role="status" className="fixed bottom-4 right-4 rounded-xl bg-white p-4 shadow-lg">Đang mở tư vấn…</p>}><AIChatAdvisor open={chatOpen} onClose={() => setChatOpen(false)} /></Suspense>}

      {!chatOpen && (
        <motion.button
          type="button"
          onClick={() => setChatOpen(true)}
          whileHover={{ scale: 1.04, y: -2 }}
          whileTap={{ scale: 0.96 }}
          transition={{ duration: 0.18 }}
          className="fixed bottom-5 right-5 z-50 flex items-center gap-2.5 rounded-2xl bg-gradient-to-br from-sky-500 to-cyan-600 px-4 py-3.5 text-sm font-bold text-white shadow-lg shadow-sky-600/25 ring-1 ring-white/30"
          aria-label="Mở Cố vấn AI"
        >
          <span className="relative grid place-items-center">
            <MessageCircle size={20} />
            <span className="absolute -right-1 -top-1 size-2.5 rounded-full border-2 border-sky-500 bg-emerald-400" />
          </span>
          <span className="hidden sm:inline">Cố vấn AI</span>
        </motion.button>
      )}
      <ScrollRestoration />
    </div>
  )
}
