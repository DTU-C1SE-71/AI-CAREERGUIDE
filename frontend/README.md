# AI CareerGuide - Frontend Architecture & Contribution Guide

Dự án Frontend được xây dựng trên nền tảng **React 19 + TypeScript + Vite + Tailwind CSS v4**.

---

## 📁 Cấu trúc thư mục (Directory Structure)

Thành viên trong team vui lòng tuân thủ phân chia thư mục khi thêm code:

```text
frontend/src/
├── assets/         # Tài nguyên tĩnh: hình ảnh, svg, logos, icons riêng
├── components/     # UI Components dùng chung và theo phân hệ
│   ├── common/     # Button, Card, Badge, Modal, Input...
│   ├── layout/     # Sidebar, MainLayout, PageContainer, Footer...
│   ├── assessment/ # Các thẻ câu hỏi RIASEC, nhận thức, bảng nhập điểm...
│   ├── visualization/ # Biểu đồ Recharts, sơ đồ luồng React Flow...
│   └── xai/        # ExplanationBox, FeasibilityBadge, Funnel...
├── constants/      # Các hằng số hệ thống, danh mục, quy chuẩn văn bản
├── context/        # React Context quản lý Global State (Auth, Assessment)
├── data/           # Mock data dự phòng hoặc bộ câu hỏi tĩnh
├── hooks/          # Custom React Hooks (useAuth, useRoadmap, useAssessment...)
├── pages/          # Các trang giao diện chính (Route Views)
│   ├── Home.tsx
│   ├── Login.tsx
│   ├── Dashboard.tsx
│   ├── AssessmentWizard.tsx
│   ├── MajorDetail.tsx
│   ├── RoadmapView.tsx
│   └── AdminHITLDashboard.tsx
├── routes/         # Định tuyến URL (React Router v7) & Route Guards (Private/Admin)
├── services/       # Giao tiếp HTTP với Backend (API Client, Storage helper)
├── types/          # Khai báo TypeScript Interfaces & Type definitions
└── utils/          # Hàm tiện ích (formatting, text manipulation, math helpers)
```

---

## 🛠️ Hướng dẫn phát triển (Development)

1. **Cài đặt thư viện**:
   ```bash
   cd frontend
   npm install
   ```

2. **Chạy máy chủ phát triển (Dev server)**:
   ```bash
   npm run dev
   ```
   Ứng dụng sẽ chạy tại: `http://localhost:5173/`

3. **Kiểm tra TypeScript & Build**:
   ```bash
   npm run build
   ```
   *(Trước khi commit, luôn đảm bảo lệnh này chạy với 0 lỗi).*
