# AGENTS.md – Tài Liệu Hướng Dẫn Agent Tổng Hợp (AI CareerGuide – C1SE.71)
> **Dự án:** AI CareerGuide – Hệ thống Hướng nghiệp & Đề xuất Ngành học XAI Cá nhân hóa cho Học sinh THPT Việt Nam  
> **Đơn vị:** Capstone Project 1 (CMU-SE 450 – Nhóm C1SE.71 – Đại học Duy Tân)  
> **Ngôn ngữ giao tiếp & tài liệu:** Tiếng Việt.  
> **Nguyên tắc "Chưa chốt":** Mọi hạng mục đánh dấu **"Chưa chốt"** (thay đổi trọng số toán học 3 trụ cột, thêm bảng ngoài 7 phân hệ DB, đổi LLM provider...) thì Agent **bắt buộc phải hỏi người dùng trước**, tuyệt đối không tự ý quyết định.

---

## 1. Kiến Trúc & Công Nghệ Đã Chốt (Tech Stack)

### 1.1. Backend (`backend/`)
- **Ngôn ngữ & Framework:** Python **3.11+**, **FastAPI**, ASGI server **Uvicorn**.
- **ORM & CSDL:** **SQLAlchemy 2.0 Async** (`asyncpg` cho **PostgreSQL 16 + `pgvector`**, `aiosqlite` cho môi trường dev nhẹ và test cô lập).
- **Xác thực & Bảo mật:** Băm mật khẩu chuẩn **Argon2id**, xác thực **JWT Bearer Token**, tích hợp **Google OAuth 2.0**, tuân thủ bảo vệ dữ liệu cá nhân theo **Luật 91/2025/QH15** và **Nghị định 13/2023/NĐ-CP** (Zero-PII Guardrails).
- **AI & Dual-RAG:** **LlamaIndex** + OpenRouter/Qwen3-VL (Stream A: OCR Thông tư PDF, sinh giải thích XAI) + **Tavily API** (Stream B: khám phá học liệu từ danh sách tên miền học thuật trắng).
- **Danh mục ngành chuẩn:** **435 ngành đào tạo cấp IV** theo Thông tư **`74/2026/TT-BGDĐT`** (`backend/app/db/seeds/moet_taxonomy_tt74.json`).

### 1.2. Frontend (`frontend/`)
- **Framework:** **React 19 + TypeScript 5.8+ + Vite 8**.
- **Giao diện & Hoạt ảnh:** **Tailwind CSS v4**, **Framer Motion**, **Lucide React**, **React Router v7**.
- **Phong cách thiết kế bắt buộc:** **Liquid Glass** (kính trong suốt `backdrop-blur-xl`, nền `bg-white/45`–`bg-white/80`, viền `border-white/80`), đồng bộ bảng màu **`Sky / Cyan / Slate`**, **càng ít chữ càng tốt** (xóa bỏ mọi nhãn/hộp giải thích thừa gây rối mắt).
- **Biến môi trường chuẩn:** `VITE_API_BASE_URL` và `VITE_GOOGLE_CLIENT_ID`.

---

## 2. Lệnh Thường Dùng & Tách Biệt Môi Trường Test

### 2.1. Backend
```bash
cd backend
pip install -r requirements.txt
python -m scripts.init_db                        # Khởi tạo DB & nạp 435 ngành TT74/2026
uvicorn app.main:app --reload --port 8000        # Chạy server dev tại http://localhost:8000
python -m pytest tests/ -v                       # Chạy bộ Pytest trên DB Test cô lập
```
- **Tách Database Test:** Khi chạy `pytest`, bắt buộc dùng `ENVIRONMENT=test` với SQLite in-memory (`sqlite+aiosqlite:///:memory:`) hoặc DB test riêng (`careerguide_test`), tuyệt đối không chạy test đè lên DB dev/production.

### 2.2. Frontend
```bash
npm --prefix frontend install                    # Cài đặt thư viện
npm --prefix frontend run dev                    # Chạy dev tại http://localhost:5173
npm --prefix frontend run build                  # Kiểm tra TypeScript (tsc -b) & build Vite
```

