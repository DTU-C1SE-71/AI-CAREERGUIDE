# BE – Bảo mật Zero-PII, Quy ước đặt tên, Tách DTO & Mã lỗi cố định

## 1. Bảo mật & Tuân thủ Pháp lý (Luật 91/2025/QH15 & Nghị định 13/2023/NĐ-CP)

- **Repo Public:** Tuyệt đối không commit mật khẩu DB, `SECRET_KEY`, `OPENROUTER_API_KEY`, `TAVILY_API_KEY`, `GOOGLE_CLIENT_SECRET`, hoặc file `.env`.
- **Băm mật khẩu Argon2id:** Mật khẩu người dùng bắt buộc băm bằng **Argon2id** (`app/core/security.py`), không dùng MD5/SHA-1.
- **Zero-PII Guardrails (Bảo vệ danh tính học sinh):**
  - Trước khi gửi bất kỳ ngữ cảnh nào sang LLM bên ngoài (`guidance_rag.py`) hoặc Tavily (`stream_b_discovery.py`), dữ liệu bắt buộc phải đi qua hàm khử thông tin định danh (`sanitize_pii`), ẩn toàn bộ họ tên, email, số điện thoại, CCCD, tên trường THPT của học sinh.
  - LLM chỉ nhận các chỉ số vô danh: mã ngành (`7480101`), vector điểm RIASEC (`{"I": 0.85, "R": 0.78}`), điểm tổ hợp môn và phong cách nhận thức.
- **Tách bạch Schema/DTO giữa Học sinh (`STUDENT`) và Quản trị viên (`ADMIN`):**
  - Không cho phép người dùng tự truyền `role="admin"` khi gọi API đăng ký (`/api/v1/auth/register`).
  - Các DTO trả về cho `STUDENT` không được chứa thông tin nhạy cảm của hệ thống quản trị (như cấu hình API Key nội bộ, log staging thô chưa duyệt).

## 2. Chuẩn hóa Mã lỗi HTTP & Định dạng JSON Lỗi

Khi xảy ra lỗi nghiệp vụ, Backend trả về đúng HTTP Status Code kèm mã lỗi cố định (`code`) để Frontend xử lý chính xác:

| HTTP Status | Mã lỗi cố định (`code`) | Khi nào trả về |
|---|---|---|
| `400 Bad Request` | `DU_LIEU_KHONG_HOP_LE` | Thiếu trường bắt buộc hoặc điểm số ngoài khoảng hợp lệ $[0, 10]$ |
| `401 Unauthorized` | `CHUA_XAC_THUC` | Thiếu JWT token, token hết hạn hoặc sai mật khẩu đăng nhập |
| `403 Forbidden` | `KHONG_DU_QUYEN_ADMIN` | Tài khoản `STUDENT` gọi vào các API quản trị HITL / cấu hình hệ thống |
| `404 Not Found` | `KHONG_TIM_THAY_NGANH` | Mã ngành không tồn tại trong danh mục 435 ngành Bộ GD&ĐT |
| `409 Conflict` | `EMAIL_DA_TON_TAI` | Đăng ký tài khoản mới trùng với email đã có trong hệ thống |
| `422 Unprocessable Entity` | `CHUA_HOAN_THANH_BAI_TEST` | Yêu cầu tính toán đề xuất ngành khi học sinh chưa làm bài trắc nghiệm |

## 3. Thống nhất quy ước đặt tên

| Thành phần | Quy ước | Ví dụ chuẩn |
|---|---|---|
| Bảng & cột DB | `snake_case` tiếng Anh chuẩn | `majors`, `major_code`, `riasec_vector`, `staging_records` |
| Class Python (Model, Schema, Service) | `PascalCase` | `MajorItemResponse`, `StudentProfile`, `GuidanceRAGEngine` |
| Hàm, biến Python & key JSON | `snake_case` | `major_code`, `riasec_scores`, `grades_by_subject` |
| Đường dẫn REST API | `kebab-case` sau `/api/v1/` | `/api/v1/taxonomy/majors`, `/api/v1/rag-governance/explain-recommendation` |

## 4. Cấu trúc thư mục Backend (`backend/app/`)

```text
backend/app/
├── core/                           # config.py, database.py, security.py (Argon2id/JWT), dependencies.py
├── db/
│   ├── init_database.sql           # DDL khởi tạo 7 phân hệ CSDL
│   └── seeds/                      # moet_taxonomy_tt74.json (435 ngành), Excel template chuẩn
├── middleware/                     # logging.py (đo thời gian phản hồi & kiểm soát bảo mật)
├── models/                         # SQLAlchemy ORM Models (identity, assessment, taxonomy, recommender, roadmap, staging, vector)
├── schemas/                        # Pydantic DTOs tách biệt Request / Student Response / Admin Response
├── services/
│   ├── identity/                   # Đăng ký, đăng nhập, Google OAuth 2.0, Consent Log
│   ├── assessment/                 # Ngân hàng câu hỏi RIASEC/Nhận thức & chấm điểm
│   ├── taxonomy/                   # Quản lý & tra cứu 435 ngành chuẩn TT 74/2026/TT-BGDĐT
│   ├── recommender/                # Động cơ 3 trụ cột tất định, Z-Score & Phễu 2 tầng
│   ├── gap_roadmap_engine/         # Phân tích lỗ hổng kỹ năng & Lộ trình tự học 4 tuần
│   └── llamaindex_rag_orchestrator/# Dual-RAG, Stream A (OCR), Stream B (Tavily), HITL Governance & Zero-PII
├── utils/                          # helpers.py (chuẩn hóa tiếng Việt, khử PII)
└── main.py                         # Điểm khởi chạy FastAPI, cấu hình CORS & nạp các Router
```
