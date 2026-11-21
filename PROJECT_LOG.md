# AI CareerGuide — Project Context & Engineering Log (AI-Readable)

> **Mục đích file:** Tài liệu nhật ký tập trung, tối ưu để bất kỳ AI / lập trình viên nào đọc vào đầu phiên làm việc mới đều nắm ngay kiến trúc, quy ước bất biến, lịch sử thay đổi theo commit và quy trình kiểm thử/triển khai của dự án **AI CareerGuide**.
>
> **Cập nhật lần cuối:** 2026-11-21 (HEAD trước commit tạo log: `d42f2ce`, nhánh `develop`)
> **Tài liệu kỹ thuật chi tiết đi kèm:** `docs/ENGINEERING_NOTES.md`, `docs/AUDIT_AND_HANDOFF_REPORT.md`, `AGENTS.md`

---

## 1. Tổng quan Dự án & Hạ tầng Triển khai

- **Tên hệ thống:** AI CareerGuide — Hệ thống Tư vấn Hướng nghiệp & Gợi ý 435 Ngành đào tạo (theo Thông tư 74/2026/TT-BGDĐT & Thông tư 09).
- **Tech Stack:**
  - **Frontend:** React 19 + TypeScript + Vite 8 + Tailwind CSS v4 + Framer Motion + Recharts (`frontend/`).
  - **Backend:** FastAPI + Python 3.11/3.12 + SQLAlchemy Async + Pydantic v2 + Argon2id + PyJWT (`backend/`).
  - **Database:** PostgreSQL (`Supabase`, Project ID `uwggiegmkwfayeutjrty`) trên production; SQLite (`backend/app/db/careerguide_active.db`) cho chạy thử cục bộ.
  - **AI / Search:** Cấu hình LLM Runtime động (OpenAI-compatible / Gemini / OpenRouter qua `ai_config`, mã hóa API key bằng Fernet) + Tavily Search cho Trend Discovery & HITL RAG.
- **Hạ tầng Production:**
  - **Frontend (Vercel):** `https://ai-careerguide-ten.vercel.app` (proxy `/api/*` sang Render qua `frontend/vercel.json`, timeout mặc định 45s cho cold-start).
  - **Backend (Render Free):** `https://ai-careerguide-bny3.onrender.com` (`startCommand`: `python scripts/init_db.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT`).
  - **Email OTP:** Dùng **Google Apps Script HTTPS Webhook** (cổng `443`, tránh giới hạn chặn SMTP của Render Free) qua `MAIL_WEBHOOK_URL` & `MAIL_WEBHOOK_SECRET`, có dự phòng Brevo / SMTP / Resend.
- **Quy trình Git & Đồng bộ thư mục (BẮT BUỘC):**
  - Workspace chính: `e:\CMU-SoftWareEngineering\CAPSTONE PROJECT\capstone 1\AI_CAREERGUIDE` (nhánh làm việc: `develop`).
  - Thư mục bản sao đồng bộ: `e:\CMU-SoftWareEngineering\CAPSTONE PROJECT\capstone 1\AI_CAREERGUIDE_1` — **mọi tệp chỉnh sửa cần được sao chép đồng bộ sang thư mục này**.
  - Đẩy triển khai Vercel/Render qua remote `personal`: `git push personal develop:main` (`https://github.com/ntanduy25/ai-careerguide_2.git`).

---

## 2. Quy ước Kiến trúc & Nguyên tắc Bất biến (AI KHÔNG ĐƯỢC PHÁ VỠ)

1. **Hệ màu thương hiệu (Color Lock):**
   - Toàn bộ giao diện dùng hệ **Sky (`#0284c7` / `#0ea5e9`) + Slate**, chỉ dùng Emerald/Amber/Rose cho trạng thái cảnh báo/đạt chuẩn. **Không sử dụng màu `indigo` tím xanh** trên Dashboard, Auth và các thẻ XAI.
