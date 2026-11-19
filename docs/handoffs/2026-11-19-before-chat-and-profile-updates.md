> BẢN LƯU LỊCH SỬ. Đọc HANDOFF.md ở thư mục gốc để biết trạng thái mới. Các mục chặn toán học, selector lớp/giới tính và mật khẩu cũ không còn là hướng dẫn hiện hành. Mật khẩu dạng rõ đã được ẩn trong bản lưu.

# BÀN GIAO DỰ ÁN AI CAREERGUIDE (HANDOFF DOCUMENT)

> **Thời điểm lập:** 2026-11-19  
> **Phiên bản:** v5.1 — Core Recommender & Multi-Agent AI Hardening  
> **Kho mã nguồn:**
> - Workspace chính: `AI_CAREERGUIDE` (Branch `develop`)  
> - Workspace thực thi & Docker runtime: `AI_CAREERGUIDE_1` (Branch `feature/sync-careerguide-1`)  
> - Remote chính thức: `https://github.com/DTU-C1SE-71/AI-CAREERGUIDE.git`

---

## 1. TỔNG QUAN DỰ ÁN & TIẾN ĐỘ THỰC HIỆN

Dự án **AI CareerGuide** là nền tảng hướng nghiệp thông minh dành cho học sinh THPT Việt Nam (Lớp 10–12), tích hợp giải thuật gợi ý ngành 3 trụ cột (Tâm lý học Holland RIASEC, Học lực học bạ theo khối thi, Năng lực tư duy nhận thức), mô hình HA-GAE v3.1 (Horizon-Aware Grade & Gender Adaptive Engine), RAG đa nguồn (TT74/2026/TT-BGDĐT) và các tác nhân AI (LLM multi-agent) hỗ trợ giải thích cá nhân hóa và khám phá xu hướng nghề nghiệp.

Trong phiên làm việc vừa qua, hệ thống đã hoàn thành toàn diện các hạng mục trọng điểm:
1. **Bảo mật xác thực & Đăng xuất (Logout & Google OAuth Hardening)**.
2. **Khôi phục bằng chứng khả thi tuyển sinh (Feasibility Evidence) & Động cơ HA-GAE v3.1**.
3. **Kích hoạt & Kiểm định thực tế LLM / AI Multi-Agent trong Docker**.
4. **Tái thiết kế toàn diện bộ 38 câu hỏi Đánh giá năng lực (v5.1 Micro-Swipe)**: Chuyển đổi 100% câu hỏi người lớn sang ngữ cảnh học sinh THPT, độ dài siêu ngắn 10–12 từ chống mỏi mắt trên thẻ swipe.

---

## 2. CHI TIẾT CÁC HẠNG MỤC ĐÃ HOÀN TẤT & ĐÃ KIỂM THỬ

### 2.1. Bảo mật Phiên làm việc & Đăng xuất (Logout Session Purge & OAuth Hardening)
- **Vấn đề đã xử lý:** Khi học sinh đăng xuất, một số state lưu tạm (như bài test khách, token cũ, hồ sơ học sinh) vẫn còn sót lại trong `localStorage` dẫn đến việc tài khoản đăng nhập sau có thể bị lẫn dữ liệu. Ngoài ra, Google OAuth thỉnh thoảng gặp lỗi lệch đồng hồ (clock skew).
- **Giải pháp triển khai:**
  - `backend/app/services/identity/service.py`:
    - Bổ sung `leeway=60` cho hàm giải mã Google OAuth Token, khắc phục triệt để lỗi chênh lệch microsecond giữa client và server Google.
    - Xác thực chặt chẽ `aud` và `azp` theo danh sách Client ID được cấp phép.
    - Thêm cơ chế whitelist URL chuyển hướng (`redirect_uri`).
    - API Logout chủ động thu hồi JWT và dọn sạch session liên kết.
  - `frontend/src/context/AuthContext.tsx` & `AssessmentContext.tsx`:
    - Khi gọi `logout()`, hệ thống lập tức thanh lọc toàn bộ `localStorage`: `auth_token`, `refresh_token`, `guest_assessment_snapshot`, `assessment_state`, `student_profile`.
    - Điều hướng an toàn về `/login` và reset toàn bộ state trong React Context.
  - **Kiểm định:** 42/42 bài test bảo mật xác thực (`backend/tests/test_auth_security.py`) vượt qua 100%.

---

