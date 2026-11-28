import { AnimatePresence, motion } from "framer-motion"
import { MessageCircle } from "lucide-react"
import { lazy, Suspense, useEffect, useState } from "react"
import { Outlet, ScrollRestoration, useLocation } from "react-router"
const AIChatAdvisor = lazy(() => import("../../pages/AIChatAdvisor").then(module => ({ default: module.AIChatAdvisor })))
import { Footer } from "./Footer"
import { Sidebar } from "./Sidebar"
import { PROFILE_SETUP_STORAGE_KEY, UserProfileModal } from "../profile/UserProfileModal"
import { useAIConnection } from "../../context/AIConnectionContext"
import { useAuth } from "../../context/AuthContext"

export function MainLayout() {
  const { user } = useAuth()
  const { connection } = useAIConnection()
  const aiStatusDotClass =
    connection.state === "online"
      ? "bg-emerald-400"
      : connection.state === "checking"
        ? "animate-pulse bg-amber-300"
        : "bg-rose-400"
  const aiStatusText =
    connection.state === "online"
      ? "Đang hoạt động"
      : connection.state === "checking"
        ? "Đang kiểm tra…"
        : "Chưa kết nối"
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  const [chatMounted, setChatMounted] = useState(false)
  const openChat = () => {
    setChatMounted(true)
    setChatOpen(true)
  }
  const [showProfileSetup, setShowProfileSetup] = useState(false)
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

  useEffect(() => {
    if (!user || user.role !== "student" || location.pathname.startsWith("/login")) {
      setShowProfileSetup(false)
      return
    }
    if (sessionStorage.getItem(PROFILE_SETUP_STORAGE_KEY) === "1") {
      setShowProfileSetup(true)
    }
  }, [user, location.pathname])

  const handleCloseProfileSetup = () => {
    sessionStorage.removeItem(PROFILE_SETUP_STORAGE_KEY)
    setShowProfileSetup(false)
  }

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
        onOpenChat={openChat}
      />

      <div
        style={{ paddingLeft: desktop ? (collapsed ? 84 : 260) : 0 }}
        className="relative z-10 flex min-h-screen min-w-0 flex-col overflow-x-clip pt-18 transition-[padding-left] duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] motion-reduce:transition-none lg:pt-0"
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
      </div>

      {chatMounted && (
        <Suspense
          fallback={
            chatOpen ? (
              <p role="status" className="fixed bottom-4 right-4 rounded-xl bg-white p-4 shadow-lg">
                Đang mở tư vấn…
              </p>
            ) : null
          }
        >
          <AIChatAdvisor open={chatOpen} onClose={() => setChatOpen(false)} />
        </Suspense>
      )}

      <AnimatePresence>
        {!chatOpen && (
          <motion.div
            key="ai-advisor-fab"
            initial={{ opacity: 0, scale: 0.88, y: 6 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.88, y: 6 }}
            transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
            className="fixed bottom-5 right-5 z-50"
          >
            <button
              type="button"
              onClick={openChat}
              aria-label={`Mở Giáo viên Cố vấn AI (${aiStatusText})`}
              className="group inline-flex h-[52px] items-center rounded-full bg-gradient-to-br from-sky-500 to-cyan-600 p-1.5 text-white shadow-lg shadow-sky-600/25 ring-1 ring-white/30 transition-[transform,box-shadow] duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] hover:-translate-y-0.5 hover:shadow-xl hover:shadow-sky-600/35 active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 focus-visible:ring-offset-2 motion-reduce:transition-none cursor-pointer select-none"
            >
              <span className="grid grid-cols-[0fr] transition-[grid-template-columns] duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] group-hover:grid-cols-[1fr] group-focus-visible:grid-cols-[1fr] motion-reduce:transition-none">
                <span className="overflow-hidden">
                  <span className="flex flex-col items-end whitespace-nowrap pl-3.5 pr-1.5 text-right opacity-0 translate-x-2 transition-[opacity,transform] duration-150 ease-[cubic-bezier(0.22,1,0.36,1)] group-hover:translate-x-0 group-hover:opacity-100 group-hover:duration-200 group-hover:delay-75 group-focus-visible:translate-x-0 group-focus-visible:opacity-100 group-focus-visible:duration-200 group-focus-visible:delay-75 motion-reduce:transition-none">
                    <span className="text-sm font-bold leading-tight">Giáo viên Cố vấn AI</span>
                    <span className="text-[11px] font-medium leading-tight text-sky-100">
                      {aiStatusText}
                    </span>
                  </span>
                </span>
              </span>
              <span className="grid size-10 shrink-0 place-items-center rounded-full">
                <span className="relative inline-flex items-center justify-center transition-transform duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] group-hover:scale-105 motion-reduce:transition-none">
                  <MessageCircle size={21} />
                  <span
                    className={`absolute -right-1 -top-1 size-2.5 rounded-full border-2 border-sky-500 ${aiStatusDotClass}`}
                  />
                </span>
              </span>
            </button>
          </motion.div>
        )}
      </AnimatePresence>
      <UserProfileModal
        isOpen={showProfileSetup}
        onClose={handleCloseProfileSetup}
        isSetupMode
      />
      <ScrollRestoration />
    </div>
  )
}