2. **Trắc nghiệm 3 bước (`/assessment`):**
   - Chỉ gồm **3 bước**: `1. Sở thích` (30 câu Holland RIASEC bối cảnh học đường THPT) $\rightarrow$ `2. Tư duy` (8 câu tình huống nhận thức) $\rightarrow$ `3. Điểm số`.
   - **Không thêm lại** bước `4. Nguyện vọng` (đã tách sang tab `Nguyện vọng với AI` trên `/dashboard`), nút chuyển `Khung hiển thị`, hay nút `Hướng dẫn làm bài`.
   - Khung hiển thị cố định rộng rãi (`max-w-4xl xl:max-w-5xl`), nút `Quay lại` nằm ngang hàng nhưng **tách biệt khối** bên trái thanh bước.
   - Toàn bộ **30 ảnh minh họa RIASEC** lưu tĩnh cục bộ tại `frontend/public/images/assessment/R1.jpg`..`C5.jpg` (tỷ lệ 2:1 `960×480`, không dùng link Unsplash ngoài dễ lệch chủ đề hoặc chậm tải).
3. **Khám phá Ngành (`/dashboard` — 2 Tab tách biệt):**
   - **Tab 1 — `Đề xuất theo hồ sơ` (Mặc định):** Hồ sơ Định hướng (Radar + Top Holland + Khối thi tốt nhất) + Phễu 2 tầng (`TwoTierFunnelRecommendation`) ở phía trên; `SkillAnalysisCard` (lưới 2 cột, mặc định 2 mục + nút xem thêm) ngay phía dưới; đợi `/recommender/evaluate` xong mới gọi `/major-insights/student-skills`.
   - **Tab 2 — `Nguyện vọng với AI`:** Gọi `POST /api/v1/major-insights/aspiration-ai`, hiển thị `AspirationAlignmentCard` (đã bỏ lặp `HollandInterestSummary`, giữ nút `Đổi nghề mơ ước` và mục `Gợi ý các ngành phù hợp hơn với hồ sơ của bạn`).
   - Nút tab giữ tối giản (chỉ tên tab + icon, **không thêm chip phụ chữ nhỏ** hay dòng mô tả dài bên phải).
   - Giữ nguyên `data-testid="profile-recommendation-context"` trên `TwoTierFunnelRecommendation.tsx` cho E2E test.
4. **Lộ trình học 4 tuần (`/roadmap`):**
   - Đang ở trạng thái **`Coming Soon`** (Sidebar ghi `Lộ trình học` kèm chip `Soon`; trang `/roadmap` và thẻ/nút trên `/majors/:code` đều hiển thị Coming Soon).
5. **Smart DB Cache & Evidence Boundary (`backend/app/services/major_insight/service.py`):**
   - Phân tích kỹ năng (`/student-skills`) **phải tính điểm Holland từ `riasec_answers`** qua `_format_riasec_summary_from_payload` (không chỉ đọc `riasec_scores` vốn rỗng khi frontend gửi raw answers). Cache policy hiện tại: `evidence-skills-v4` trong bảng `student_skill_insights`.
   - Phân tích nguyện vọng AI (`/aspiration-ai`) dùng chung bảng `student_skill_insights` (không cần migration mới) với `major_code = "ASPIRATION_AI"`, `model_name = "aspiration-ai-v1:<FIT_LEVEL>"`.
   - Khi hồ sơ rỗng (`riasec_*` và `grades_by_subject` trống), **không gọi LLM** và trả mảng rỗng `strengths = []`, `weaknesses = []`, `skill_gaps = []`.
   - **Sub-facet Veto Gate (PA 3):** Khi nguyện vọng bị `STRONG_VETO`, AI không được tự nâng `fit_level` lên `"HIGH"` (khóa ở `"LOW"`), và `better_majors` **chỉ được chọn mã ngành 7 số có thật** trong danh sách ứng viên từ hệ thống.
6. **Trend Discovery Agent (`Zero Fabrication`):**
   - `backend/app/services/recommender/trend_agent.py` **tuyệt đối không** bốc ngành có sẵn từ DB hay bịa nguồn bài báo. Chỉ chấp nhận ngành xuất hiện trực tiếp trong ít nhất 1 bài báo thực (`evidence_score >= 2.0`, khớp biên từ chặt); nếu không có ngành khớp trả `status: "no_matching_majors"`, `trending_majors: []`.
7. **Bảo mật & Tài khoản Admin:**
   - Không hardcode mật khẩu Admin hay API key trong code git.
   - Enum quyền trong DB (`user_role_enum`) là chữ **IN HOA**: `'STUDENT'`, `'ADMIN'`.
   - Mật khẩu lưu bằng **Argon2id** (`backend/app/core/security.py`), không bao giờ ghi plaintext vào `hashed_password`.
   - Hỗ trợ bootstrap Admin trên Render qua biến môi trường trong `backend/scripts/init_db.py`: `BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_PASSWORD`, `BOOTSTRAP_ADMIN_NAME`, `BOOTSTRAP_ADMIN_RESET_PASSWORD`.