### 2.2. Khôi phục Bằng chứng Tuyển sinh & Động cơ HA-GAE v3.1 (Grade/Gender Adaptive)
- **Vấn đề đã xử lý:** Đợt refactor trước đó làm mất trường dữ liệu bằng chứng khả thi tuyển sinh (`feasibility_evidence`), khiến giao diện 2 tầng phễu (Two-Tier Funnel) và thẻ chọn Lớp (10/11/12) / Giới tính (Nam/Nữ) không hiển thị chiến lược tuyển sinh cụ thể.
- **Giải pháp triển khai:**
  - `backend/app/services/recommender/service.py`:
    - Gọi hàm `_publish_readiness(..., preserve_complete_feasibility=True)` để giữ lại toàn bộ dữ liệu đối chiếu điểm học bạ và điểm chuẩn thực tế.
    - Khôi phục bộ định tuyến `apply_horizon_gender_reranking`, tự động điều chỉnh độ ưu tiên theo lớp:
      - **Lớp 12:** Tập trung vào Feasibility (Điểm chuẩn sát thực tế, chiến lược xét tuyển NV1/NV2).
      - **Lớp 10–11:** Tập trung vào Exploration & Cognitive Growth (Mở rộng phổ ngành, bồi dưỡng năng lực tư duy).
  - `frontend/src/components/xai/TwoTierFunnelRecommendation.tsx`:
    - Khôi phục thanh điều khiển chọn Khối Lớp (10, 11, 12) và Giới tính (Nam, Nữ).
    - Hiển thị đầy đủ 3 nhóm chiến lược: **Mục tiêu an toàn (TARGET)**, **Thử thách (REACH)**, và **Cần thêm điểm (NEED_ACADEMIC_DATA)**.
    - Cung cấp huy hiệu Nudge thông minh và lời giải thích XAI minh bạch.
  - **Kiểm định:** 85/85 test suites (`test_horizon_gender_engine.py` và `test_scoring_and_gap_engine.py`) xanh 100%.

---

### 2.3. Vận hành & Kiểm định LLM / AI Multi-Agent trong Docker
- **Cấu hình môi trường:**
  - Docker Compose chạy tại `AI_CAREERGUIDE_1`.
  - LLM Provider: `https://api.xkiro.com/v1` (OpenAI-compatible protocol).
  - Model: `mistralai/mistral-medium-3.5`.
  - Lưu ý độ ưu tiên biến môi trường: Docker Compose **luôn ưu tiên giá trị trong tệp `.env`** hơn giá trị mặc định `${VAR:-default}` trong `docker-compose.yml`. Khi sửa config, cần cập nhật `.env` và chạy `docker compose up -d backend`.
- **Kết quả kiểm định thực tế bên trong container `careerguide-v9-backend-1`:**
  - `resolve_snapshot()` & `adapter.chat()`: Kết nối thành công, HTTP 200, độ trễ phản hồi ~300ms.
  - `explain_recommendation_with_ai`: Sinh lời giải thích hướng nghiệp cá nhân hóa theo hồ sơ học sinh (`is_ai_generated: True`).
  - `run_trend_discovery_agent`: Agent quét xu hướng 82 ngành nghề (kết hợp Tavily search + RSS) và tinh chỉnh qua LLM (`llm_refined: True`).
  - Tài khoản Admin: `admin@careerguide.vn` / `[REDACTED_PASSWORD]` tạo JWT hợp lệ, truy cập đầy đủ bảng điều khiển Quản trị.
- **Cơ chế Guardrail an toàn (Phạm vi Chatbot):**
  - Trong `backend/app/services/llamaindex_rag_orchestrator/guidance_boundary.py`, hàm `in_scope()` kiểm soát chặt chẽ mục tiêu tư vấn hướng nghiệp.
  - Khi người dùng nhập câu hỏi ngoài phạm vi (như `1+1=` hoặc toán học thuần túy), AI Guardrail tự động chuyển hướng (`REDIRECT`) về phạm vi hướng nghiệp để tiết kiệm token và chống lạm dụng prompt jailbreak.

---

## 3. TÁI THIẾT KẾ BỘ CÂU HỎI ĐÁNH GIÁ NĂNG LỰC (v5.1 MICRO-SWIPE)

