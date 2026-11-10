# FE – Cấu trúc Code & Quy ước đặt tên (`frontend/src/`)

## 1. Cấu trúc thư mục chuẩn đã chốt

```text
frontend/src/
├── components/
│   ├── assessment/                 # AcademicInputForm, CognitiveQuestionCard, LikertScale, QuestionCard
│   ├── common/                     # Button.tsx, Card.tsx, Badge.tsx (chuẩn Liquid Glass)
│   ├── layout/                     # MainLayout.tsx, Sidebar.tsx, Footer.tsx, PageContainer.tsx
│   ├── visualization/              # RiasecRadarChart.tsx, ScoreBarChart.tsx, RoadmapFlow.tsx
│   └── xai/                        # TwoTierFunnelRecommendation.tsx, FeasibilityBadge.tsx, ExplanationBox.tsx, GapAnalysisCard.tsx
├── constants/                      # Hằng số cấu hình điểm, khối thi, câu hỏi
├── context/                        # AuthContext.tsx, AssessmentContext.tsx (cô lập theo user_id)
├── data/                           # moetMajors435.ts (danh mục 435 ngành chuẩn TT 74/2026/TT-BGDĐT)
├── hooks/                          # useAssessment.ts và các custom hooks
├── pages/                          # Home, Login, GoogleCallback, AssessmentWizard, Dashboard, MajorDetail, RoadmapView, AIChatAdvisor, AdminHITLDashboard
├── routes/                         # AppRoutes.tsx, PrivateRoute.tsx, AdminRoute.tsx
├── services/                       # api.ts (gọi API tập trung), storage.ts, mockData.ts
├── types/                          # assessment.ts, major.ts, roadmap.ts, user.ts
└── utils/                          # Các hàm tiện ích định dạng ngày giờ, chuỗi, tính điểm
```

## 2. Quy ước đặt tên và tổ chức Component

| Thành phần | Quy ước | Ví dụ chuẩn |
|---|---|---|
| Component & Page file | `PascalCase.tsx` | `Dashboard.tsx`, `TwoTierFunnelRecommendation.tsx` |
| Hook file | `camelCase.ts` bắt đầu bằng `use` | `useAssessment.ts`, `useAuth.ts` |
| Data / Service / Type file | `camelCase.ts` | `moetMajors435.ts`, `api.ts`, `assessment.ts` |
| Biến môi trường Vite | `UPPER_SNAKE_CASE` có tiền tố `VITE_` | `VITE_API_BASE_URL`, `VITE_GOOGLE_CLIENT_ID` |

- **Nguyên tắc viết Component:**
  - Không gọi `fetch` trực tiếp trong component; luôn đi qua `apiRequest` tại `src/services/api.ts`.
  - Dùng lại các component nền trong `src/components/common/` (`Card`, `Button`, `Badge`) để đảm bảo tính đồng bộ tuyệt đối về hiệu ứng **Liquid Glass** và bảng màu **Sky / Cyan / Slate**.
