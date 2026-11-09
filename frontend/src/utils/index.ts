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
