# BE – Quy tắc nghiệp vụ cốt lõi từ SRS (XAI, Phễu 2 Tầng & Dual-RAG)

## 1. Động cơ Khuyến nghị XAI Tất định 3 Trụ cột (FR04)

- **Tách bạch 100% giữa Toán học và LLM:** Điểm số phù hợp và thứ tự xếp hạng ngành bắt buộc tính bằng thuật toán tất định trong `backend/app/services/recommender/engine.py`. Mô hình ngôn ngữ lớn (LLM) chỉ được dùng để **giải thích bằng lời văn** sau khi đã có kết quả toán học.
- **Công thức tổng hợp:**
  $$S(u, m) = 100 \times \left( 0.45 \cdot S_{\text{RIASEC}}(u, m) + 0.35 \cdot S_{\text{Academic}}(u, m) + 0.20 \cdot S_{\text{Cognitive}}(u, m) \right)$$
  1. **Trụ cột 1 – Sở thích Holland RIASEC ($45\%$):** Độ tương tự Cosine giữa vector 6 chiều $(R, I, A, S, E, C)$ của học sinh và vector chuẩn của ngành.
  2. **Trụ cột 2 – Năng lực học thuật Z-Score ($35\%$):** Chuẩn hóa điểm học bạ/thi thử theo phân phối chuẩn quốc gia $\Phi(Z_{u,s})$ trên tổ hợp môn xét tuyển tốt nhất của ngành (`A00`, `A01`, `D01`, `B00`...).
  3. **Trụ cột 3 – Thiên hướng nhận thức ($20\%$):** Ma trận đối chiếu phong cách tư duy và môi trường học tập.

## 2. Phân tầng Khả thi Solution B & Phễu Đề xuất 2 Tầng

- **Phễu 2 tầng (Two-Tier Funnel):**
  - **Tầng 1:** Gom nhóm và chọn ra **Top 3 Lĩnh vực đào tạo** có độ tương thích trung bình cao nhất.
  - **Tầng 2:** Trong mỗi lĩnh vực, liệt kê **Top 2–3 Ngành đào tạo mã cấp IV** phù hợp nhất.
- **Phân loại tính khả thi (Feasibility Tiering):**
  - `TARGET` (Khả thi cao): Điểm năng lực học thuật đáp ứng tốt ngưỡng chuẩn của khối ngành.
  - `REACH` (Thử thách / Phấn đấu): Rất hợp sở thích RIASEC nhưng cần nỗ lực cải thiện thêm điểm các môn trong tổ hợp xét tuyển.

## 3. Chặn đề xuất khi chưa làm bài test & Lưu lịch sử nhiều lần làm bài

- Khi tài khoản học sinh chưa hoàn thành bài đánh giá (chưa có dữ liệu trả lời RIASEC và điểm học tập), hệ thống **tuyệt đối không trả về đề xuất ngành mặc định**.
- Học sinh có thể làm lại bài trắc nghiệm nhiều lần; mỗi lần hoàn thành phải được lưu thành một bản ghi phiên đánh giá riêng để học sinh xem lại và đối chiếu lịch sử đề xuất trước đó.

## 4. Quy trình Nạp tri thức 2 Luồng & Kiểm duyệt HITL (FR05, FR07)

- **Stream A (Thông tư Bộ GD&ĐT):** Trích xuất danh mục ngành từ file Excel/PDF chuẩn Bộ GD&ĐT (hỗ trợ OCR qua Qwen3-VL cho PDF scan).
- **Stream B (Tavily Discovery):** Tìm kiếm khung chương trình và kỹ năng thực tế từ các nguồn học thuật uy tín.
- **Kiểm duyệt Human-in-the-Loop (HITL):** Mọi bản ghi mới nạp từ Stream A/B phải vào bảng `staging_records` ở trạng thái `PENDING`. Chỉ khi `ADMIN` bấm **Approve** thì dữ liệu mới chuyển sang `APPROVED` và đưa vào chỉ mục tìm kiếm chính thức.
