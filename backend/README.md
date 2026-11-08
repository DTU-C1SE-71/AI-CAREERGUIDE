# AI CareerGuide - Backend Architecture & Contribution Guide

Backend Core REST API được xây dựng trên nền tảng **FastAPI (Python 3.11+) + SQLAlchemy 2.0 Async + Pydantic v2**.

---

## 📁 Cấu trúc thư mục (Directory Structure)

Thành viên trong team vui lòng tuân thủ phân chia thư mục khi thêm code:

```text
backend/
├── app/
│   ├── core/           # Cấu hình hệ thống (config), CSDL (database), bảo mật (security/JWT)
│   ├── data/           # Tài liệu văn bản, thông tư TT09/TT74 dạng tệp
│   ├── db/             # SQLite active database & seed scripts
│   ├── middleware/     # Custom ASGI middlewares (Logging, Headers, CORS...)
│   ├── models/         # SQLAlchemy ORM Models (users, majors, assessments, roadmaps...)
│   ├── schemas/        # Pydantic v2 Schemas xác thực dữ liệu request/response
│   ├── services/       # 6 Modular Business Services:
│   │   ├── identity/                    # Xác thực Argon2id, JWT, Google OAuth
│   │   ├── assessment/                  # Khảo sát RIASEC & chuẩn hóa điểm học bạ
│   │   ├── recommender/                 # Mô hình gợi ý 3 trụ cột tất định
│   │   ├── taxonomy/                    # Danh mục 108 ngành cấp IV Bộ GD&ĐT
│   │   ├── gap_roadmap_engine/          # Phân tích khoảng trống kỹ năng & lộ trình
│   │   └── llamaindex_rag_orchestrator/ # Guidance RAG, HITL Staging, kiểm duyệt AI
│   └── utils/          # Hàm tiện ích bổ trợ dùng chung
├── scripts/            # Scripts gieo dữ liệu (seeders) & kiểm tra CSDL
└── tests/              # Kiểm thử tự động với Pytest (Unit & Integration tests)
```

---

## 🛠️ Hướng dẫn phát triển (Development)

1. **Kích hoạt môi trường ảo & cài đặt dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Chạy máy chủ Backend**:
   ```bash
   py -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

3. **Tài liệu API (Swagger UI)**:
   Mở trình duyệt: `http://127.0.0.1:8000/docs`
