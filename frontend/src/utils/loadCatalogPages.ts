const PAGE_SIZE = 500
const MAX_ROWS = 10000

/** Chỉ trả danh mục khi đã nhận hết các trang; không biến dữ liệu một phần thành tổng số. */
export async function loadCatalogPages<T extends { major_code: string; name: string }>(
  fetchPage: (limit: number, offset: number) => Promise<unknown>,
  signal?: AbortSignal,
): Promise<T[]> {
  const rows: T[] = []
  const seen = new Set<string>()
  for (let offset = 0; offset <= MAX_ROWS; offset += PAGE_SIZE) {
    signal?.throwIfAborted()
    const page = await fetchPage(PAGE_SIZE, offset)
    signal?.throwIfAborted()
    if (!Array.isArray(page) || page.length > PAGE_SIZE) throw new Error("Phản hồi danh mục ngành không hợp lệ.")
    if (rows.length + page.length > MAX_ROWS) throw new Error("Danh mục vượt giới hạn 10.000 dòng cho một lần tải. Chưa xác nhận được tổng số ngành.")
    for (const row of page) {
      if (!row || typeof row.major_code !== "string" || typeof row.name !== "string" || !row.major_code || !row.name) {
        throw new Error("Một bản ghi danh mục thiếu mã hoặc tên ngành. Vui lòng tải lại.")
      }
      if (seen.has(row.major_code)) throw new Error("Danh mục thay đổi trong lúc tải hoặc có mã trùng. Vui lòng tải lại để lấy đầy đủ dữ liệu.")
      seen.add(row.major_code)
      rows.push(row as T)
    }
    if (page.length < PAGE_SIZE) return rows
  }
  throw new Error("Chưa tải hết danh mục. Vui lòng thử lại.")
}
