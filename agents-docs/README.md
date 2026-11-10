# Tài liệu hướng dẫn Agent – AI CareerGuide (DTU – C1SE.71)

Bộ tài liệu hướng dẫn dành cho AI Coding Agent làm việc trên dự án **AI CareerGuide – Hệ thống Hướng nghiệp & Đề xuất Ngành học XAI Cá nhân hóa cho Học sinh THPT Việt Nam** (Capstone Project 1 – CMU-SE 450 – Nhóm C1SE.71).

Tài liệu được chia nhỏ theo từng chủ đề Backend (`be/`) và Frontend (`fe/`) để Agent tra cứu nhanh, chính xác và không làm sai lệch kiến trúc.

## File dùng chung

| File | Nội dung |
|---|---|
| [AGENTS.md](AGENTS.md) | Bản điều phối cho Backend (`backend/`), trỏ tới `be/` |
| [AGENTS_FE.md](AGENTS_FE.md) | Bản điều phối cho Frontend (`frontend/`), trỏ tới `fe/` |
| [AGENTS_TONG_HOP.md](AGENTS_TONG_HOP.md) | Bản gộp đầy đủ toàn bộ quy tắc BE + FE + Git Flow trong 1 file duy nhất |
| [PROGRESS.md](PROGRESS.md) | Mẫu ghi tiến độ theo từng nhánh (`progress/<ten-nhanh>.md`) để bàn giao giữa các phiên mà không gây conflict khi merge |

## Backend (`be/`) – Python 3.11 + FastAPI + PostgreSQL/pgvector

| File | Nội dung |
|---|---|
| [01-stack-va-lenh.md](be/01-stack-va-lenh.md) | Stack FastAPI, SQLAlchemy 2.0 Async, LlamaIndex Dual-RAG, lệnh chạy & các mục "chưa chốt" |
| [02-dung-moi-truong.md](be/02-dung-moi-truong.md) | Dựng môi trường macOS/Windows/Docker, tách biệt DB Test (`ENVIRONMENT=test`), bảng lỗi thường gặp |
| [03-database.md](be/03-database.md) | Cấu trúc 7 module DB, 435 ngành Thông tư 74/2026/TT-BGDĐT, quy tắc migration theo timestamp & múi giờ |
| [04-nghiep-vu-srs.md](be/04-nghiep-vu-srs.md) | Công thức XAI 3 trụ cột ($0.45, 0.35, 0.20$), Phễu 2 tầng, Solution B (Target/Reach), quy trình HITL Staging |
| [05-bao-mat-va-cau-truc.md](be/05-bao-mat-va-cau-truc.md) | Bảo mật Zero-PII (Luật 91/2025 & NĐ 13/2023), Argon2id, tách Pydantic Schema, mã lỗi cố định & cấu trúc thư mục |
| [06-git-va-quy-trinh.md](be/06-git-va-quy-trinh.md) | Quy trình Git Flow (`develop`, `feature/*`), quản lý tiến độ không conflict & chia nhỏ task |

## Frontend (`fe/`) – React 19 + TypeScript + Vite 8 + Tailwind CSS v4

| File | Nội dung |
|---|---|
| [01-stack-va-lenh.md](fe/01-stack-va-lenh.md) | Stack React 19 + TypeScript + Vite, lệnh npm, quy chuẩn thiết kế **Liquid Glass** & tối giản chữ |
| [02-ket-noi-backend.md](fe/02-ket-noi-backend.md) | Biến môi trường `VITE_API_BASE_URL`, Google OAuth (`client-id` vs `secret`), tiền tố `/api/v1`, xử lý mã lỗi |
| [03-man-hinh-va-nghiep-vu.md](fe/03-man-hinh-va-nghiep-vu.md) | Phạm vi màn hình, cô lập dữ liệu bài test theo từng học sinh, chặn đề xuất khi chưa làm test, lịch sử làm bài |
| [04-cau-truc-code.md](fe/04-cau-truc-code.md) | Cấu trúc thư mục `frontend/src/`, quy ước đặt tên Component, Hook, Context, Service |
| [05-git-va-quy-trinh.md](fe/05-git-va-quy-trinh.md) | Quy tắc Git Flow, kiểm tra `npm run build` trước khi commit, quản lý file tiến độ theo nhánh |
