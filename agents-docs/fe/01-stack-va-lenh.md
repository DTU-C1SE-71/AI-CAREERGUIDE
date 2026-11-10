# FE – Stack, Lệnh thường dùng & Quy chuẩn Thiết kế Liquid Glass

Frontend của **AI CareerGuide** (Capstone Project C1SE.71 – Đại học Duy Tân), viết bằng **React 19 + TypeScript + Vite 8 + Tailwind CSS v4**.
Hãy trả lời và viết comment bằng **tiếng Việt**.

## 1. Stack đã chốt (đừng tự ý đổi)

- **Core:** **React 19** + **TypeScript 5.8+** + **Vite 8**.
- **Styling & Animation:** **Tailwind CSS v4** (`@tailwindcss/vite`), **Framer Motion** (`framer-motion`), icon từ **Lucide React** (`lucide-react`).
- **Routing:** **React Router v7** (`react-router`).
- **Node.js:** Phiên bản **20+** hoặc **22+**, trình quản lý gói **npm**.
- **Điểm khởi động:** `frontend/src/main.tsx`, component gốc: `frontend/src/App.tsx`.

Khi cần cài thêm thư viện mới vào `frontend/package.json`, bắt buộc nói rõ lý do và hỏi người dùng trước.

## 2. Quy chuẩn Thẩm mỹ Bắt buộc: Liquid Glass & Minimal Text

Mọi trang và component trên Frontend phải tuân thủ nghiêm ngặt 3 nguyên tắc thiết kế đã chốt:
1. **Hiệu ứng kính lỏng (Liquid Glass):**
   - Nền trang có các quầng sáng mờ chuyển động (`mesh-bg`, `mesh-blob-sky`, `mesh-blob-cyan`).
   - Các khối thẻ (`Card`, `Sidebar`, `Modal`, `Banner`) dùng nền bán trong suốt (`bg-white/45` đến `bg-white/80`), độ mờ kính cao (`backdrop-blur-xl` hoặc `backdrop-blur-2xl`), viền phản quang trắng (`border border-white/80`) và bóng đổ nhẹ tông xanh (`shadow-[0_20px_60px_rgba(14,165,233,0.10)]`).
2. **Đồng bộ bảng màu (Unified Palette):**
   - Chỉ sử dụng dải màu chủ đạo **`Sky` (`sky-500`, `sky-600`) – `Cyan` (`cyan-500`) – `Slate` (`slate-900`, `slate-600`, `slate-400`)**.
   - Không phối quá nhiều màu đối chọi (như tím, cam, vàng rực, hồng...) trên cùng một màn hình gây rối mắt.
3. **Tối giản chữ tối đa (Minimal Text):**
   - Xóa bỏ mọi đoạn văn giải thích dài dòng, các câu khẩu hiệu phụ không cần thiết và các mục tĩnh gây nhiễu (như "Lộ trình đã lưu" hay "Gần đây" giả lập trên Sidebar).
   - Ưu tiên hiển thị trực tiếp con số (`% tương thích`, `Mã ngành`, `Z-Score`, `435 ngành`) và biểu đồ trực quan.

## 3. Lệnh thường dùng

```bash
# Chạy từ thư mục gốc dự án:
npm --prefix frontend install       # cài đặt dependencies
npm --prefix frontend run dev       # chạy dev server tại http://localhost:5173
npm --prefix frontend run build     # kiểm tra TypeScript (tsc -b) & đóng gói Vite ra dist/
npm --prefix frontend run preview   # chạy thử bản build production
```

Thư mục `frontend/dist/` và `frontend/node_modules/` tuyệt đối không commit lên Git.