8. **Responsive đa màn hình (Laptop vs Màn hình rời):**
   - Laptop (Scale 125%–150%, viewport thực ~`1280×600`): Sidebar mở rộng `244px` (`MainLayout` `paddingLeft: 260`), khung ảnh RIASEC co giãn theo chiều cao `h-[clamp(132px,22vh,235px)]` để vừa khít 1 màn hình không cần cuộn ở từng câu.
   - Màn hình rời (1920×1080+, Scale 100%): `index.css` nâng `html font-size` tối thiểu `17px` ($\ge 1600\times 850$) và `17.5px` ($\ge 1900\times 920$).

---

## 3. Bản đồ các Tệp Cốt lõi (Core File Map)

### Backend (`backend/`)
| Đường dẫn | Vai trò chính |
| :--- | :--- |
| `app/main.py` | Khởi tạo FastAPI, CORS, mount các router `/api/v1/*`. |
| `app/models/identity.py` | ORM `User` (`UserRole`: `STUDENT`/`ADMIN`), `UserConsent`, `StudentAssessment`, `StudentGrade`. |
| `app/models/insight.py` | ORM `MajorInsight`, `StudentSkillInsight` (cache kỹ năng + `ASPIRATION_AI`), `MajorExplanationInsight`. |
| `app/core/security.py` | Hash/verify mật khẩu Argon2id (OWASP ASVS L2), JWT HS256. |
| `app/core/email_service.py` | Gửi OTP qua Google Apps Script Webhook / Brevo / SMTP / Resend. |
| `app/services/recommender/service.py` | Engine đề xuất 3 trụ cột + HA-GAE v3.1 + Sub-facet Veto Gate (PA 3) + `evaluate_dashboard_profile_bundle`. |
| `app/services/recommender/aspiration_agent.py` | Đối chiếu nguyện vọng nghề nghiệp trên 44 nghề chuẩn & nhóm ngành 4 số, cảnh báo xung đột sở thích. |
| `app/services/recommender/trend_agent.py` | Agent săn ngành xu hướng theo nguyên tắc Zero-Fabrication. |
| `app/services/recommender/readiness.py` | `build_interest_evidence`, `validate_readiness_grades`, `evaluate_current_readiness`. |
| `app/services/major_insight/service.py` | `analyze_student_skills` (`evidence-skills-v4`) & `analyze_aspiration_with_ai` (`aspiration-ai-v1`). |
| `app/services/major_insight/router.py` | Endpoints `GET /major-insights/{code}`, `POST /student-skills`, `POST /aspiration-ai`. |
| `app/schemas/insight.py` | Schemas `StudentSkillAnalysis*`, `AspirationAIAnalysis*`, `AspirationMajorSuggestion`. |
| `scripts/init_db.py` | Chạy migration tự động (timeout 20s) + `bootstrap_admin_from_env()` khi khởi động Render. |
| `scripts/create_admin.py` | CLI tạo tài khoản Admin thủ công trên terminal máy chủ. |

