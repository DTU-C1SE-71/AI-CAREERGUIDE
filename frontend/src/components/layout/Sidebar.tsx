import {
  BarChart3,
  BrainCircuit,
  ClipboardCheck,
  Compass,
  LogIn,
  LogOut,
  Map,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  UserCheck,
  X,
} from "lucide-react"
import { AnimatePresence, motion } from "framer-motion"
import { type ReactNode, useEffect, useRef, useState } from "react"
import { Link, NavLink, useNavigate } from "react-router"
import { useAuth } from "../../context/AuthContext"
import { UserProfileModal } from "../profile/UserProfileModal"

interface SidebarProps {
  collapsed: boolean
  mobileOpen: boolean
  onToggle: () => void
  onMobileClose: () => void
  onMobileOpen: () => void
  onOpenChat: () => void
}

const mainLinks = [
  {
    label: "Tổng quan",
    href: "/",
    icon: BarChart3,
  },
  {
    label: "Trắc nghiệm",
    href: "/assessment",
    icon: ClipboardCheck,
  },
  {
    label: "Khám phá ngành",
    href: "/dashboard",
    icon: Compass,
  },
  {
    label: "Lộ trình 4 tuần",
    href: "/roadmap",
    icon: Map,
  },
]

function SidebarLabel({
  children,
  collapsed,
}: {
  children: ReactNode
  collapsed: boolean
}) {
  return (
    <AnimatePresence initial={false}>
      {!collapsed && (
        <motion.span
          initial={{ opacity: 0, width: 0 }}
          animate={{ opacity: 1, width: "auto" }}
          exit={{ opacity: 0, width: 0 }}
          transition={{ duration: 0.16, ease: [0.22, 1, 0.36, 1] }}
          className="overflow-hidden whitespace-nowrap"
        >
          {children}
        </motion.span>
      )}
    </AnimatePresence>
  )
}

