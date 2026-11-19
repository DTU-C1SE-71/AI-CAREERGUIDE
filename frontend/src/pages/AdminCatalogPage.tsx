import { FileUp } from "lucide-react"
import { Link } from "react-router"
import { useAdmin } from "../components/admin/AdminLayout"
import { MajorsCatalogPanel } from "../components/admin/MajorsCatalogPanel"

export function AdminCatalogPage() {
  const { notify } = useAdmin()
  return (
    <section aria-labelledby="admin-catalog-title">
      <div className="admin-page-heading">
        <div>
          <h1 id="admin-catalog-title">Danh mục ngành</h1>
          <p>Tra cứu dữ liệu đang hoạt động trong cơ sở dữ liệu. Tìm theo tên, mã ngành, tổ hợp hoặc nhóm lĩnh vực.</p>
        </div>
        <Link to="/admin/import" className="admin-button">
          <FileUp size={17} aria-hidden="true" />Nhập danh mục
        </Link>
      </div>
      <MajorsCatalogPanel onNotify={notify} />
    </section>
  )
}