### Frontend (`frontend/`)
| Đường dẫn | Vai trò chính |
| :--- | :--- |
| `src/index.css` | Token bảng màu Sky + Slate, `.glass-card`, fluid root `font-size` cho Laptop & Màn hình rời. |
| `src/components/layout/MainLayout.tsx` | Khung ứng dụng chính, điều chỉnh `paddingLeft` (`260`/`84`), nút mở `Cố vấn AI`. |
| `src/components/layout/Sidebar.tsx` | Menu điều hướng (`244px` mở / `68px` thu gọn), badge `Soon` cho `Lộ trình học`. |
| `src/pages/AssessmentWizard.tsx` | Trắc nghiệm 3 bước (`Sở thích`, `Tư duy`, `Điểm số`), cố định khung rộng rãi. |
| `src/data/onetMiniIpQuestions.ts` | Bộ 30 câu hỏi RIASEC học đường THPT + đường dẫn ảnh tĩnh `/images/assessment/*.jpg` + `iconKey`. |
| `src/components/assessment/OnetSwipeCardVisual.tsx` | Khung ảnh minh họa co giãn `clamp(132px,22vh,235px)`, icon nhóm ngành, biểu đồ lục giác. |
| `src/pages/Dashboard.tsx` | Trang Khám phá ngành 2 tab (`Đề xuất theo hồ sơ`, `Nguyện vọng với AI`), quản lý cache client & lịch sử. |
| `src/components/xai/TwoTierFunnelRecommendation.tsx` | Phễu đề xuất 2 tầng (Lĩnh vực $\rightarrow$ Ngành), ngữ cảnh theo khối lớp/giới tính. |
| `src/components/xai/SkillAnalysisCard.tsx` | Thẻ Phân tích kỹ năng (lưới 2 cột, nút `Xem thêm` / `Thu gọn`, badge cache 0 token). |
| `src/components/xai/AspirationAlignmentCard.tsx` | Thẻ Đánh giá nguyện vọng với AI (`fit_label`, `reasons_fit`, `reasons_gap`, `better_majors`, đổi nghề mơ ước). |
| `src/pages/RoadmapView.tsx` | Màn hình `Lộ trình học tập 4 tuần — Coming Soon`. |
| `src/pages/MajorDetail.tsx` | Chi tiết ngành đào tạo, cơ hội nghề nghiệp, khối thi, trạng thái Lộ trình `Coming Soon`. |
| `public/images/assessment/R1.jpg..C5.jpg` | 30 ảnh minh họa chuẩn hóa `960×480` (tỷ lệ 2:1) cho 30 câu RIASEC. |

---

## 4. Nhật ký Thay đổi Dự án (Chronological Engineering Log)

### Ngày 2026-11-21
- **`d42f2ce` — `feat(auth): support env-driven admin bootstrap in init_db.py`**
  - Thêm `bootstrap_admin_from_env()` vào `backend/scripts/init_db.py` để tự tạo hoặc nâng quyền `ADMIN` trên Render/Supabase thông qua biến môi trường `BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD` mà không hardcode mật khẩu trong repo.
  - Xác nhận DB production dùng **Supabase PostgreSQL** (`uwggiegmkwfayeutjrty`) với enum `UserRole` viết HOA (`ADMIN`, `STUDENT`) và mật khẩu băm Argon2id.
- **`73cc749` — `feat(assessment): optimize all 30 RIASEC question illustrations and icons locally`**
  - Thay toàn bộ 30 ảnh Unsplash cũ (nhiều ảnh lệch chủ đề sau khi Việt hóa câu hỏi THPT) bằng 30 ảnh chuẩn hóa `960×480` lưu cục bộ tại `frontend/public/images/assessment/R1.jpg..C5.jpg` (14 ảnh AI sinh mới tông Sky + Daylight + 16 ảnh kiểm tra trực quan).
  - Cập nhật lại các `iconKey` bị lệch (`R3 -> sprout`, `R5 -> dumbbell`, `I1 -> calculator`, `A2 -> home`, `A5 -> sparkles`, `S5 -> globe`, `E5 -> calendar`, `C4 -> calendar`, `C5 -> check`) và bật `loading="eager"`.
- **`3c4d120` — `feat(ui): place assessment step bar beside Back button separately and remove help guide`**
  - Đặt thanh 3 bước nằm ngang hàng nhưng tách khối riêng ngay bên phải nút `Quay lại` trên `/assessment` để tiết kiệm thêm chiều cao màn Laptop.
  - Xóa hoàn toàn mục `Hướng dẫn làm bài` (`HelpGuideCollapsible`).
- **`064126c` — `feat(ui): remove assessment scale toggle and step 4 aspiration, clean dashboard tab sub-labels`**
  - Xóa nút đổi `Khung hiển thị` trên `/assessment`, cố định mặc định khung rộng rãi.
  - Bỏ bước `4. Nguyện vọng` khỏi `/assessment` (rút gọn còn 3 bước; bước 3 submit hoàn tất và giữ nguyên nguyện vọng đã lưu ở Dashboard).
  - Xóa các chip chữ nhỏ (`Hồ sơ & Kỹ năng`, `Đánh giá nghề mơ ước`) và đoạn mô tả nhỏ trên thanh tab `/dashboard`; đổi nhãn Sidebar thành `Lộ trình học` để không bị cắt dấu `...` cạnh chip `Soon`.