function SidebarBody({
  collapsed,
  onToggle,
  onNavigate,
  onOpenChat,
  mobile,
}: {
  collapsed: boolean
  onToggle: () => void
  onNavigate?: () => void
  onOpenChat: () => void
  mobile?: boolean
}) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [showSettingsMenu, setShowSettingsMenu] = useState(false)
  const [showProfileModal, setShowProfileModal] = useState(false)
  const menuRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!showSettingsMenu) return
    const handleOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowSettingsMenu(false)
      }
    }
    document.addEventListener("mousedown", handleOutside)
    return () => document.removeEventListener("mousedown", handleOutside)
  }, [showSettingsMenu])

  const handleQuickSearch = () => {
    onNavigate?.()
    navigate("/dashboard?search=1")
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* Brand Header */}
      <div
        className={`flex shrink-0 items-center ${
          collapsed ? "flex-col justify-start gap-2.5 py-1" : "h-13 gap-2 px-1"
        }`}
      >
        <Link
          to="/"
          onClick={onNavigate}
          className={`flex min-w-0 items-center gap-2.5 ${
            collapsed ? "" : "flex-1"
          }`}
          title={collapsed ? "AI CareerGuide" : undefined}
        >
          <span className="relative grid size-10 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-sky-500 to-cyan-600 text-white shadow-sm shadow-sky-600/20">
            <BrainCircuit size={20} />
          </span>
          <SidebarLabel collapsed={collapsed}>
            <span className="block text-base font-extrabold tracking-tight text-slate-900">
              AI Career<span className="text-sky-600">Guide</span>
            </span>
          </SidebarLabel>
        </Link>

        {!collapsed && (
          <button
            type="button"
            onClick={handleQuickSearch}
            className="sidebar-icon-button"
            title="Tra cứu danh mục ngành"
            aria-label="Tìm kiếm nhanh"
          >
            <Search size={17} />
          </button>
        )}

        <button
          type="button"
          onClick={onToggle}
          className={
            collapsed
              ? "grid size-10 shrink-0 place-items-center rounded-xl bg-sky-50 text-sky-700 transition hover:bg-sky-100"
              : "sidebar-icon-button"
          }
          title={collapsed ? "Mở rộng thanh bên" : "Thu gọn thanh bên"}
          aria-label={collapsed ? "Mở rộng thanh bên" : "Thu gọn thanh bên"}
        >
          {mobile ? (
            <X size={18} />
          ) : collapsed ? (
            <PanelLeftOpen size={18} />
          ) : (
            <PanelLeftClose size={18} />
          )}
        </button>
      </div>

      {/* Quick AI Assistant Action */}
      <div className="mt-4 shrink-0 px-0.5">
        <button
          type="button"
          onClick={onOpenChat}
          title={collapsed ? "Trợ lý AI" : undefined}
          className={`group flex h-11 w-full items-center rounded-2xl border border-sky-200/80 bg-sky-50/75 font-bold text-sky-700 transition hover:border-sky-300 hover:bg-sky-100/70 active:scale-[0.985] ${
            collapsed ? "justify-center px-0" : "gap-2.5 px-3.5 text-sm"
          }`}
        >
          <Sparkles
            size={17}
            className="shrink-0 text-sky-600 transition-transform duration-200 group-hover:scale-110"
          />
          <SidebarLabel collapsed={collapsed}>Trợ lý AI</SidebarLabel>
        </button>
      </div>

      {/* Primary Navigation */}
      <div className="sidebar-scroll mt-5 flex-1 overflow-x-hidden overflow-y-auto px-0.5">
        <nav aria-label="Điều hướng chính">
          <div className="space-y-1.5">
            {mainLinks.map(({ label, href, icon: Icon }) => (
              <NavLink
                key={href}
                to={href}
                end={href === "/"}
                onClick={onNavigate}
                title={collapsed ? label : undefined}
                className={`relative flex h-11 items-center rounded-2xl text-sm font-semibold transition-colors ${
                  collapsed ? "justify-center px-0" : "gap-3 px-3.5"
                }`}
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <motion.span
                        layoutId="activeSidebarItem"
                        className="absolute inset-0 rounded-2xl border border-sky-200/80 bg-white shadow-xs"
                        transition={{
                          type: "spring",
                          stiffness: 380,
                          damping: 32,
                        }}
                      />
                    )}
                    <Icon
                      size={18}
                      className={`relative z-10 shrink-0 transition-colors ${
                        isActive ? "text-sky-600" : "text-slate-500"
                      }`}
                    />
                    {!collapsed && (
                      <span
                        className={`relative z-10 min-w-0 flex-1 truncate transition-colors ${
                          isActive
                            ? "font-bold text-slate-900"
                            : "text-slate-600 hover:text-slate-900"
                        }`}
                      >
                        {label}
                      </span>
                    )}
                  </>
                )}
              </NavLink>
            ))}

            {user?.role === "admin" && (
              <NavLink
                to="/admin"
                onClick={onNavigate}
                title={collapsed ? "Quản trị hệ thống" : undefined}
                className={`relative flex h-11 items-center rounded-2xl text-sm font-semibold transition-colors ${
                  collapsed ? "justify-center px-0" : "gap-3 px-3.5"
                }`}
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <motion.span
                        layoutId="activeSidebarItem"
                        className="absolute inset-0 rounded-2xl border border-sky-200/80 bg-white shadow-xs"
                        transition={{
                          type: "spring",
                          stiffness: 380,
                          damping: 32,
                        }}
                      />
                    )}
                    <ShieldCheck
                      size={18}
                      className={`relative z-10 shrink-0 ${
                        isActive ? "text-sky-600" : "text-slate-500"
                      }`}
                    />
                    {!collapsed && (
                      <span
                        className={`relative z-10 truncate ${
                          isActive
                            ? "font-bold text-slate-900"
                            : "text-slate-600 hover:text-slate-900"
                        }`}
                      >
                        Quản trị hệ thống
                      </span>
                    )}
                  </>
                )}
              </NavLink>
            )}
          </div>
        </nav>
      </div>

      {/* Account Footer */}
      <div
        ref={menuRef}
        className="relative mt-2 shrink-0 border-t border-slate-200/70 pt-3"
      >
        {user ? (
          <>
            <AnimatePresence>
              {showSettingsMenu && (
                <motion.div
                  initial={{ opacity: 0, y: 8, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 6, scale: 0.98 }}
                  transition={{ duration: 0.16, ease: [0.22, 1, 0.36, 1] }}
                  className={`mb-2.5 space-y-2 rounded-2xl border border-slate-200/90 bg-white p-3 text-sm shadow-xl ${
                    collapsed
                      ? "fixed bottom-4 left-21 z-[90] w-68"
                      : "w-full"
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => {
                      setShowSettingsMenu(false)
                      setShowProfileModal(true)
                    }}
                    className="flex w-full items-center gap-3 rounded-xl border-b border-slate-100 p-1.5 pb-3 text-left transition hover:bg-slate-50"
                  >
                    <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-sky-500 to-cyan-600 text-xs font-bold text-white">
                      {user.name.slice(0, 2).toUpperCase()}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-bold text-slate-900">
                        {user.name}
                      </p>
                      <p className="truncate text-xs text-slate-500">
                        {user.email}
                      </p>
                    </div>
                  </button>

                  <div className="space-y-1">
                    <button
                      type="button"
                      onClick={() => {
                        setShowSettingsMenu(false)
                        setShowProfileModal(true)
                      }}
                      className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-left text-xs font-semibold text-slate-700 transition hover:bg-sky-50 hover:text-sky-700"
                    >
                      <UserCheck size={15} className="text-sky-600" />
                      <span>Chỉnh sửa hồ sơ</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        setShowSettingsMenu(false)
                        onNavigate?.()
                        navigate("/dashboard")
                      }}
                      className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-left text-xs font-semibold text-slate-700 transition hover:bg-sky-50 hover:text-sky-700"
                    >
                      <Compass size={15} className="text-sky-600" />
                      <span>Kết quả định hướng</span>
                    </button>

                    {user.role === "admin" && (
                      <button
                        type="button"
                        onClick={() => {
                          setShowSettingsMenu(false)
                          onNavigate?.()
                          navigate("/admin")
                        }}
                        className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-left text-xs font-semibold text-slate-700 transition hover:bg-sky-50 hover:text-sky-700"
                      >
                        <ShieldCheck size={15} className="text-sky-600" />
                        <span>Quản trị hệ thống</span>
                      </button>
                    )}
                  </div>

                  <div className="border-t border-slate-100 pt-1.5">
                    <button
                      type="button"
                      onClick={() => {
                        setShowSettingsMenu(false)
                        logout()
                      }}
                      className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-left text-xs font-semibold text-rose-600 transition hover:bg-rose-50"
                    >
                      <LogOut size={15} />
                      <span>Đăng xuất</span>
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <div
              onClick={() => setShowSettingsMenu((v) => !v)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault()
                  setShowSettingsMenu((v) => !v)
                }
              }}
              title={user.name}
              className={`flex items-center rounded-2xl border border-slate-200/80 bg-white/75 p-2 transition hover:border-sky-200 hover:bg-white ${
                collapsed ? "justify-center" : "gap-2.5"
              }`}
            >
              <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-sky-500 to-cyan-600 text-xs font-bold text-white">
                {user.name.slice(0, 2).toUpperCase()}
              </span>
              {!collapsed && (
                <>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-bold text-slate-800">
                      {user.name}
                    </p>
                    <p className="truncate text-xs text-slate-500">
                      {user.role === "admin" ? "Quản trị viên" : user.grade_level || "Học sinh"}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      setShowSettingsMenu(false)
                      setShowProfileModal(true)
                    }}
                    title="Chỉnh sửa hồ sơ"
                    className="group grid size-8 place-items-center rounded-xl text-slate-400 transition hover:bg-slate-100 hover:text-sky-600"
                  >
                    <Settings
                      size={16}
                      className="transition-transform duration-200 group-hover:rotate-45"
                    />
                  </button>
                </>
              )}
            </div>
          </>
        ) : (
          <Link
            to="/login"
            title={collapsed ? "Đăng nhập" : undefined}
            className={`flex h-11 items-center rounded-2xl border border-slate-200/80 bg-white/80 text-sm font-bold text-slate-700 transition hover:border-sky-300 hover:bg-white ${
              collapsed ? "justify-center" : "gap-3 px-3.5"
            }`}
          >
            <LogIn size={17} className="text-sky-600" />
            <SidebarLabel collapsed={collapsed}>Đăng nhập</SidebarLabel>
          </Link>
        )}
      </div>

      <UserProfileModal
        isOpen={showProfileModal}
        onClose={() => setShowProfileModal(false)}
      />
    </div>
  )
}

export function Sidebar({
  collapsed,
  mobileOpen,
  onToggle,
  onMobileClose,
  onMobileOpen,
  onOpenChat,
}: SidebarProps) {
  return (
    <>
      <header className="glass-panel fixed inset-x-3 top-3 z-50 flex h-14 items-center justify-between rounded-2xl px-3 lg:hidden">
        <button
          type="button"
          onClick={onMobileOpen}
          className="sidebar-icon-button"
          aria-label="Mở thanh điều hướng"
        >
          <Menu size={19} />
        </button>
        <Link to="/" className="flex items-center gap-2 text-sm font-extrabold">
          <span className="grid size-8 place-items-center rounded-xl bg-gradient-to-br from-sky-500 to-cyan-600 text-white">
            <BrainCircuit size={17} />
          </span>
          <span>
            AI Career<span className="text-sky-600">Guide</span>
          </span>
        </Link>
        <button
          type="button"
          onClick={onOpenChat}
          className="sidebar-icon-button"
          aria-label="Mở cố vấn AI"
        >
          <Sparkles size={18} className="text-sky-600" />
        </button>
      </header>

      <motion.aside
        initial={false}
        animate={{ width: collapsed ? 68 : 268 }}
        transition={{ duration: 0.26, ease: [0.22, 1, 0.36, 1] }}
        className="glass-sidebar fixed bottom-3 left-3 top-3 z-50 hidden overflow-hidden rounded-3xl p-3 lg:block"
      >
        <SidebarBody
          collapsed={collapsed}
          onToggle={onToggle}
          onOpenChat={onOpenChat}
        />
      </motion.aside>

      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.button
              type="button"
              className="fixed inset-0 z-[70] bg-slate-950/30 backdrop-blur-xs lg:hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              onClick={onMobileClose}
              aria-label="Đóng menu"
            />
            <motion.aside
              className="glass-sidebar fixed bottom-3 left-3 top-3 z-[80] w-[min(276px,calc(100vw-24px))] rounded-3xl p-3.5 lg:hidden"
              initial={{ x: "-108%" }}
              animate={{ x: 0 }}
              exit={{ x: "-108%" }}
              transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
            >
              <SidebarBody
                collapsed={false}
                mobile
                onToggle={onMobileClose}
                onNavigate={onMobileClose}
                onOpenChat={() => {
                  onMobileClose()
                  onOpenChat()
                }}
              />
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  )
}
