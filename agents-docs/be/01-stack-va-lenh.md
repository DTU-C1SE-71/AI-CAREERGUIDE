# BE – Stack, lệnh thường dùng và các mục "chưa chốt"

Backend của **AI CareerGuide** (Capstone Project C1SE.71 – Đại học Duy Tân).
Hãy trả lời và viết docstring/comment bằng **tiếng Việt**; tên class, hàm, biến và endpoint giữ đúng quy ước trong các file `be/`.

## Stack đã chốt (đừng tự ý đổi)

- **Ngôn ngữ & Framework:** Python **3.11+**, **FastAPI**, chạy trên ASGI server **Uvicorn**.
- **ORM & Database:** **SQLAlchemy 2.0 (Async)** với `asyncpg` (cho PostgreSQL 16 + `pgvector`) và `aiosqlite` (cho môi trường dev nhẹ / test cô lập).
- **Validation & DTO:** **Pydantic v2** (`pydantic`, `pydantic-settings`, `email-validator`).
- **Bảo mật & Xác thực:** Băm mật khẩu chuẩn **Argon2id** (`argon2-cffi` / `passlib`), cấp phát **JWT Bearer Token** (`PyJWT` / `python-jose`), tích hợp **Google OAuth 2.0**.
- **AI & Dual-RAG Orchestrator:** **LlamaIndex** kết hợp OpenAI-compatible client (OpenRouter / Qwen3-VL cho Stream A OCR Thông tư PDF, LLM sinh giải thích ngành học) và **Tavily API** (Stream B khám phá học liệu từ danh sách domain học thuật trắng).
- **Xử lý dữ liệu Bộ GD&ĐT:** `openpyxl`, `pypdf` phục vụ nạp và chuẩn hóa **435 ngành đào tạo cấp IV** theo Thông tư `74/2026/TT-BGDĐT`.

## Các mục đã chốt giữa BE & FE

- **Cơ chế xác thực:** Dùng **JWT Bearer Token** (`Authorization: Bearer <token>`).
- **Tiền tố đường dẫn API:** Thống nhất dùng **`/api/v1/...`** (ví dụ: `/api/v1/auth/login`, `/api/v1/taxonomy/majors`, `/api/v1/recommender/evaluate`, `/api/v1/rag-governance/explain-recommendation`).
- **Luồng Google OAuth 2.0:** Hỗ trợ cả Authorization Code Flow và User-Agent Access Token gửi xuống `/api/v1/auth/google` để BE xác thực trực tiếp với Google UserInfo API rồi cấp JWT nội bộ.

## Các mục "chưa chốt" phía BE (Agent PHẢI HỎI trước, không tự chọn)

> Khi yêu cầu mới chạm tới các mục dưới đây mà người dùng chưa chỉ định rõ, agent **phải hỏi người dùng trước khi code**:

1. **Thay đổi bộ trọng số 3 trụ cột XAI:** Trọng số chuẩn đang khóa ở $w_1 = 0.45$ (RIASEC), $w_2 = 0.35$ (Học lực Z-Score), $w_3 = 0.20$ (Nhận thức). Không tự ý đổi công thức nếu chưa hỏi.
2. **Đổi nhà cung cấp LLM / Embedding mặc định:** Khi thêm provider mới ngoài cấu hình OpenRouter/Gemini hiện có, phải hỏi model ID và cơ chế fallback.
3. **Mở rộng bảng Database ngoài 7 module cốt lõi:** Không tự ý thêm bảng mới phá vỡ thiết kế 7 module nếu chưa thống nhất với nhóm.
4. **Cơ chế lưu trữ file PDF Thông tư tải lên trên Cloud:** Dùng lưu trữ tạm phục vụ OCR hay đẩy lên S3/Cloudflare R2? (Hiện tại chỉ trích xuất văn bản rồi lưu vào bảng Staging DB).

## Lệnh thường dùng

```bash
# Di chuyển vào thư mục backend
cd backend

# Cài đặt thư viện
pip install -r requirements.txt

# Khởi tạo Database & nạp 435 ngành chuẩn TT74/2026
python -m scripts.init_db

# Chạy server phát triển (cổng 8000)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Chạy bộ kiểm thử tự động Pytest (trên DB Test cô lập)
python -m pytest tests/ -v
```