### 3.1. Lý do cải tiến & Nguyên tắc Sư phạm
- **Vấn đề thực tế từ người dùng phản hồi:**
  1. *Ngữ cảnh phi thực tế với học sinh:* Các câu hỏi cũ mang tính công việc người lớn (ví dụ: *"lập kế hoạch vận chuyển hàng hóa"*, *"kiểm duyệt hồ sơ tuân thủ quy định"*, *"vận hành thiết bị phòng lab"*). Học sinh cấp 3 chưa từng đi làm nên không thể trả lời chính xác, gây nhiễu kết quả đánh giá (Construct-Irrelevant Variance).
  2. *Mệt mỏi khi đọc (Reading Fatigue):* Câu hỏi quá dài (20–30 từ) hiển thị trên giao diện Swipe Card làm tràn thành 4–5 dòng chữ to, khiến học sinh nản và quẹt bừa từ câu số 10 trở đi.
- **Tiêu chuẩn thiết kế Micro-Swipe v5.1:**
  - **100% ngữ cảnh học đường THPT:** Sinh hoạt trường lớp, bài tập nhóm, câu lạc bộ, thói quen học tập, sở thích khám phá thường ngày.
  - **Độ dài siêu ngắn:** 10–12 từ/câu, hiển thị gọn gàng trong tối đa 2 dòng trên màn hình điện thoại (font chữ lớn), học sinh đọc hiểu trong 1.5 giây.
  - **Bảo toàn 100% thuật toán tính điểm:** Giữ nguyên toàn bộ mã định danh (`R1..C5`, `COG_1..COG_8`), 4 mức lựa chọn (`A, B, C, D`) và logic chuẩn hóa trong `engine.py`.

---

### 3.2. Toàn bộ 30 câu hỏi RIASEC v5.1 (Micro-Swipe 10–12 từ)

| Mã | Chiều Holland | Nội dung Micro-Swipe v5.1 (10–12 từ) | Ngữ cảnh thực tế THPT |
|:---|:---|:---|:---|
| **R1** | Realistic (Kỹ thuật) | Tự tay tháo lắp đồ điện hỏng hoặc sửa xe đạp tại nhà. | Tò mò cơ khí thực tế |
| **R2** | Realistic (Kỹ thuật) | Lắp ráp các mô hình đồ chơi kỹ thuật hoặc mạch điện tử. | Tự làm sản phẩm hữu hình |
| **R3** | Realistic (Kỹ thuật) | Chăm sóc vườn cây trường học hoặc dựng lều trại ngoại khóa. | Hoạt động ngoài trời, thể chất |
| **R4** | Realistic (Kỹ thuật) | Sử dụng thành thạo búa, kìm hoặc cưa để đóng vật dụng. | Dùng công cụ cầm tay |
| **R5** | Realistic (Kỹ thuật) | Tự cài đặt phần mềm máy tính và sửa lỗi mạng wifi. | Thao tác thiết bị thực tế |
| **I1** | Investigative (Nghiên cứu) | Tìm hiểu nguyên lý hoạt động của các hiện tượng khoa học lạ. | Tò mò quy luật tự nhiên |
| **I2** | Investigative (Nghiên cứu) | Tự làm các thí nghiệm Vật lý hoặc Hóa học tại trường. | Thử nghiệm, quan sát chứng minh |
| **I3** | Investigative (Nghiên cứu) | Đọc tài liệu khoa học để tìm lời giải cho bài khó. | Đào sâu kiến thức |
| **I4** | Investigative (Nghiên cứu) | Lập bảng số liệu thống kê để tìm ra quy luật chung. | Phân tích dữ liệu logic |
| **I5** | Investigative (Nghiên cứu) | Khám phá các công nghệ mới và học viết mã lập trình. | Thử thách tư duy công nghệ |
| **A1** | Artistic (Nghệ thuật) | Vẽ tranh, thiết kế poster bài thuyết trình hoặc chụp ảnh đẹp. | Sáng tạo hình ảnh thị giác |
| **A2** | Artistic (Nghệ thuật) | Viết truyện, làm thơ hoặc chia sẻ cảm xúc qua trang viết. | Biểu đạt ngôn từ nghệ thuật |
| **A3** | Artistic (Nghệ thuật) | Tham gia biểu diễn văn nghệ, ca hát hoặc chơi nhạc cụ. | Âm nhạc và trình diễn |
| **A4** | Artistic (Nghệ thuật) | Thích tìm tòi các ý tưởng độc lạ, không theo khuôn mẫu. | Tư duy phá cách |
| **A5** | Artistic (Nghệ thuật) | Trang trí góc học tập hoặc tự phối đồ theo phong cách. | Thẩm mỹ cá nhân |
| **S1** | Social (Xã hội) | Hướng dẫn bạn bè hiểu bài học khó bằng sự kiên nhẫn. | Giảng giải, hỗ trợ học tập |
| **S2** | Social (Xã hội) | Lắng nghe và an ủi tâm sự của bạn bè khi buồn. | Đồng cảm, kết nối cảm xúc |
| **S3** | Social (Xã hội) | Làm tình nguyện viên giúp đỡ người có hoàn cảnh khó khăn. | Tinh thần cống hiến cộng đồng |
| **S4** | Social (Xã hội) | Hòa giải các bất đồng để gắn kết nhóm bạn trong lớp. | Gắn kết, giải quyết xung đột |
| **S5** | Social (Xã hội) | Tham gia các hoạt động thiện nguyện do đoàn trường tổ chức. | Hoạt động xã hội có tổ chức |
| **E1** | Enterprising (Quản lý) | Nhận làm trưởng nhóm để điều phối và giao việc bạn bè. | Dẫn dắt, tổ chức nhóm |
| **E2** | Enterprising (Quản lý) | Thuyết phục cả lớp đồng thuận với kế hoạch của mình. | Kỹ năng tranh biện, thuyết phục |
| **E3** | Enterprising (Quản lý) | Lên kế hoạch bán hàng hội chợ để gây quỹ câu lạc bộ. | Kinh doanh, huy động nguồn lực |
| **E4** | Enterprising (Quản lý) | Tự tin phát biểu ý kiến cá nhân trước đám đông lớp. | Bản lĩnh nói trước công chúng |
| **E5** | Enterprising (Quản lý) | Đứng ra khởi xướng các phong trào thi đua cho lớp. | Khởi xướng hành động mới |
| **C1** | Conventional (Nghiệp vụ) | Sắp xếp góc học tập và tài liệu học luôn ngăn nắp. | Gọn gàng, hệ thống hóa đồ đạc |
| **C2** | Conventional (Nghiệp vụ) | Lập thời gian biểu chi tiết để ôn tập thi đúng hạn. | Kỷ luật kế hoạch thời gian |
| **C3** | Conventional (Nghiệp vụ) | Ghi chép chi tiêu tiền tiêu vặt cá nhân cẩn thận. | Quản lý tiền bạc rõ ràng |
| **C4** | Conventional (Nghiệp vụ) | Soát lỗi chính tả và kiểm tra kỹ bài trước khi nộp. | Tỉ mỉ, kiểm tra độ chính xác |
| **C5** | Conventional (Nghiệp vụ) | Tuân thủ nghiêm túc nội quy trường học và quy định nhóm. | Tôn trọng nguyên tắc, trật tự |