- **`e763402` — `feat(ui): mark 4-week roadmap as Coming Soon and sync layout across laptop and external monitors`**
  - Chuyển toàn bộ chức năng Lộ trình 4 tuần (`/roadmap`, Sidebar, `MajorDetail`, thẻ ngành) sang trạng thái **Coming Soon**.
  - Đồng bộ hiển thị giữa Laptop (Scale 125%–150%) và Màn hình rời (Scale 100%): nâng root `font-size` ở màn lớn (`17px`/`17.5px`), thu gọn Sidebar `268px -> 244px`, co giãn ảnh RIASEC theo `clamp(132px,22vh,235px)`, căn thẳng trục chiều rộng trên `/assessment` và nén phần đầu `/dashboard`.

### Ngày 2026-11-20
- **`f0a8bef` — `feat(dashboard): restructure 2 Sky+Slate tabs and add /major-insights/aspiration-ai`**
  - Sửa lỗi `/student-skills` báo thiếu dữ liệu Holland dù đã trả lời 30/30 câu bằng `_format_riasec_summary_from_payload` (đọc từ `riasec_answers` qua `build_interest_evidence`), nâng policy cache lên `evidence-skills-v4`.
  - Thêm endpoint `POST /api/v1/major-insights/aspiration-ai` có Smart DB Cache (`major_code = "ASPIRATION_AI"`), tuân thủ Veto PA 3 và giới hạn `better_majors` trong danh mục ngành thật.
  - Tái cấu trúc `/dashboard` thành 2 tab đồng bộ **Sky + Slate** (xóa toàn bộ lớp màu `indigo`), đưa Phễu 2 tầng + `SkillAnalysisCard` (lưới 2 cột) lên Tab 1 mặc định và tách `AspirationAlignmentCard` sang Tab 2.

### Ngày 2026-11-19
- **`67432a3` — `style(auth): simplify login, registration and OTP UI copy and unify Sky/Slate palette`**: Tinh gọn giao diện đăng nhập/đăng ký/OTP và đồng bộ màu Sky + Slate.
- **`94e0821` / `3698543` / `1f4afb0` / `b399152` — Hệ thống gửi Email OTP trên Render Free**: Bổ sung Google Apps Script HTTPS Webhook (cổng 443), Brevo HTTP API, timeout SMTP 6s, làm sạch khoảng trắng URL và báo lỗi chẩn đoán chi tiết.
- **`680c2a2` — `feat(aspiration): upgrade aspiration agent with trait conflict warnings, full related paths and AI coaching (PA 3)`**: Phủ đủ 44 nghề chuẩn & nhóm ngành 4 số, thêm cảnh báo xung đột sở thích (`subfacet_status`, `trait_warning`), tính điểm/môn thiếu.
- **`f655762` — `fix(trend-agent): enforce strict evidence-only discovery without fabricated majors`**: Xóa hoàn toàn fallback bịa ngành/nguồn trong Trend Agent, chỉ trích xuất ngành có bằng chứng trực tiếp trong bài báo thật.
- **`d2dd70a` — `fix(deploy): add 20s timeout guard to init_db.py`**: Tránh lỗi port-scan timeout trên Render khi khởi chạy migration.
- **`0a52692` — `feat(recommender): add PA 3 sub-facet affinity & asymmetric veto gate`**: Triển khai cơ chế phạt bất đối xứng khi học sinh chọn "Rất không thích" hoạt động cốt lõi của ngành.
- **`c7f2622` — `feat(auth): enforce strong password policy, email OTP registration, and forgot/reset password flow`**: Chính sách mật khẩu 5 tiêu chí + đăng ký/quên mật khẩu qua OTP 6 số.
- **`6b54147` / `d164b22` / `6106621` — AI Chat Advisor & Guardrails**: Hỗ trợ hỏi đáp hướng dẫn sử dụng hệ thống bằng tiếng Việt tự nhiên kèm hàng rào chống prompt-injection 3 tầng.
- **`d2bf3c6` / `719459c` / `ad9e475` — Smart AI Cache & Anti-Double-Click**: Khóa cache theo hồ sơ đầy đủ (gồm khối lớp/giới tính) + in-flight `asyncio.Lock`.
- **`ff1e5a1` / `6e19700` — Vercel Proxy & Render Timeout**: Cấu hình rewrite `/api/*` trên Vercel và timeout 45s.
- **`deee9b3` — Bộ 38 câu hỏi học đường THPT & tách trang Danh mục 435 ngành**.

