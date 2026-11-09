import { AnimatePresence, motion } from "framer-motion"
import { MessageCircle } from "lucide-react"
import { useEffect, useState } from "react"
import { Outlet, ScrollRestoration, useLocation } from "react-router"
import { AIChatAdvisor } from "../../pages/AIChatAdvisor"
import { Footer } from "./Footer"
import { Sidebar } from "./Sidebar"

export function MainLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  const [desktop, setDesktop] = useState(() => window.innerWidth >= 1024)
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
        animate={{ paddingLeft: desktop ? (collapsed ? 76 : 300) : 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="relative z-10 min-h-screen pt-20 lg:pt-0"
      >
        <AnimatePresence mode="wait">
          <motion.main
            key={location.pathname}
            initial={{ opacity: 0, y: 12, filter: "blur(4px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            exit={{ opacity: 0, y: -6, filter: "blur(3px)" }}
            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
          >
            <Outlet />
          </motion.main>
        </AnimatePresence>
        <Footer />
      </motion.div>
      <AIChatAdvisor open={chatOpen} onClose={() => setChatOpen(false)} />
      {!chatOpen && (
        <motion.button
          onClick={() => setChatOpen(true)}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.96 }}
          className="fixed bottom-5 right-5 z-50 grid size-14 place-items-center rounded-2xl bg-gradient-to-br from-sky-400 via-sky-500 to-cyan-500 text-white shadow-xl shadow-sky-300/50"
          aria-label="Mở AI Career Advisor"
        >
          <MessageCircle size={22} />
          <i className="absolute -right-1 -top-1 size-3 rounded-full border-2 border-white bg-emerald-400" />
        </motion.button>
      )}
      <ScrollRestoration />
    </div>
  )
}
