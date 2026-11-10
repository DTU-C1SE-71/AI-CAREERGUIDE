# AGENTS.md – AI CareerGuide Frontend (`frontend/`)

Frontend của hệ thống **AI CareerGuide – Tư vấn hướng nghiệp & Đề xuất ngành học XAI cá nhân hóa** (Đồ án Capstone C1SE.71 – Đại học Duy Tân), viết bằng **React 19 + TypeScript + Vite 8 + Tailwind CSS v4**.
Hãy trả lời và viết comment bằng **tiếng Việt**.

> **Nguyên tắc "Chưa chốt":** Mục nào ghi "chưa chốt" nghĩa là nhóm chưa quyết định. Agent **phải hỏi người dùng trước**, không tự ý chọn.

Hướng dẫn chi tiết được chia thành các file nhỏ trong `agents-docs/fe/`. **Đọc file liên quan đến việc đang làm trước khi bắt đầu:**

| Khi nào | Đọc file |
|---|---|
| Luôn đọc đầu tiên: stack, lệnh npm, chuẩn giao diện **Liquid Glass** & tối giản chữ | [agents-docs/fe/01-stack-va-lenh.md](fe/01-stack-va-lenh.md) |
| Gọi API (`VITE_API_BASE_URL`), Google OAuth, xử lý mã lỗi cố định, CORS | [agents-docs/fe/02-ket-noi-backend.md](fe/02-ket-noi-backend.md) |
| Làm màn hình mới, cô lập bài test theo tài khoản, lịch sử đề xuất, 435 ngành | [agents-docs/fe/03-man-hinh-va-nghiep-vu.md](fe/03-man-hinh-va-nghiep-vu.md) |
| Tạo file/thư mục mới trong `frontend/src/` | [agents-docs/fe/04-cau-truc-code.md](fe/04-cau-truc-code.md) |
| Commit, merge theo Git Flow, ghi tiến độ không conflict, hoặc nhận task dài | [agents-docs/fe/05-git-va-quy-trinh.md](fe/05-git-va-quy-trinh.md) |

## Quy tắc bắt buộc (tóm tắt)

- **Thẩm mỹ giao diện (Liquid Glass & Minimal Text):**
  - Toàn bộ giao diện tuân thủ phong cách **Liquid Glass** (kính trong suốt `bg-white/45` đến `bg-white/80`, `backdrop-blur-xl`, viền sáng `border-white/80`).
  - **Đồng bộ màu sắc:** Chỉ sử dụng dải màu chủ đạo **`Sky / Cyan / Slate`**. Không dùng quá nhiều màu sắc lòe loẹt trên cùng một màn hình.
  - **Càng ít chữ càng tốt:** Xóa bỏ mọi đoạn văn giải thích rườm rà, tiêu đề phụ thừa hoặc các mục tĩnh gây rối mắt (như lộ trình mẫu/lịch sử giả lập trên Sidebar).
- **Hiển thị đủ 435 ngành:** Mọi nhãn hiển thị, bộ lọc tra cứu và dữ liệu tĩnh (`src/data/moetMajors435.ts`) phải phản ánh đúng **435 ngành** chuẩn Bộ GD&ĐT (Thông tư 74/2026/TT-BGDĐT).
- **Cô lập dữ liệu bài test theo từng học sinh & Chặn đề xuất giả:**
  - Khi học sinh mới đăng ký hoặc đăng nhập nhưng **chưa làm bài đánh giá**, Dashboard bắt buộc hiển thị màn hình hướng dẫn bắt đầu làm bài test — **tuyệt đối không hiển thị sẵn đề xuất ngành**.
  - Lưu trữ tiến độ và lịch sử các lần làm bài tách biệt theo từng `user_id` để học sinh có thể làm lại bài test và xem lại các lần đề xuất trước đó.
- **Biến môi trường & Bảo mật:**
  - Đọc địa chỉ API từ `VITE_API_BASE_URL`, Google Client ID từ `VITE_GOOGLE_CLIENT_ID`.
  - Tuyệt đối không đặt `GOOGLE_CLIENT_SECRET`, `OPENROUTER_API_KEY`, `TAVILY_API_KEY` ở code Frontend.
- **Kiểm tra biên dịch:** Luôn chạy `npm --prefix frontend run build` (`tsc -b && vite build` đạt 0 lỗi) trước khi commit.

## Ghi tiến độ (tránh conflict khi merge)

- Không commit chung một file `PROGRESS.md` duy nhất ở gốc repo.
- Lưu tiến độ theo từng nhánh tại `progress/<ten-nhanh>.md` (ví dụ `progress/feature-liquid-glass-ui.md`) hoặc đưa vào `.gitignore`.
- Chi tiết mẫu ghi tiến độ xem tại [agents-docs/PROGRESS.md](PROGRESS.md).
