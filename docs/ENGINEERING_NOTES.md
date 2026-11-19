# AI CareerGuide — Nhật ký Kỹ thuật, Giải pháp & Công nghệ (Engineering Notes)

> Tài liệu tổng hợp toàn bộ các tính năng đã triển khai, giải pháp kỹ thuật, công nghệ sử dụng và tệp liên quan để dễ tra cứu, bảo trì và báo cáo dự án.

---

## Tổng quan Công nghệ Cốt lõi (Tech Stack)
- **Frontend:** React 19 + TypeScript + Vite 8 + Tailwind CSS + Framer Motion + Lucide Icons + Recharts (deploy trên **Vercel**).
- **Backend:** FastAPI + SQLAlchemy 2.0 Async + Pydantic v2 + Argon2id + JWT HS256 (deploy trên **Render**).
- **Database:** PostgreSQL 16 + `pgvector` (và SQLite `aiosqlite` cho unit/integration tests cách ly).
- **AI / LLM:** OpenAI-compatible API (`https://api.xkiro.com/v1`, model `mistralai/mistral-medium-3.5`) + Tavily Search + Guardrails tất định 3 lớp.

---

## Nhật ký Tính năng & Quyết định Kỹ thuật

### 1. Bộ 38 câu hỏi Hướng nghiệp 100% Trải nghiệm Học sinh THPT
- **Vấn đề:** Bộ câu hỏi dịch nguyên bản từ O*NET chứa đầu việc công sở/nhà máy khiến học sinh THPT chọn "Phân vân (3)" hàng loạt (mù trải nghiệm), làm dẹt biểu đồ lục giác RIASEC.
- **Giải pháp:** Thiết kế lại toàn bộ **30 câu RIASEC + 8 câu Nhận thức** gắn 100% với đời sống học đường, ở nhà và hoạt động nhóm; loại bỏ bẫy giải trí thụ động (Ceiling Effect) và bẫy áp lực đạo đức.
- **Tệp liên quan:**
  - `frontend/src/data/onetMiniIpQuestions.ts`
  - `frontend/src/data/cognitiveQuestions.ts`
  - `backend/app/db/seeds/assessment_questions_v1_8.json`
  - `backend/app/db/seeds/seed_assessment_questions.py`

### 2. Tách riêng **Khám phá ngành** (`/dashboard`) và **Danh mục ngành** (`/majors`)
- **Vấn đề:** Trang cũ gộp chung phần đề xuất cá nhân hóa và bảng tra cứu 435 ngành gây rối mắt; ngoài ra người dùng đã có dữ liệu bài test trong DB nhưng chưa hiện kết quả đề xuất sau khi đăng nhập lại.
- **Giải pháp:**
  - Tách `/majors` (`MajorsCatalog.tsx`) chứa toàn bộ 435 ngành chuẩn Bộ GD&ĐT (tìm kiếm theo mã/tên + lọc lĩnh vực).
  - Mở rộng `GET /api/assessment/profile` để hydrate đầy đủ câu trả lời RIASEC, tư duy, điểm số và nguyện vọng từ DB vào `AssessmentContext`.
  - Xóa hiển thị phần trăm trọng số tĩnh `45% / 35% / 20%` (vì hệ thống đã dùng trọng số động theo khối lớp & dữ liệu hồ sơ).
  - Tinh gọn UX Trắc nghiệm: bỏ thanh "Chế độ xem lại", đổi nút góc trên trái thành nút **Quay lại** về cổng chọn làm mới / xem lại.
- **Tệp liên quan:**
  - `frontend/src/pages/MajorsCatalog.tsx`, `frontend/src/pages/Dashboard.tsx`, `frontend/src/pages/AssessmentWizard.tsx`
  - `frontend/src/context/AssessmentContext.tsx`, `frontend/src/hooks/useSelectedAssessment.ts`
  - `backend/app/services/assessment/service.py`

