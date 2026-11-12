/**
 * Các hàm tiện ích dùng chung (Helper Utilities) cho Frontend
 */

/**
 * Định dạng điểm số phần trăm (vd: 91.5 -> 92%)
 */
export function formatPercent(value?: number): string {
  if (value === undefined || value === null || Number.isNaN(value)) return "0%"
  return `${Math.round(value)}%`
}

/**
 * Định dạng Z-score kèm dấu +/- (vd: 1.18 -> +1.18)
 */
export function formatZScore(value?: number): string {
  if (value === undefined || value === null || Number.isNaN(value)) return "0.00"
  const prefix = value > 0 ? "+" : ""
  return `${prefix}${value.toFixed(2)}`
}

/**
 * Rút gọn chuỗi văn bản quá dài kèm dấu ba chấm
 */
export function truncateText(text: string, maxLength: number): string {
  if (!text || text.length <= maxLength) return text
  return `${text.slice(0, maxLength).trim()}...`
}

/**
 * Chuyển đổi mã ngành cấp IV thành chuỗi hiển thị chuẩn (vd: 7480101 -> 748.01.01)
 */
export function formatMajorCode(code: string): string {
  if (!code || code.length !== 7) return code
  return `${code.slice(0, 3)}.${code.slice(3, 5)}.${code.slice(5)}`
}

/**
 * Bản đồ ánh xạ tổ hợp xét tuyển chuẩn Bộ GD&ĐT sang tên đầy đủ các môn học cấu thành
 */
export const BLOCK_SUBJECTS_MAP: Record<string, string> = {
  A00: "Toán, Vật lý, Hóa học",
  A01: "Toán, Vật lý, Tiếng Anh",
  A02: "Toán, Vật lý, Sinh học",
  B00: "Toán, Hóa học, Sinh học",
  B08: "Toán, Sinh học, Tiếng Anh",
  C00: "Ngữ văn, Lịch sử, Địa lý",
  C01: "Ngữ văn, Toán, Vật lý",
  C02: "Ngữ văn, Toán, Hóa học",
  C03: "Ngữ văn, Toán, Lịch sử",
  C04: "Ngữ văn, Toán, Địa lý",
  D01: "Toán, Ngữ văn, Tiếng Anh",
  D07: "Toán, Hóa học, Tiếng Anh",
  D08: "Toán, Sinh học, Tiếng Anh",
  D09: "Toán, Lịch sử, Tiếng Anh",
  D10: "Toán, Địa lý, Tiếng Anh",
  D14: "Ngữ văn, Lịch sử, Tiếng Anh",
  D15: "Ngữ văn, Địa lý, Tiếng Anh",
  H00: "Ngữ văn, Năng khiếu Vẽ",
  V00: "Toán, Vật lý, Vẽ mỹ thuật",
  V01: "Toán, Ngữ văn, Vẽ mỹ thuật",
}

/**
 * Bản đồ tên rút gọn các môn cho badge nhỏ trên mobile hoặc card hẹp
 */
export const BLOCK_SUBJECTS_SHORT_MAP: Record<string, string> = {
  A00: "Toán, Lý, Hóa",
  A01: "Toán, Lý, Anh",
  A02: "Toán, Lý, Sinh",
  B00: "Toán, Hóa, Sinh",
  B08: "Toán, Sinh, Anh",
  C00: "Văn, Sử, Địa",
  C01: "Văn, Toán, Lý",
  C02: "Văn, Toán, Hóa",
  C03: "Văn, Toán, Sử",
  C04: "Văn, Toán, Địa",
  D01: "Toán, Văn, Anh",
  D07: "Toán, Hóa, Anh",
  D08: "Toán, Sinh, Anh",
  D09: "Toán, Sử, Anh",
  D10: "Toán, Địa, Anh",
  D14: "Văn, Sử, Anh",
  D15: "Văn, Địa, Anh",
  H00: "Văn, Năng khiếu",
  V00: "Toán, Lý, Vẽ",
  V01: "Toán, Văn, Vẽ",
}

/**
 * Định dạng mã tổ hợp kèm tên các môn học rõ ràng, dễ hiểu cho học sinh và phụ huynh.
 * VD:
 * - formatBlockWithSubjects("A00") -> "Khối A00 (Toán, Vật lý, Hóa học)"
 * - formatBlockWithSubjects("A00", { short: true }) -> "Khối A00 (Toán, Lý, Hóa)"
 * - formatBlockWithSubjects("A00", { short: true, includePrefix: false }) -> "A00 (Toán, Lý, Hóa)"
 */
export function formatBlockWithSubjects(
  block?: string | null,
  options?: { short?: boolean; includePrefix?: boolean }
): string {
  if (!block) return ""
  const str = String(block).trim()
  if (str.includes("(") && str.includes(")")) {
    return str
  }
  const match = str.match(/([A-Za-z]\d{2})/i)
  if (!match) return str
  const code = match[1].toUpperCase()
  const map = options?.short ? BLOCK_SUBJECTS_SHORT_MAP : BLOCK_SUBJECTS_MAP
  const subjs = map[code]
  const prefix = options?.includePrefix !== false ? "Khối " : ""
  if (subjs) {
    return `${prefix}${code} (${subjs})`
  }
  return `${prefix}${code}`
}
