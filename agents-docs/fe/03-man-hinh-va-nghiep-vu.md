# FE – Phạm vi màn hình và Quy tắc nghiệp vụ Giao diện

## 1. Phạm vi các màn hình chính (`frontend/src/pages/`)

1. **`Home.tsx` (`/`):** Trang chủ giới thiệu ngắn gọn mô hình 3 trụ cột XAI, 435 ngành chuẩn Bộ GD&ĐT và nút bắt đầu đánh giá.
2. **`Login.tsx` & `GoogleCallback.tsx` (`/login`, `/auth/google/callback`):** Đăng nhập, đăng ký tài khoản học sinh và xác thực Google OAuth 2.0.
3. **`AssessmentWizard.tsx` (`/assessment`):** Bài trắc nghiệm 3 bước (30 câu sở thích Holland RIASEC -> Nhập điểm học bạ/tổ hợp môn -> 8 chiều phong cách nhận thức).
4. **`Dashboard.tsx` (`/dashboard`):**
   - Báo cáo phân tích hồ sơ RIASEC (Biểu đồ Radar kép: Sở thích vs Học lực).
   - Phễu đề xuất ngành 2 tầng (`TwoTierFunnelRecommendation.tsx`): Top 3 Lĩnh vực (Tầng 1) -> Danh sách ngành mã cấp IV kèm huy hiệu `TARGET`/`REACH` và 3 thanh tương thích (Tầng 2).
   - Thanh chuyển đổi & xem lại **Lịch sử các lần đánh giá trước đó**.
   - Bộ tra cứu & lọc đầy đủ **435 ngành đào tạo** Bộ GD&ĐT.
5. **`MajorDetail.tsx` (`/majors/:id`):** Chi tiết ngành học, tự động kích hoạt giải thích XAI cá nhân hóa, phân tích kỹ năng cần bổ sung (`GapAnalysisCard`) và liên kết lộ trình 4 tuần.
6. **`RoadmapView.tsx` (`/roadmap`):** Lộ trình tự học trải nghiệm 4 tuần với danh sách nhiệm vụ kiểm chứng mức độ phù hợp.
7. **`AIChatAdvisor.tsx` (Drawer):** Trợ lý tư vấn hướng nghiệp AI tương tác theo ngữ cảnh hồ sơ học sinh.
8. **`AdminHITLDashboard.tsx` (`/admin`):** Cổng quản trị dành riêng cho `ADMIN` kiểm duyệt dữ liệu nạp từ Stream A/B (HITL Staging Review) và giám sát trạng thái 435 ngành.

## 2. Quy tắc nghiệp vụ bắt buộc trên Giao diện

- **Không đề xuất ngành khi chưa làm bài test:**
  - Khi học sinh mới tạo tài khoản hoặc đăng nhập lần đầu (`hasCompletedAssessment === false`), trang `/dashboard` **bắt buộc hiển thị trạng thái rỗng (Empty State) dạng Liquid Glass** mời học sinh làm bài đánh giá — tuyệt đối không hiển thị sẵn kết quả đề xuất ngành giả lập.
- **Cô lập dữ liệu bài test theo từng tài khoản (`user_id`):**
  - Kho khóa `localStorage` trong `AssessmentContext.tsx` phải tách biệt theo từng tài khoản (`career-guide:assessment:u:<user_id>` và `career-guide:assessment-history:u:<user_id>`). Khi đăng xuất và đăng nhập tài khoản khác, tuyệt đối không để lộ kết quả bài test của người dùng trước.
- **Hỗ trợ làm lại bài test & Xem lại lịch sử đề xuất:**
  - Mỗi lần học sinh hoàn thành bài trắc nghiệm ở `AssessmentWizard.tsx`, kết quả được lưu thêm vào mảng lịch sử (`AssessmentHistoryItem`) để học sinh có thể bấm nút **`Lịch sử`** trên Dashboard và chuyển đổi xem lại bất kỳ lần đề xuất nào trước đó.
- **Đầy đủ 435 ngành chuẩn Bộ GD&ĐT:**
  - Mọi nhãn trên Sidebar (`435 Ngành học`), tiêu đề Dashboard và bảng tra cứu phải hiển thị đúng **435 ngành** (theo `src/data/moetMajors435.ts`), không hiển thị số 108 cũ.
