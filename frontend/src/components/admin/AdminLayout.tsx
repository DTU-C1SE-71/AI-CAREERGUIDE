import { useCallback, useEffect, useState } from "react"
import { Link, NavLink, Outlet, useLocation, useOutletContext } from "react-router"
import { BookOpen, Cpu, FileCheck2, FileUp, LogOut, Radar, ShieldCheck, X, ArrowUpRight, ChevronRight, UserRound } from "lucide-react"
import { useAuth } from "../../context/AuthContext"

type AdminContext = { notify: (message: string, error?: boolean) => void }
export const useAdmin = () => useOutletContext<AdminContext>()
const navigationGroups = [
  { title: "Dữ liệu", items: [
    { path: "/admin/catalog", title: "Danh mục ngành", icon: BookOpen },
    { path: "/admin/import", title: "Nhập danh mục", icon: FileUp },
    { path: "/admin/governance", title: "Kiểm duyệt dữ liệu", icon: FileCheck2 },
  ] },
  { title: "AI", items: [
    { path: "/admin/trends", title: "Xu hướng nghề nghiệp", icon: Radar },
    { path: "/admin/ai-settings", title: "Cấu hình AI & API", icon: Cpu },
  ] },
]
const navigation = navigationGroups.flatMap(group => group.items)

export function AdminLayout() {
  const { user, logout } = useAuth()
  const { pathname } = useLocation()
  const [notice, setNotice] = useState<{ message: string; error: boolean } | null>(null)
  const notify = useCallback((message: string, error = false) => setNotice({ message, error }), [])
  useEffect(() => {
    if (!notice) return
    const timer = window.setTimeout(() => setNotice(null), 7000)
    return () => window.clearTimeout(timer)
  }, [notice])
  return <div className="admin-shell">
    <a href="#admin-content" className="admin-skip">Đến nội dung chính</a>
    <aside className="admin-sidebar">
      <Link to="/admin" className="admin-brand"><span className="admin-brand-mark"><ShieldCheck aria-hidden="true" size={26} /></span><span>CareerGuide<strong>Quản trị hệ thống</strong></span></Link>
      <nav aria-label="Điều hướng quản trị" className="admin-nav">
        {navigationGroups.map(group => <div key={group.title} className="admin-nav-group">
          <h2 className="admin-nav-group-title">{group.title}</h2>
          <div className="admin-nav-group-links">{group.items.map(({ path, title, icon: Icon }) =>
            <NavLink key={path} to={path} className={({ isActive }) => isActive ? "active" : ""}><Icon aria-hidden="true" size={19} /><span>{title}</span></NavLink>)}</div>
        </div>)}
      </nav>
      <div className="admin-account"><div className="admin-account-details"><span className="admin-avatar"><UserRound size={20} aria-hidden="true" /></span><div><p className="font-semibold break-words">{user?.name}</p><p className="admin-role">Quản trị viên</p></div></div><button type="button" onClick={logout} className="admin-button mt-3 w-full"><LogOut aria-hidden="true" size={17} />Đăng xuất</button></div>
    </aside>
    <div className="admin-workspace">
      <header className="admin-topbar"><div className="admin-breadcrumb"><span>Quản trị</span><ChevronRight size={15} aria-hidden="true" /><strong>{navigation.find(item => item.path === pathname)?.title || "Hệ thống"}</strong></div><div className="flex items-center gap-4"><Link to="/">Xem trang chủ<ArrowUpRight size={15} aria-hidden="true" /></Link><button className="admin-button lg:hidden" onClick={logout}>Đăng xuất</button></div></header>
      <main id="admin-content" tabIndex={-1} className="admin-content">
        {notice && <div role={notice.error ? "alert" : "status"} className={`admin-notice ${notice.error ? "is-error" : "is-success"}`}><span>{notice.message}</span><button type="button" aria-label="Đóng thông báo" onClick={() => setNotice(null)}><X size={18} /></button></div>}
        <Outlet key={`${user?.id}:${pathname}`} context={{ notify } satisfies AdminContext} />
      </main>
    </div>
  </div>
}
