# FE – Kết nối với Backend, Biến môi trường & Xử lý lỗi

## 1. Biến môi trường (`VITE_API_BASE_URL`)

- Địa chỉ kết nối Backend đọc qua biến môi trường **`VITE_API_BASE_URL`** trong `frontend/src/services/api.ts` (không viết cứng địa chỉ máy chủ rải rác trong các component).
- File `.env` ở máy cá nhân không được commit. Trong repo chỉ lưu mẫu `.env.example`:
  ```env
  VITE_API_BASE_URL=http://localhost:8000/api/v1
  VITE_GOOGLE_CLIENT_ID=your_google_oauth_client_id.apps.googleusercontent.com
  ```
- **Cấu hình định tuyến trên Vercel (`frontend/vercel.json`):**
  - Chỉ rewrite các đường dẫn giao diện SPA (`"source": "/((?!api/).*)"` về `"/index.html"`), **không chặn các route `/api/*`** để tránh lỗi `HTTP 405 Method Not Allowed` khi gọi POST `/api/v1/auth/register` hoặc `/api/v1/auth/login`.

## 2. Bảo mật Google OAuth & API Keys ở Frontend

- **`VITE_GOOGLE_CLIENT_ID` (public)** được phép đặt ở Frontend để mở luồng đăng nhập Google OAuth 2.0.
- **`GOOGLE_CLIENT_SECRET`, `OPENROUTER_API_KEY`, `TAVILY_API_KEY`, `SECRET_KEY` tuyệt đối KHÔNG để ở Frontend** (vì mọi biến `VITE_*` đều bị đóng gói công khai vào bundle JavaScript trên trình duyệt).
- Mật khẩu của học sinh không bao giờ được `console.log` hoặc lưu vào `localStorage`.

## 3. Lớp gọi API tập trung (`src/services/api.ts`) & Cơ chế Fallback

- Toàn bộ lời gọi HTTP về Backend phải đi qua hàm `apiRequest<T>(endpoint, fallback, options)` trong `frontend/src/services/api.ts`.
- Tự động đính kèm header `Authorization: Bearer <token>` nếu người dùng đã đăng nhập.
- **Xử lý mã lỗi chuẩn hóa từ Backend:**
  - `401 CHUA_XAC_THUC`: Thông báo sai thông tin đăng nhập hoặc phiên hết hạn.
  - `403 KHONG_DU_QUYEN_ADMIN`: Chặn truy cập trang `/admin` đối với tài khoản học sinh.
  - `409 EMAIL_DA_TON_TAI`: Hiển thị thông báo email đã được đăng ký để học sinh chuyển sang đăng nhập.
  - `422 CHUA_HOAN_THANH_BAI_TEST`: Chuyển hướng hoặc hiển thị màn hình yêu cầu làm bài trắc nghiệm trước khi xem đề xuất ngành.
- Khi triển khai bản demo tĩnh trên Vercel mà chưa bật máy chủ Backend riêng, `api.ts` và `Login.tsx` hỗ trợ cơ chế local session/fallback an toàn cùng bộ dữ liệu đủ **435 ngành** (`src/data/moetMajors435.ts`) để ứng dụng luôn hoạt động mượt mà.
