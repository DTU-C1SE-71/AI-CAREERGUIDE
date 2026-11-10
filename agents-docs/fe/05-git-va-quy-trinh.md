# FE – Quy trình Git Flow, Kiểm tra Build & Quản lý tiến độ

## 1. Quy tắc Git Flow

- Nhánh tích hợp phát triển chung là **`develop`**. Nhánh phát hành chính thức là **`main`**.
- **Không push thẳng lên `main` hoặc `develop`**. Mọi thay đổi giao diện hay tính năng mới phải tạo nhánh riêng từ `develop` (`feature/#<issue>_<mo-ta>` hoặc `bugfix/#<issue>_<mo-ta>`), sau đó mở Pull Request vào `develop`.
- **Trước khi tạo PR hoặc merge:**
  1. Kéo `develop` mới nhất về nhánh đang làm (`git pull dtu develop`) và giải quyết hết conflict.
  2. Chạy lệnh kiểm tra biên dịch TypeScript & Vite:
     ```bash
     npm --prefix frontend run build
     ```
  3. Chỉ commit và đẩy code khi lệnh `build` báo thành công (`✓ built in ...`, **0 lỗi TypeScript**).
- Commit message bắt buộc tuân theo chuẩn Conventional Commits (`feat(ui): ...`, `fix(auth): ...`, `style(dashboard): ...`, `refactor: ...`) để vượt qua `.githooks/commit-msg`.

## 2. Quản lý file tiến độ không gây Conflict (`progress/<ten-nhanh>.md`)

- **Tuyệt đối không commit chung một file `PROGRESS.md` ở gốc repo** trên nhiều nhánh vì sẽ gây conflict liên tục khi merge vào `develop`.
- Lưu tiến độ riêng theo từng nhánh tại `progress/<ten-nhanh>.md` (ví dụ `progress/feature-liquid-glass-ui.md`) hoặc thêm vào `.gitignore`.

## 3. Khi làm việc với các Task giao diện lớn

1. Trước khi sửa nhiều màn hình, liệt kê rõ danh sách các file sẽ chỉnh sửa để người dùng xác nhận.
2. Luôn đối chiếu 3 tiêu chí nghiệm thu UI của dự án sau mỗi lần sửa:
   - Đúng hiệu ứng kính lỏng **Liquid Glass** (`backdrop-blur`, viền trắng sáng).
   - Đồng bộ tông màu **`Sky / Cyan / Slate`**, không pha tạp nhiều màu gây rối mắt.
   - **Tối giản chữ tối đa**, xóa bỏ các nhãn/hộp thông tin thừa và hiển thị đúng con số **435 ngành**.
3. Chạy `npm --prefix frontend run build` xác nhận không có biến thừa (`noUnusedLocals`) trước khi commit.