---

### 3.3. Toàn bộ 8 câu hỏi Nhận thức Tư duy v5.1 (Micro-Swipe)

Mỗi câu hỏi gồm Tiêu đề tình huống ngắn (4–6 từ), Câu hỏi trải nghiệm (9–12 từ) và 4 phương án phản ánh 4 mức độ nhận thức (1–4 điểm), bảo toàn tuyệt đối logic của hàm `normalize_student_cognitive_traits()` trong `backend/app/services/recommender/engine.py`.

1. **COG_1 (Tư duy Logic & Trừu tượng - abstract_reasoning)**
   - *Tình huống:* Giải bài tập Toán khó
   - *Câu hỏi:* Khi gặp bài toán mới lạ chưa từng học dạng, bạn làm gì?
   - A: Bỏ qua và chờ thầy cô giải (1đ)
   - B: Xem lời giải mẫu để làm theo (2đ)
   - C: Thử áp dụng công thức quen thuộc để biến đổi (3đ)
   - D: Tự tìm quy luật mới và so sánh nhiều cách giải (4đ)

2. **COG_2 (Tư duy Không gian - spatial_reasoning)**
   - *Tình huống:* Hình dung hình vẽ không gian
   - *Câu hỏi:* Khi học môn Hình không gian, khả năng tưởng tượng của bạn thế nào?
   - A: Rất khó hình dung nếu không có mô hình thật (1đ)
   - B: Cần giáo viên xoay hình vẽ mới nhìn ra góc (2đ)
   - C: Tự tưởng tượng được các mặt cắt khi đọc đề (3đ)
   - D: Dễ dàng xoay chuyển và nhìn thấu vật thể trong đầu (4đ)

