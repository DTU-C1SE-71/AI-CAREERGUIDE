import {
  BarChart3,
  BrainCircuit,
  ChevronRight,
  ClipboardCheck,
  Compass,
  LogIn,
  LogOut,
  Map,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react"
import { AnimatePresence, motion } from "framer-motion"
import { type ReactNode, useState } from "react"
import { Link, NavLink, useNavigate } from "react-router"
import { useAuth } from "../../context/AuthContext"

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
    short: "Tổng quan",
    href: "/",
    icon: BarChart3,
  },
  {
    label: "Trắc nghiệm",
    short: "Trắc nghiệm",
    href: "/assessment",
    icon: ClipboardCheck,
  },
  {
    label: "Khám phá 435 ngành",
    short: "435 Ngành học",
    href: "/dashboard",
    icon: Compass,
  },
  {
    label: "Lộ trình 4 tuần",
    short: "Lộ trình",
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
          transition={{ duration: 0.16 }}
          className="whitespace-nowrap"
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

  const handleQuickSearch = () => {
    onNavigate?.()
    navigate("/dashboard?search=1")
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div
        className={`flex shrink-0 items-center ${
          collapsed ? "h-24 flex-col justify-start gap-2" : "h-14 gap-2"
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
          <span className="relative grid size-10 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-sky-500 to-cyan-500 text-white shadow-md shadow-sky-500/20">
            <BrainCircuit size={20} />
          </span>
          <SidebarLabel collapsed={collapsed}>
            <span className="block text-sm font-black leading-tight text-slate-900">
              AI Career<span className="text-sky-600">Guide</span>
            </span>
          </SidebarLabel>
        </Link>
        {!collapsed && (
          <button
            type="button"
            onClick={handleQuickSearch}
            className="sidebar-icon-button"
            title="Tra cứu 435 ngành"
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
              ? "grid size-10 shrink-0 place-items-center rounded-xl bg-sky-100/80 text-sky-700 transition-all hover:bg-sky-200"
              : "sidebar-icon-button"
          }
          title={collapsed ? "Mở rộng" : "Thu gọn"}
          aria-label={collapsed ? "Mở rộng" : "Thu gọn"}
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

      <div className="mt-4 shrink-0">
        <button
          type="button"
          onClick={onOpenChat}
          title={collapsed ? "Trợ lý AI" : undefined}
          className={`group flex h-11 items-center rounded-2xl border border-white/85 bg-white/65 font-extrabold text-sky-700 shadow-2xs backdrop-blur-md transition hover:bg-white ${
            collapsed
              ? "w-full justify-center px-0"
              : "w-full gap-2.5 px-4 text-xs"
          }`}
        >
          <Plus
            size={17}
            className="shrink-0 transition-transform group-hover:rotate-90"
          />
          <SidebarLabel collapsed={collapsed}>Trợ lý AI</SidebarLabel>
        </button>
      </div>

      <div className="sidebar-scroll mt-5 flex-1 overflow-x-hidden overflow-y-auto pr-1">
        <nav>
          <motion.div
            className="space-y-1.5"
            initial="hidden"
            animate="visible"
            variants={{ visible: { transition: { staggerChildren: 0.04 } } }}
          >
            {mainLinks.map(({ label, short, href, icon: Icon }) => (
              <motion.div
                key={href}
                variants={{
                  hidden: { opacity: 0, x: -6 },
                  visible: { opacity: 1, x: 0 },
                }}
              >
                <NavLink
                  to={href}
                  end={href === "/"}
                  onClick={onNavigate}
                  title={collapsed ? label : undefined}
                  className={`relative flex h-11 items-center rounded-2xl text-xs font-bold transition-colors ${
                    collapsed ? "justify-center px-0" : "gap-3 px-3.5"
                  }`}
                >
                  {({ isActive }) => (
                    <>
                      {isActive && (
                        <motion.span
                          layoutId="activeSidebarItem"
                          className="absolute inset-0 rounded-2xl border border-white/90 bg-white/80 shadow-2xs backdrop-blur-md"
                          transition={{
                            type: "spring",
                            stiffness: 300,
                            damping: 30,
                          }}
                        />
                      )}
                      <Icon
                        size={17}
                        className={`relative z-10 shrink-0 ${
                          isActive ? "text-sky-600" : "text-slate-500"
                        }`}
                      />
                      {!collapsed && (
                        <>
                          <span
                            className={`relative z-10 min-w-0 flex-1 truncate ${
                              isActive ? "text-slate-900" : "text-slate-600"
                            }`}
                          >
                            {short}
                          </span>
                          <ChevronRight
                            size={13}
                            className={`relative z-10 ${
                              isActive ? "text-sky-500" : "text-slate-300"
                            }`}
                          />
                        </>
                      )}
                    </>
                  )}
                </NavLink>
              </motion.div>
            ))}
            {user?.role === "admin" && (
              <NavLink
                to="/admin"
                onClick={onNavigate}
                title={collapsed ? "Quản trị HITL" : undefined}
                className={`relative flex h-11 items-center rounded-2xl text-xs font-bold ${
                  collapsed ? "justify-center" : "gap-3 px-3.5"
                }`}
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <motion.span
                        layoutId="activeSidebarItem"
                        className="absolute inset-0 rounded-2xl border border-white/90 bg-white/80 shadow-2xs backdrop-blur-md"
                      />
                    )}
                    <ShieldCheck
                      size={17}
                      className="relative z-10 text-sky-600"
                    />
                    {!collapsed && (
                      <span className="relative z-10 text-slate-700">
                        Quản trị HITL
                      </span>
                    )}
                  </>
                )}
              </NavLink>
            )}
          </motion.div>
        </nav>
      </div>

      <div className="relative mt-2 shrink-0 border-t border-white/70 pt-2.5">
        {user ? (
          <>
            {showSettingsMenu && !collapsed && (
              <div className="mb-2 space-y-1.5 rounded-2xl border border-white/85 bg-white/90 p-2.5 text-xs shadow-lg backdrop-blur-xl">
                <div className="border-b border-slate-100 px-2 py-1">
                  <p className="truncate text-[11px] font-extrabold text-slate-800">
                    {user.name}
                  </p>
                  <p className="truncate text-[10px] font-medium text-slate-400">
                    {user.email}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setShowSettingsMenu(false)
                    logout()
                  }}
                  className="flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-left text-[11px] font-bold text-slate-700 hover:bg-slate-100/80"
                >
                  <LogOut size={14} />
                  <span>Đăng xuất</span>
                </button>
              </div>
            )}

            <div
              className={`flex items-center rounded-2xl border border-white/80 bg-white/55 p-2 backdrop-blur-md ${
                collapsed ? "justify-center" : "gap-2.5"
              }`}
            >
              <button
                type="button"
                onClick={logout}
                title={collapsed ? `${user.name} · Đăng xuất` : "Đăng xuất"}
                className="grid size-9 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-sky-500 to-cyan-500 text-[10px] font-black text-white"
              >
                {user.name.slice(0, 2).toUpperCase()}
              </button>
              {!collapsed && (
                <>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[11px] font-extrabold text-slate-800">
                      {user.name}
                    </p>
                    <p className="truncate text-[9px] font-semibold text-slate-400">
                      {user.role === "admin" ? "Quản trị viên" : "Học sinh"}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowSettingsMenu((v) => !v)}
                    title="Tài khoản"
                    className="group grid size-8 place-items-center rounded-xl text-slate-400 hover:bg-white hover:text-sky-600"
                  >
                    <Settings
                      size={15}
                      className="transition-transform group-hover:rotate-45"
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
            className={`flex h-11 items-center rounded-2xl border border-white/80 bg-white/60 text-xs font-bold text-slate-700 backdrop-blur-md ${
              collapsed ? "justify-center" : "gap-3 px-3.5"
            }`}
          >
            <LogIn size={17} className="text-sky-600" />
            <SidebarLabel collapsed={collapsed}>Đăng nhập</SidebarLabel>
          </Link>
        )}
      </div>
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
          onClick={onMobileOpen}
          className="sidebar-icon-button"
          aria-label="Mở thanh điều hướng"
        >
          <Menu size={19} />
        </button>
        <Link to="/" className="flex items-center gap-2 text-sm font-black">
          <span className="grid size-8 place-items-center rounded-xl bg-gradient-to-br from-sky-500 to-cyan-500 text-white">
            <BrainCircuit size={17} />
          </span>
          AI Career<span className="-ml-2 text-sky-600">Guide</span>
        </Link>
        <button
          onClick={onOpenChat}
          className="sidebar-icon-button"
          aria-label="Mở cố vấn AI"
        >
          <Sparkles size={18} className="text-sky-600" />
        </button>
      </header>

      <motion.aside
        initial={false}
        animate={{ width: collapsed ? 64 : 288 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="glass-sidebar fixed bottom-3 left-3 top-3 z-50 hidden overflow-hidden rounded-[26px] p-2.5 lg:block"
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
              className="fixed inset-0 z-[70] bg-slate-950/25 backdrop-blur-sm lg:hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={onMobileClose}
              aria-label="Đóng menu"
            />
            <motion.aside
              className="glass-sidebar fixed bottom-3 left-3 top-3 z-[80] w-[min(260px,calc(100vw-24px))] rounded-[26px] p-3 lg:hidden"
              initial={{ x: "-110%" }}
              animate={{ x: 0 }}
              exit={{ x: "-110%" }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
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