---

## 3. Quy Tắc Nghiệp Vụ & Bảo Mật Cốt Lõi (SRS)

1. **Động cơ Khuyến nghị XAI Tất định 3 Trụ cột ($0.45, 0.35, 0.20$):**
   $$S(u, m) = 100 \times \left( 0.45 \cdot S_{\text{RIASEC}}(u, m) + 0.35 \cdot S_{\text{Academic}}(u, m) + 0.20 \cdot S_{\text{Cognitive}}(u, m) \right)$$
   - Tính toán hoàn toàn bằng toán học tất định ở Backend (`recommender/engine.py`), **tuyệt đối không để LLM tự chấm điểm hay tự xếp hạng ngành**.
2. **Mô hình Phễu 2 Tầng & Phân tầng Khả thi (`TARGET` / `REACH`):**
   - **Tầng 1:** Top 3 Lĩnh vực đào tạo phù hợp nhất.
   - **Tầng 2:** Top 2–3 Ngành đào tạo mã cấp IV trong từng lĩnh vực kèm nhãn `TARGET` (Khả thi cao) hoặc `REACH` (Thử thách).
3. **Chặn đề xuất khi chưa làm bài test & Cô lập dữ liệu theo `user_id`:**
   - Khi học sinh mới đăng nhập nhưng chưa hoàn thành bài trắc nghiệm (`hasCompletedAssessment === false`), **tuyệt đối không hiển thị sẵn đề xuất ngành**.
   - Dữ liệu bài làm và **Lịch sử các lần đề xuất trước đó** được cô lập riêng theo từng `user_id` để học sinh có thể làm lại bài test và xem lại lịch sử bất cứ lúc nào.
4. **Zero-PII & Tách bạch DTO Học sinh / Quản trị viên:**
   - Khử toàn bộ thông tin định danh cá nhân (họ tên, email, SĐT, trường lớp) trước khi gọi LLM/Tavily.
   - Tách riêng DTO/Schema của `STUDENT` và `ADMIN`; không cho phép tự đăng ký quyền `ADMIN` qua API công khai.
5. **Kiểm duyệt HITL Staging (FR07):**
   - Dữ liệu nạp từ Stream A (OCR) và Stream B (Tavily) phải lưu ở trạng thái `PENDING` trong bảng `staging_records`, chỉ xuất bản khi `ADMIN` duyệt (`APPROVED`).
6. **Mã lỗi HTTP cố định:**
   - `400 DU_LIEU_KHONG_HOP_LE`, `401 CHUA_XAC_THUC`, `403 KHONG_DU_QUYEN_ADMIN`, `404 KHONG_TIM_THAY_NGANH`, `409 EMAIL_DA_TON_TAI`, `422 CHUA_HOAN_THANH_BAI_TEST`.

---

## 4. Quy Trình Git Flow & Quản Lý Tiến Độ Không Conflict

1. **Nhánh Git Flow:**
   - `main`: Chỉ chứa code phát hành chính thức (cấm commit trực tiếp).
   - `develop`: Nhánh tích hợp phát triển chung.
   - `feature/#<issue>_<mo-ta>`, `bugfix/#<issue>_<mo-ta>`: Tách từ `develop`, mở Pull Request về `develop`.
   - `release/<version>`, `hotfix/<version>_<mo-ta>`: Chốt phiên bản / vá lỗi khẩn cấp, merge vào cả `main` và `develop` kèm tag `vX.Y.Z`.
2. **Commit Message (Kiểm tra bởi `.githooks/commit-msg`):**
   - Bắt buộc dùng tiền tố `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`, `style:`, `perf:`.
3. **Ghi tiến độ không gây conflict khi merge (`progress/<ten-nhanh>.md`):**
   - **Cấm commit chung một file `PROGRESS.md` duy nhất ở gốc repo** trên nhiều nhánh.
   - Mỗi nhánh lưu file riêng tại `progress/<ten-nhanh>.md` (ví dụ `progress/feature-18_funnel-435-majors.md`) hoặc đưa vào `.gitignore`.