3. **COG_3 (Năng lực Ngôn ngữ & Đọc hiểu - verbal_reasoning)**
   - *Tình huống:* Tóm tắt bài đọc dài
   - *Câu hỏi:* Khi đọc một văn bản dài nhiều chữ, bạn nắm ý thế nào?
   - A: Dễ buồn ngủ và khó nhớ nội dung vừa đọc (1đ)
   - B: Phải đọc đi đọc lại nhiều lần mới hiểu được (2đ)
   - C: Gạch chân được các từ khóa trọng tâm của bài (3đ)
   - D: Tóm tắt nhanh ý chính và phân tích sâu lập luận (4đ)

4. **COG_4 (Tư duy Số học & Dữ liệu - numerical_reasoning)**
   - *Tình huống:* Đọc biểu đồ thống kê
   - *Câu hỏi:* Khi nhìn biểu đồ số liệu Địa lý, bạn nhận thấy điều gì?
   - A: Thấy rối mắt và sợ nhìn vào các con số (1đ)
   - B: Chỉ đọc được các con số lớn nhất hoặc nhỏ nhất (2đ)
   - C: Tính toán và so sánh được tỉ lệ giữa các năm (3đ)
   - D: Nhận ra ngay xu hướng biến động và dự đoán tiếp (4đ)

5. **COG_5 (Khả năng Ghi nhớ & Xử lý - working_memory)**
   - *Tình huống:* Ghi nhớ thông tin ôn thi
   - *Câu hỏi:* Khi cần nhớ nhanh danh sách nhiều công thức ôn thi, bạn làm sao?
   - A: Rất hay quên sau khi học vài phút (1đ)
   - B: Phải chép đi chép lại nhiều lần mới tạm thuộc (2đ)
   - C: Nhớ tốt các ý chính thông qua sơ đồ tư duy (3đ)
   - D: Ghi nhớ chuẩn xác và liên kết nhanh các kiến thức (4đ)

6. **COG_6 (Tập trung & Tỉ mỉ - attention_to_detail)**
   - *Tình huống:* Soát lỗi bài làm
   - *Câu hỏi:* Khi kiểm tra lại bài kiểm tra trước lúc nộp, bạn phát hiện gì?
   - A: Thường nộp bài luôn mà không kiểm tra lại (1đ)
   - B: Nhìn lướt qua nhưng hay sót lỗi tính toán nhỏ (2đ)
   - C: Phát hiện và sửa được lỗi sai dấu hoặc số liệu (3đ)
   - D: Soát kỹ từng bước và không để lọt lỗi nhỏ nào (4đ)

7. **COG_7 (Tốc độ Xử lý - processing_speed)**
   - *Tình huống:* Giải đề thi trắc nghiệm
   - *Câu hỏi:* Trong bài thi trắc nghiệm có áp lực thời gian gấp, bạn làm bài ra sao?
   - A: Thường không làm kịp và phải đánh bừa nhiều câu (1đ)
   - B: Làm vừa kịp giờ nhưng không có thời gian xem lại (2đ)
   - C: Phân bổ giờ hợp lý và hoàn thành đúng tiến độ (3đ)
   - D: Làm bài rất nhanh, chính xác và còn thừa thời gian (4đ)

8. **COG_8 (Tư duy Phản biện & Đánh giá - critical_thinking)**
   - *Tình huống:* Đánh giá tin tức mạng
   - *Câu hỏi:* Khi đọc một thông tin bất ngờ trên mạng xã hội, bạn phản ứng thế nào?
   - A: Tin ngay và chia sẻ cho bạn bè cùng đọc (1đ)
   - B: Cảm thấy phân vân nhưng không kiểm chứng lại (2đ)
   - C: Tìm kiếm thêm từ các nguồn báo chí chính thống (3đ)
   - D: Phân tích động cơ bài viết, kiểm tra chứng cứ độc lập (4đ)

---

## 4. BẢNG TRA CỨU CÁC TỆP TRỌNG YẾU (FILES IN PLAY)