### 3. Tối ưu Responsive đa màn hình & Thanh cuộn ngang AI Chatbox
- **Vấn đề:** Nội dung dài (code/bảng) trong AI Chatbox bị tràn khung; một số thẻ bị chật trên màn hình laptop nhỏ / mobile.
- **Giải pháp:** Bổ sung `overflow-x-auto` cho block nội dung dài trong `AIChatAdvisor.tsx` & `index.css`; tối ưu lưới responsive trên `MainLayout`, `PageContainer`, `RiasecRadarChart`, `TwoTierFunnelRecommendation`, `AspirationAlignmentCard`, `SkillAnalysisCard`.

### 4. Tách chế độ **Thuật toán đề xuất** (tức thì) vs **Đề xuất ngành có AI** (On-Demand + Smart Cache)
- **Vấn đề:** Gọi AI phân tích ngay khi mở trang làm thời gian tải lâu (5–15 giây) và tốn token ngay cả khi người dùng chỉ xem kết quả thuật toán hoặc mở lại lịch sử cũ.
- **Giải pháp & Công nghệ:**
  - **2 chế độ tách biệt trên `/dashboard`:**
    1. **Thuật toán đề xuất** *(mặc định · Tức thì · 0 AI)*: Chạy 100% toán học tất định (`/recommender/evaluate`).
    2. **Đề xuất ngành có AI** *(On-Demand)*: Chỉ gọi `/major-insights/student-skills` khi người dùng chủ động bấm mở.
  - **Khóa cache thông minh (Smart Cache Key — SHA-256):** Băm toàn bộ yếu tố ảnh hưởng thuật toán (`owner`, `riasec_answers`, `riasec_scores`, `grades_by_subject`, `cognitive_preferences`, `aspiration`, `grade_level`, `gender`, `major_code`, `catalog_context`) lưu vào bảng `student_skill_insights`. Mở lại đúng hồ sơ cũ đọc thẳng DB (**0 token**, hiển thị badge *"Đã tải từ lịch sử CSDL · 0 token"*); chỉ gọi lại AI khi có yếu tố đầu vào thay đổi.
  - **Chống bấm đúp 2 lớp (Idempotency):**
    - Backend: `asyncio.Lock` theo từng `(profile_hash, major_code)` qua `weakref.WeakValueDictionary` (request thứ 2 chờ request 1 lưu DB xong rồi đọc cache).
    - Frontend: `inFlightAiFingerprintRef` + khóa nút bấm + hiển thị rõ trạng thái **`AI đang phân tích...`** kèm spinner (`Loader2`).
- **Tệp liên quan:**
  - `backend/app/services/major_insight/router.py`, `backend/app/services/major_insight/service.py`
  - `frontend/src/pages/Dashboard.tsx`, `frontend/src/components/xai/SkillAnalysisCard.tsx`, `frontend/src/components/xai/AspirationAlignmentCard.tsx`

### 5. Trợ lý AI hỗ trợ sử dụng hệ thống & Bảo mật 3 lớp (Chống Prompt Injection)
- **Vấn đề:** Người dùng hỏi cách sử dụng hệ thống (như *"web này là gì"*, *"cách kiểm tra hồ sơ"*, *"cách kiểm sử dụng web này"*) bị từ chối nhầm; đồng thời cần ngăn tuyệt đối việc AI tiết lộ thông tin nội bộ (DB schema, API endpoints, mã nguồn, system prompt, API key, dữ liệu người khác).
- **Giải pháp & Công nghệ:**
  - **Lớp 1 — Bộ chặn tiền xử lý (`forbidden_request`, 0 token):** Chặn ngay trước khi gọi LLM đối với các câu hỏi dò DB schema, tên bảng/cột, endpoint, source code, system prompt, API key/JWT/mật khẩu admin, cấu hình server, lỗ hổng/cơ chế kiểm duyệt, prompt injection và giả danh quản trị viên; trả đúng mẫu câu từ chối chuẩn (`SECURITY_REFUSAL`).
  - **Lớp 2 — Bộ phân loại tổ hợp (`chat_scope.py`):** Phân loại theo tổ hợp `[Thực thể giao diện / Tính năng] + [Hành động / Câu hỏi]` để hiểu mọi cách hỏi tự nhiên tiếng Việt (kể cả câu ngắn hoặc gõ dư chữ) mà không bắt nhầm câu hỏi học tập/lập trình hoặc câu hỏi phân tích dữ liệu hồ sơ cá nhân.
  - **Lớp 3 — Hướng dẫn công khai + Phòng thủ chiều sâu (`system_help.py`, `guidance_rag.py`):** Cung cấp bản đồ menu/nút bấm công khai (có fallback offline từng bước) và nhúng `SECURITY_BOUNDARIES_PROMPT` vào toàn bộ các chế độ prompt LLM.
