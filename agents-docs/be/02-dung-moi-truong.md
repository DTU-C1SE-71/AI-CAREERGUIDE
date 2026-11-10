# BE – Dựng môi trường từ đầu và tách biệt DB Test

Mỗi thành viên dựng môi trường trên máy cá nhân hoặc chạy qua Docker Compose.

## Cách 1: Chạy nhanh bằng Docker Compose (Khuyên dùng)

Từ thư mục gốc của dự án:
```bash
cp .env.example .env
docker compose up --build -d
```
- **PostgreSQL 16 + pgvector:** cổng `5432`
- **Backend FastAPI:** `http://localhost:8000` (Swagger UI tại `http://localhost:8000/docs`)
- **Frontend Nginx/React:** `http://localhost:5173` (hoặc cổng cấu hình trong `docker-compose.yml`)

## Cách 2: Dựng trực tiếp trên máy (Windows PowerShell / macOS)

1. **Python 3.11+:** Kiểm tra `python --version` (ra `3.11.x` hoặc `3.12.x`).
2. **Tạo môi trường ảo (Virtual Environment) và cài đặt thư viện:**
   - **Windows (PowerShell):**
     ```powershell
     cd backend
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     pip install -r requirements.txt
     ```
   - **macOS / Linux / Git Bash:**
     ```bash
     cd backend
     python3 -m venv .venv
     source .venv/bin/activate
     pip install -r requirements.txt
     ```
3. **Cấu hình biến môi trường (`.env`):**
   - Sao chép từ `.env.example` sang `.env` (tuyệt đối không commit `.env`).
   - Nếu có PostgreSQL: đặt `DATABASE_URL=postgresql+asyncpg://postgres:<mat_khau>@localhost:5432/careerguide_db`.
   - Nếu chạy local nhanh không bật PostgreSQL: hệ thống tự động hỗ trợ fallback sang SQLite (`sqlite+aiosqlite:///./careerguide.db`) và đọc seed JSON 435 ngành.
4. **Khởi tạo bảng và nạp 435 ngành chuẩn Thông tư 74/2026:**
   ```bash
   python -m scripts.init_db
   ```
5. **Chạy ứng dụng:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

## Tách biệt Database Test (Bắt buộc khi chạy Pytest)

- **Tuyệt đối không chạy `pytest` trực tiếp trên database dev (`careerguide_db`)** để tránh làm mất dữ liệu khảo sát hoặc ghi đè danh mục ngành.
- Khi chạy kiểm thử (`python -m pytest`), hệ thống phải đặt `ENVIRONMENT=test` và sử dụng **SQLite in-memory (`sqlite+aiosqlite:///:memory:`)** hoặc database test riêng biệt (`careerguide_test`).
- Các bài test trong `backend/tests/test_scoring_and_gap_engine.py` và `backend/tests/test_dual_rag_and_ingestion.py` phải tự khởi tạo dữ liệu giả lập (synthetic fixtures) độc lập.

## Bảng lỗi thường gặp khi dựng môi trường

| Lỗi | Nguyên nhân và cách xử lý |
|---|---|
| `ModuleNotFoundError: No module named 'app'` | Đang đứng sai thư mục khi chạy lệnh. Phải `cd backend` trước khi chạy `uvicorn app.main:app` hoặc `python -m pytest` |
| `ImportError: email-validator is not installed` | Thiếu gói kiểm tra định dạng `EmailStr` của Pydantic. Chạy `pip install email-validator` (đã có trong `requirements.txt`) |
| `UnicodeEncodeError: 'charmap' codec can't encode...` (Windows) | Terminal Windows mặc định dùng cp1252/cp1258 khi in tiếng Việt. Đặt `$env:PYTHONIOENCODING="utf-8"` trên PowerShell |
| `Database unavailable ... falling back to seed JSON` | PostgreSQL chưa bật hoặc sai `DATABASE_URL`. Hệ thống vẫn hoạt động an toàn nhờ cơ chế self-healing đọc từ `moet_taxonomy_tt74.json` (435 ngành) |

Agent **không tự chạy** `DROP DATABASE` hay xóa file cơ sở dữ liệu khi chưa được người dùng đồng ý.