| STT | Đường dẫn tệp | Vai trò kiến trúc |
|:---|:---|:---|
| 1 | `backend/app/services/recommender/service.py` | Lõi tính điểm 3 trụ cột, khôi phục `preserve_complete_feasibility=True`, kết nối HA-GAE v3.1 |
| 2 | `backend/app/services/recommender/engine.py` | Giải thuật đối chiếu tuyển sinh, chuẩn hóa tư duy nhận thức `normalize_student_cognitive_traits` |
| 3 | `backend/app/services/identity/service.py` | Bảo mật xác thực Google OAuth (leeway 60s), thu hồi JWT và dọn sạch session khi đăng xuất |
| 4 | `backend/app/services/llamaindex_rag_orchestrator/guidance_boundary.py` | Bộ lọc an toàn (Guardrails) của Chatbot, ngăn chặn câu hỏi ngoài lề (như toán học, prompt injection) |
| 5 | `backend/app/services/llamaindex_rag_orchestrator/counselor_connection.py` | Bộ điều phối luồng tư vấn hướng nghiệp kết hợp dữ liệu hồ sơ học sinh và kho tài liệu RAG |
| 6 | `frontend/src/components/xai/TwoTierFunnelRecommendation.tsx` | UI 2 tầng phễu hướng nghiệp, bộ lọc chọn Lớp (10/11/12) và Giới tính (Nam/Nữ) kèm XAI |
| 7 | `frontend/src/context/AuthContext.tsx` | Quản lý phiên đăng nhập/đăng xuất, tự động dọn sạch `localStorage` chống lẫn phiên |
| 8 | `frontend/src/data/onetMiniIpQuestions.ts` | *(File chờ cập nhật)* 30 câu hỏi RIASEC trên giao diện Web |
| 9 | `frontend/src/data/cognitiveQuestions.ts` | *(File chờ cập nhật)* 8 câu hỏi Nhận thức trên giao diện Web |
| 10 | `backend/app/db/seeds/assessment_questions_v1_8.json` | *(File chờ cập nhật)* Bộ câu hỏi hạt giống nạp vào CSDL PostgreSQL |
| 11 | `docker-compose.yml` & `.env` | Cấu hình dịch vụ Docker (Backend FastAPI, Frontend Vite, PostgreSQL 16 + pgvector) |

---

## 5. HƯỚNG DẪN VẬN HÀNH & LỆNH ĐIỀU KHIỂN

### 5.1. Khởi động hệ thống qua Docker (Tại `AI_CAREERGUIDE_1`)
```powershell
cd "e:\CMU-SoftWareEngineering\CAPSTONE PROJECT\capstone 1\AI_CAREERGUIDE_1"

# 1. Khởi động toàn bộ cụm dịch vụ (Backend, Frontend, PostgreSQL)
docker compose up -d

# 2. Xem logs của Backend khi có thay đổi cấu hình
docker compose logs -f backend

# 3. Khởi động lại riêng Backend khi sửa file .env
docker compose up -d backend
```

### 5.2. Chạy kiểm thử tự động (Pytest Backend)
```powershell
# Chạy trong container hoặc trực tiếp từ môi trường Python
$env:ENVIRONMENT="test"
py -3 -m pytest backend/tests/test_scoring_and_gap_engine.py backend/tests/test_horizon_gender_engine.py -v
py -3 -m pytest backend/tests/test_auth_security.py -v
```

### 5.3. Build kiểm tra Frontend
```powershell
cd "e:\CMU-SoftWareEngineering\CAPSTONE PROJECT\capstone 1\AI_CAREERGUIDE_1\frontend"
npm run build
```

### 5.4. Kiểm tra sức khỏe dịch vụ
- **Backend API Docs (Swagger):** `http://localhost:8000/docs`
- **DB Health:** `http://localhost:8000/api/health/db`
- **Frontend App:** `http://localhost:5173` (hoặc cổng Docker cấu hình)
- **Tài khoản Quản trị viên (Admin):**
  - Email: `admin@careerguide.vn`
  - Mật khẩu: `[REDACTED_PASSWORD]`

---

## 6. KẾ HOẠCH BƯỚC TIẾP THEO (NEXT STEPS)

1. **Người dùng phê duyệt bộ câu hỏi v5.1:**  
   Sau khi người dùng xác nhận bản thảo 30 câu RIASEC và 8 câu Cognitive siêu ngắn (10–12 từ) ở Mục 3, thực hiện ghi đè đồng bộ vào:
   - `frontend/src/data/onetMiniIpQuestions.ts`
   - `frontend/src/data/cognitiveQuestions.ts`
   - `backend/app/db/seeds/assessment_questions_v1_8.json`
   - Chạy lệnh cập nhật seed vào PostgreSQL.
2. **Đồng bộ mã nguồn giữa hai thư mục:**  
   Merge nhánh `feature/sync-careerguide-1` tại `AI_CAREERGUIDE_1` vào nhánh `develop` tại `AI_CAREERGUIDE` và push lên GitHub remote `origin`.
3. **Kiểm thử trải nghiệm trên thiết bị di động:**  
   Mở giao diện làm bài trắc nghiệm trên màn hình điện thoại (viewport mobile) để đảm bảo thẻ Swipe Card giữ đúng 2 dòng chữ, vuốt mượt mà không bị delay.