- **Kiểm thử:** `backend/tests/test_system_help_and_security.py` (149/149 test pass cùng bộ scope/boundary hiện có).

### 6. Chính sách mật khẩu mạnh + Xác nhận Email OTP (Đăng ký) + Quên/Đặt lại mật khẩu
- **Giải pháp & Công nghệ:**
  - **Chính sách mật khẩu mạnh (5 tiêu chí):** `>= 8` ký tự, chữ hoa `A-Z`, chữ thường `a-z`, chữ số `0-9`, ký tự đặc biệt — kiểm tra đồng bộ bằng Pydantic validator ở Backend và realtime checklist 5 tiêu chí + nút hiện/ẩn mật khẩu ở Frontend.
  - **Email OTP 6 chữ số bảo mật cao:**
    - Sinh mã ngẫu nhiên an toàn bằng `secrets.randbelow(1_000_000)`.
    - Lưu mã bằng **HMAC-SHA256** (dùng `SECRET_KEY`) vào bảng `email_verification_codes` (migration `20261119_005_email_otp`); mật khẩu chờ kích hoạt đăng ký được băm **Argon2id** ngay lập tức (không bao giờ lưu plaintext OTP hay plaintext password).
    - Hiệu lực **10 phút**, tối đa **5 lần nhập sai** (tự hủy mã), **cooldown 60 giây** (`HTTP 429`) chống spam.
    - Quên mật khẩu phản hồi trung tính (anti-enumeration), cập nhật mật khẩu mới bằng Argon2id và vô hiệu hóa mã OTP ngay sau khi dùng.
  - **Dịch vụ gửi Email đa kênh + Tự động fallback (`email_service.py`):**
    - Ưu tiên **SMTP** (ví dụ Gmail App Password qua `smtplib` chạy trong `asyncio.to_thread` để không block event loop — gửi được tới mọi email học sinh mà không cần mua domain riêng).
    - Hỗ trợ **Resend HTTP API** (`httpx.AsyncClient`), tự động fallback giữa SMTP $\leftrightarrow$ Resend nếu cấu hình cả hai, tự tránh lỗi gửi từ `@gmail.com` qua Resend, và trả thông báo rõ ràng nếu Resend ở chế độ dùng thử (chưa verify domain).
- **Tệp liên quan:**
  - `backend/app/core/email_service.py`, `backend/app/core/config.py`
  - `backend/app/models/identity.py`, `backend/app/db/migrations.py`
  - `backend/app/schemas/identity.py`, `backend/app/services/identity/service.py`, `backend/app/services/identity/router.py`
  - `frontend/src/utils/passwordPolicy.ts`, `frontend/src/pages/Login.tsx`
  - `backend/tests/test_email_otp_and_password_policy.py` (51/51 auth & OTP tests passed).

### 7. Hạ tầng Deploy (Vercel + Render + PostgreSQL)
- **Vercel (`frontend/vercel.json`):** Thêm rewrite `/api/(.*)` $\rightarrow$ `https://ai-careerguide-bny3.onrender.com/api/$1` để gọi API same-origin (không lỗi 404/CORS).
- **Frontend API Timeout (`frontend/src/services/api.ts`):** Tăng timeout mặc định từ `20s` lên `45s` và xử lý riêng `TIMEOUT` để tránh lỗi `signal is aborted without reason` khi Render gói Free cold-start.
- **Render (`render.yaml`):** Cập nhật `startCommand` thành `python scripts/init_db.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT` để tự chạy migration cộng thêm idempotent mỗi lần deploy; cập nhật biến `LLM_BASE_URL`, `LLM_MODEL`, `CORS_ORIGINS`, `SECRET_KEY` riêng $\ge 32$ ký tự và các biến Email (`SMTP_*` / `RESEND_API_KEY`).
