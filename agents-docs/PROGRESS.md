# Tiến độ nhánh làm việc – AI CareerGuide

> **Quy tắc chống conflict khi merge nhánh:**
> - **TUYỆT ĐỐI KHÔNG** commit chung một file `PROGRESS.md` duy nhất ở thư mục gốc trên nhiều nhánh, vì khi tạo Pull Request vào `develop` sẽ bị conflict liên tục.
> - **Cách 1 (Khuyên dùng khi cần bàn giao trên Git):** Tạo file riêng theo tên nhánh tại `progress/<ten-nhanh>.md` (thay `/` và `#` bằng `-`, ví dụ nhánh `feature/#15_liquid-glass-ui` thì tạo `progress/feature-15_liquid-glass-ui.md`).
> - **Cách 2 (Chỉ lưu trên máy cá nhân):** Thêm `PROGRESS.md` và `progress/` vào `.gitignore`.
> - Agent cập nhật sau **mỗi chức năng nhỏ**, chỉ ghi kết quả thật (log build/pytest thật), không ghi phỏng đoán.

## Task hiện tại

- Chức năng: (ví dụ: Cập nhật phễu đề xuất 2 tầng cho 435 ngành TT74)
- Nhánh: (ví dụ: `feature/#18_funnel-435-majors`)
- File tiến độ: (ví dụ: `progress/feature-18_funnel-435-majors.md`)
- Cập nhật lần cuối: (YYYY-MM-DD HH:mm – tên Agent)

## Đã xong (đã commit & pass build/test)

- (ví dụ: Đã tạo `frontend/src/data/moetMajors435.ts` đồng bộ 435 ngành từ `moet_taxonomy_tt74.json`)

## Đang dở (chưa commit hoặc đang xử lý)

- (ví dụ: Đang tích hợp bộ lọc lĩnh vực tại `Dashboard.tsx`)

## Việc tiếp theo (theo thứ tự)

1. (việc 1)
2. (việc 2)
3. Chạy `npm --prefix frontend run build` và `pytest` rồi commit theo chuẩn Conventional Commits

## Quyết định đã chốt và lưu ý

- (ví dụ: Giao diện dùng tông màu đồng nhất Sky/Cyan/Slate, phong cách Liquid Glass, không hiển thị đề xuất khi `hasCompletedAssessment === false`)

## Lỗi đang gặp (nếu có)

- (dán nguyên văn thông báo lỗi và lệnh gây ra lỗi)