### Ngày 2026-11-12 → 2026-11-14
- **`f42e2e9` / `2e59304`**: Bổ sung `LLMConnectionPanel` (cấu hình LLM Runtime cho Admin), sửa purge catalog, tối ưu responsive.
- **`3461845` / `c572e3e` / `13555d3` / `23f4982`**: Chế độ xem lại câu hỏi trắc nghiệm (`Thẻ`/`Danh sách`), `UserProfileModal` render qua Portal, trọng số động theo khối lớp/giới tính và giải thích XAI ngắn gọn.

---

## 5. Quy trình Kiểm thử, Đồng bộ & Triển khai (Runbook cho AI)

- **Lưu ý shell Windows PowerShell 5.1:** Không dùng `&&` để nối lệnh; dùng `;` kèm `if ($LASTEXITCODE -eq 0) { ... }`.
- **Kiểm tra Frontend:**
  ```powershell
  Set-Location frontend; npm run build; if ($LASTEXITCODE -eq 0) { npm test }
  ```
  - `npm run build` chạy `tsc -b && vite build`.
  - `npm test` chạy 12 unit tests (`node --experimental-strip-types --test tests/*.test.ts`).
- **Kiểm tra Backend (khi Docker cục bộ tắt):**
  ```powershell
  python -m py_compile backend/app/schemas/insight.py backend/app/services/major_insight/service.py backend/app/services/major_insight/router.py backend/scripts/init_db.py
  ```
- **Chạy Playwright E2E cục bộ (chỉ chấp nhận `localhost` / `127.0.0.1`):**
  ```powershell
  # Terminal 1: npm run dev -- --host 127.0.0.1 --port 5173
  # Terminal 2:
  $env:E2E_BASE_URL="http://127.0.0.1:5173"
  npx playwright test e2e/profile-recommendation.spec.ts
  ```
- **Đồng bộ & Deploy:**
  1. Copy mọi tệp vừa sửa từ `AI_CAREERGUIDE` sang `AI_CAREERGUIDE_1`.
  2. `git add ...` $\rightarrow$ `git commit -m "..."` trên nhánh `develop`.
  3. `git push personal develop:main` (Vercel & Render tự động build từ nhánh `main` của `personal`).

---

## 6. Trạng thái Tồn đọng / Lưu ý Hiện tại

1. **Lộ trình học 4 tuần (`/roadmap`):** Đang tạm để **Coming Soon**; khi phát triển lại cần thiết kế lại UX + cập nhật `RoadmapView.tsx`, `Sidebar.tsx`, `MajorDetail.tsx` và bài test E2E `frontend/e2e/admin-and-student.spec.ts` (hiện file E2E này vẫn giữ đoạn test luồng `/roadmap` cũ).
2. **Bộ 30 ảnh trắc nghiệm RIASEC (`frontend/public/images/assessment/`):** 14 ảnh được sinh cùng một phong cách AI (`R1–R3, I1–I2, A1, A4, S1, E1–E3, C1–C3`), 16 ảnh còn lại là ảnh thật đã kiểm tra trực quan và chuẩn hóa `960×480`. Nếu muốn đồng nhất 100% cùng một phong cách AI cho 16 ảnh còn lại, có thể tạo bổ sung sau khi reset hạn mức model tạo ảnh.
3. **Môi trường local:** Máy host Windows chạy Python 3.12 (MSYS2) không cài đủ gói `fastapi`/`sqlalchemy`/`pytest` và Docker Desktop thường tắt; cần kiểm thử đầy đủ tích hợp DB/API trên Render/Supabase hoặc bật Docker khi cần chạy `pytest`.

---

## 7. Mẫu Ghi thêm Nhật ký (Dành cho các phiên làm việc sau)

```markdown
### Ngày YYYY-MM-DD
- **`<commit_hash>` — `<type>(<scope>): <tóm tắt ngắn>`**
  - **Vấn đề / Yêu cầu:** ...
  - **Thay đổi chính (`file1`, `file2`):** ...
  - **Kiểm chứng:** (`npm run build`, `npm test`, `py_compile`, ...)
```
