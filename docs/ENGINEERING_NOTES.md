# AI CareerGuide — Báo cáo Kiến trúc Hệ thống, Kiểm toán Thuật toán, AI Agents & Nhật ký Kỹ thuật

> Tài liệu tổng hợp toàn diện kiến trúc, mối liên kết giữa toàn bộ dữ liệu trong thuật toán đề xuất ngành, danh sách AI Agents, danh mục tính năng đầy đủ và các giải pháp/công nghệ đã áp dụng trong dự án **AI CareerGuide**.

---

## 1. Tổng quan Công nghệ Cốt lõi (Tech Stack)
- **Frontend:** React 19 + TypeScript + Vite 8 + Tailwind CSS + Framer Motion + Lucide Icons + Recharts (deploy trên **Vercel** tại `https://ai-careerguide-ten.vercel.app`).
- **Backend:** FastAPI + SQLAlchemy 2.0 Async + Pydantic v2 + Argon2id + JWT HS256 (deploy trên **Render** tại `https://ai-careerguide-bny3.onrender.com`).
- **Database:** PostgreSQL 16 + `pgvector` (và SQLite `aiosqlite` cho unit/integration tests cách ly).
- **AI / LLM & Search:** OpenAI-compatible API (`https://api.xkiro.com/v1`, model `mistralai/mistral-medium-3.5`) + Tavily Academic Search + Guardrails 3 lớp.
- **Email OTP:** Google Apps Script HTTPS Mail Webhook (`MAIL_WEBHOOK_URL` qua cổng 443) + Brevo HTTP API + SMTP fallback.

---

## 2. Kiểm toán Thuật toán Đề xuất Ngành & Sơ đồ Liên kết Dữ liệu

### 2.1. Sơ đồ Luồng Dữ liệu Đầu vào $\rightarrow$ Xếp hạng $\rightarrow$ Phân tích AI

```text
+---------------------------------------------------------------------------------+
|                      1. DU LIEU DAU VAO TU HOC SINH                             |
+---------------------------------------------------------------------------------+
| [30 cau RIASEC]  [8 cau Tu duy]  [Diem mon]  [Khoi lop]  [Gioi tinh]  [Ng.vong] |
|  R1..C5 (1..5)    COG_1..COG_8   Toan,Ly..   10/11/12/TN Nam/Nu/Khac  DreamJob  |
+--------+---------------+-------------+-----------+------------+----------+------+
         |               |             |           |            |          |
         |               v             v           |            |          |
         |        +------------+ +------------+    |            |          |
         +------->| Tru cot 1: | | Tru cot 2: |    |            |          |
         |        | RIASEC Fit | | Academic   |    |            |          |
         |        | Cosine +   | | Z-Score +  |    |            |          |
         |        | Bien do    | | CDF + Moc  |    |            |          |
         |        +-----+------+ +-----+------+    |            |          |
         |              |              |           v            |          |
         |              |   +----------+------------------+     |          |
         |              |   | Tru cot 3: Cognitive Fit    |     |          |
         |              |   | Map 8 cau -> 6 truc chuan   |     |          |
         |              |   +----------+------------------+     |          |
         |              +--------------+------------------------+          |
         |                             |  [HORIZON_CONFIG: Trong so dong   |
         |                             |   theo Khoi lop (tau), tong = 1.0]|
         |                             v                                   |
         |        +------------------------------------------------+       |
         |        | 2. DIEM TONG HOP 3 TRU COT + TINH CHINH NG.VONG|<------+
         |        |    overall = w_R*S_R + w_A*S_A + w_P*S_P       | (toi da 10%
         |        |    (+ 0.1 * moi truong nguyen vong neu co)     |  tinh chinh)
         |        +------------------------+-----------------------+
         |                                 |
         | (Dap an goc R1..C5)             v
         +------->+------------------------------------------------+
                  | 3. SUB-FACET AFFINITY & ASYMMETRIC VETO GATE   |
                  |    (subfacet_gate.py — PA 3, 18 quy tac prefix)|
                  |  * 1/5 (Rat khong thich): STRONG_VETO          |
                  |    score_riasec *= 0.30, overall *= 0.45       |
                  |    -> Cach ly khoi Top de xuat & Phen 2 tang   |
                  |  * 2/5 (Khong thich): SOFT_PENALTY (0.65/0.78) |
                  |  * 5/5 (Rat thich): AFFINITY_BOOST (+0.06/+0.05)|
                  +------------------------+-----------------------+
                                           |
                                           v
                  +------------------------------------------------+
                  | 4. HA-GAE v3.1 RERANKING (horizon_gender_engine)|<-----+
                  |  * Khoi lop -> delta_reach_max & quota Reach/  |       |
                  |    Target/Safety (Lop 10: 3.5d -> Lop 12: 1.2d)| [Gioi tinh +
                  |  * Gioi tinh -> Ma tran cong thai hoc 4D (TT74)|  Trend Agent
                  |    Canh bao nang nhoc & khich le STEM/GD-Y te  |  Top5/Top10]
                  |  * STRONG_VETO -> cach ly tuyet doi (khong     |
                  |    nhan gender boost / khong vao Top)          |
                  +------------------------+-----------------------+
                                           |
                                           v
                  +------------------------------------------------+
                  | 5. PHEN 2 TANG (Linh vuc -> Nganh) + XAI       |
                  |    (100% Toan hoc tat dinh - Hien thi tuc thi) |
                  +------------------------+-----------------------+
                                           | (Bam "De xuat nganh co AI")
                                           v
                  +------------------------------------------------+
                  | 6. TANG AI CHUYEN SAU (On-Demand + Smart Cache)|
                  |  * Skill Analysis Agent (SHA-256 + Lock)       |
                  |  * Aspiration Alignment Agent                  |
                  |  * Career Counselor & System Help AI           |
                  +------------------------------------------------+
```

### 2.2. Bảng Kiểm toán Mối liên kết giữa Từng Dữ liệu Đầu vào

| Yếu tố đầu vào | Tệp xử lý chính | Vai trò & Mối liên kết trong Thuật toán |
| :--- | :--- | :--- |
| **30 câu Sở thích RIASEC (`R1..C5`)** | `assessment_questions_v1_8.json`, `recommender/service.py`, `engine.py`, `subfacet_gate.py` | Vừa tính vector 6 chiều $[0..1]$ cho **Trụ cột 1** (`calculate_enhanced_riasec_fit`), vừa cung cấp từng đáp án gốc `R1..C5` cho **Sub-facet Veto & Affinity Gate (PA 3)** để chống nén trung bình. |
| **8 câu Tư duy (`COG_1..COG_8`)** | `cognitiveQuestions.ts`, `engine.py` (`normalize_student_cognitive_traits`) | Map tất định từ 8 câu sang 6 trục nhận thức chuẩn (`abstract_thinking`, `analytical_reasoning`, `spatial_perception`, `linguistic_ability`, `learning_environment`, `teamwork_intensity`) $\rightarrow$ **Trụ cột 3** (`calculate_asymmetric_cognitive_fit`). |
| **Điểm môn học & Tổ hợp (`A00..D01`)** | `engine.py`, `readiness.py` | Chuẩn hóa tên môn $\rightarrow$ tính **Z-Score + Normal CDF** + kiểm tra điểm liệt và mốc tham chiếu đúng tổ hợp (tuyệt đối không lấy chéo khối) $\rightarrow$ **Trụ cột 2** + phân tầng khả thi (`SAFE / TARGET / REACH / UNKNOWN`). |
| **Khối lớp (`grade_level`)** | `horizon_gender_engine.py` (`HORIZON_CONFIG`) | Điều phối **trọng số động 3 trụ cột** (`Lớp 10`: 50/25/25, `Lớp 11`: 46.5/32/21.5, `Lớp 12`: 42.5/40/17.5, `Đã tốt nghiệp`: 41.5/42/16.5), biên độ vươn `delta_reach_max` (3.5đ $\rightarrow$ 1.0đ) và tỷ lệ phễu Reach/Target/Safety. Thiếu trụ cột nào hệ thống tự tái chuẩn hóa tổng = `1.0`. |
| **Giới tính (`gender`)** | `horizon_gender_engine.py` (`BROAD_DISCIPLINE_ERGONOMICS`) | Đối chiếu ma trận công thái học 4D (`phys`, `haz`, `mob`, `gap`) theo Thông tư 74 & TT 10/2020/TT-BLĐTBXH để cảnh báo đặc thù nặng nhọc/độc hại và gợi ý cân bằng giới (Nữ-STEM, Nam-Giáo dục/Y tế) khi hợp sở thích — **không vượt điều kiện điểm chuẩn và không vượt cổng `STRONG_VETO`**. |
| **Nguyện vọng (`aspiration`)** | `aspiration_agent.py`, `recommender/service.py` | Tinh chỉnh tối đa 10% (`0.9*overall + 0.1*pref`) khi có dữ liệu môi trường (không đổi điều kiện học lực) + phân tích riêng tại thẻ Đối chiếu nguyện vọng. |
| **Xu hướng thị trường** | `taxonomy/trend_agent.py` $\rightarrow$ `horizon_gender_engine.py` | Nhãn `TIER_1..3` do Admin duyệt nối vào quota `target_trending_top5=1, target_trending_top10=2` của HA-GAE v3.1. |
| **Tên lớp / Tên trường (`school_class`, `school_name`)** | `identity` (User Profile) | Chỉ phục vụ hiển thị hồ sơ cá nhân, **không đưa vào công thức điểm** để bảo đảm công bằng (chống thiên vị trường chuyên/vùng miền theo Pure Guidance Scope). |

### 2.3. Chi tiết Giải pháp Chống Nén Trung Bình: **Sub-facet Affinity & Asymmetric Veto Gate (PA 3)**
- **Vấn đề đã giải quyết:** Trong mô hình 6 chiều RIASEC truyền thống, nếu học sinh chọn thích Đồ họa (`A1=5`), Kiến trúc (`A2=5`), Truyền thông (`A3=5`), Sáng tạo (`A5=5`) nhưng chọn **Rất không thích Âm nhạc (`A4=1`)**, trung bình nhóm `A` vẫn đạt `80%`, làm ngành *Thanh nhạc / Âm nhạc học* vẫn bị đề xuất ngang *Thiết kế đồ họa*. Lỗi tương tự xảy ra với Y-Sinh (`I3=1`), Thú y/Nông lâm (`R3=1`), An ninh/Thể thao (`R5=1`)...
- **Cơ chế hoạt động (`backend/app/services/recommender/subfacet_gate.py`):**
  - Tận dụng cấu trúc phân cấp **mã ngành 7 chữ số chuẩn Bộ GD&ĐT (Thông tư 09/74)**, thiết lập **18 quy tắc tiền tố (3–7 chữ số) + từ khóa liên ngành** ánh xạ 1-1 với các câu đặc thù trong bộ 30 câu THPT (`A4` $\rightarrow$ `72102*` Âm nhạc/Biểu diễn; `A1` $\rightarrow$ `72101*/72104*` Mỹ thuật/Đồ họa; `A2` $\rightarrow$ `75801*` Kiến trúc; `A3` $\rightarrow$ `73201*/72103*` Báo chí/Điện ảnh; `I2` $\rightarrow$ `748*` CNTT; `I3` $\rightarrow$ `772*/742*` Y-Dược-Sinh; `R3` $\rightarrow$ `762*/764*` Nông-Lâm-Thú y; `R5` $\rightarrow$ `786*/78103*` An ninh/Thể chất; `E4` $\rightarrow$ `738*` Luật; `C1` $\rightarrow$ `73403*/73402*` Kế toán/Tài chính; `C4` $\rightarrow$ `7510605/784*` Logistics/Vận tải...).
  - Các câu tố chất tổng quát (`A5`, `E1`, `C5`...) không dùng để phủ quyết; ngành không thuộc quy tắc nào giữ hệ số `1.0`.
  - Với ngành liên ngành khớp nhiều câu (ví dụ *Sư phạm Âm nhạc* `7140221` khớp cả `S1` và `A4`), áp dụng nguyên tắc **Veto chặt nhất thắng (`min`)**: nếu `S1=5` nhưng `A4=1` thì chỉ *Sư phạm Âm nhạc* bị hạ hạng, còn *Sư phạm Toán/Văn* vẫn giữ nguyên top.
  - **Hệ số điều chỉnh phi đối xứng:**
    - Đáp án **`1` (Rất không thích)** $\rightarrow$ `STRONG_VETO`: `score_riasec *= 0.30`, `overall_score *= 0.45`, **cách ly tuyệt đối khỏi Top đề xuất, bỏ qua gender nudge và loại khỏi Top Phễu 2 tầng**.
    - Đáp án **`2` (Không thích)** $\rightarrow$ `SOFT_PENALTY`: `score_riasec *= 0.65`, `overall_score *= 0.78`.
    - Đáp án **`5` (Rất thích, không bị veto câu nào)** $\rightarrow$ `AFFINITY_BOOST`: `score_riasec += 0.06`, `overall_score += 0.05` (trần `1.0`).
  - **Giải thích XAI minh bạch:** Tự động ghi chú vào `top_supporting_factors` và `score_breakdown["subfacet_gate"]`.
  - **Kiểm thử:** `backend/tests/test_subfacet_veto_gate.py` (kiểm tra end-to-end với hồ sơ `A4=1`, `I3=1`, `R3=1`, ngành liên ngành *Sư phạm Âm nhạc* và tương thích ngược dữ liệu legacy).

---

## 3. Danh mục Toàn bộ AI Agents & Engines trong Dự án (8 thành phần)

| # | Tên Agent / Engine | Tệp nguồn | Loại | Nhiệm vụ & Cơ chế bảo vệ |
| :---: | :--- | :--- | :--- | :--- |
| 1 | **Deterministic 3-Pillar + Sub-facet + HA-GAE v3.1 Engine** | `recommender/engine.py`, `subfacet_gate.py`, `horizon_gender_engine.py`, `service.py` | Toán học tất định (0 LLM) | Chấm điểm 3 trụ cột, Sub-facet Veto/Boost, tái xếp hạng theo Khối lớp/Giới tính/Xu hướng, sinh 3-Sentence XAI. |
| 2 | **Aspiration Alignment Agent** | `recommender/aspiration_agent.py` | Tất định (`enable_llm=False`) | Nhận diện nghề mong muốn (có xử lý mơ hồ/nhiều nghề), đối chiếu danh mục 435 ngành & mốc điểm chuẩn thực tế. |
| 3 | **Student Skill Analysis Agent** | `major_insight/service.py` (`/student-skills`) | **LLM Agent (On-Demand)** | Phân tích ưu/nhược điểm học tập & lỗ hổng kỹ năng. Có **Smart Cache SHA-256** (băm đủ RIASEC, tư duy, điểm, nguyện vọng, lớp, giới tính, danh mục) + `asyncio.Lock` chống bấm đúp. |
| 4 | **Major Insight Agent** | `major_insight/service.py` (`/{major_code}`) | Cache DB + Danh mục | Cung cấp nội dung đào tạo & vị trí nghề nghiệp của ngành, cache theo dấu vân tay danh mục hiện hành. |
| 5 | **Career Counselor & System Help AI Agent** | `llamaindex_rag_orchestrator/guidance_rag.py`, `chat_scope.py`, `guidance_boundary.py`, `system_help.py` | **LLM Agent + Guardrails 3 lớp** | 3 vai trò: Tư vấn chọn ngành (grounded trên `guidance_facts`), Trợ giảng học tập/lập trình, và Hỗ trợ sử dụng AI CareerGuide. Chặn prompt injection & rò rỉ thông tin nội bộ ngay từ lớp tiền xử lý (0 token). |
| 6 | **Dual-Stream Knowledge & HITL Governance Agents** | `stream_a_ingest.py`, `stream_b_discovery.py`, `hitl_governance.py` | RAG + HITL | Stream A nạp PDF tài liệu chuẩn; Stream B tìm kiếm nguồn học thuật whitelist (`.edu.vn`, `coursera.org`, `roadmap.sh`...) qua Tavily, đi qua hàng đợi Admin kiểm duyệt. |
| 7 | **Labor Market Trend Agent (Strict Evidence-Only)** | `taxonomy/trend_agent.py` | Admin Agent (Web + LLM) | Quét báo chí đúng theo `focus_query` của Admin (Tavily + Google/Bing News RSS), đối chiếu **bằng chứng trực tiếp 1-1** (tên ngành chuẩn / `STRICT_MAJOR_SYNONYMS`), tuyệt đối **không** lấy ngành từ bảng cứng, **không** nhồi quota CSDL, **không** gắn link giả; trả rỗng `no_matching_majors` nếu báo không đề cập ngành nào. |
| 8 | **Gap & 4-Week Roadmap Engine** | `gap_roadmap_engine/gap_engine.py`, `service.py` | Cache Write-Once/Read-Many | Tính lỗ hổng kỹ năng tiên quyết và sinh lộ trình trải nghiệm/ôn tập 4 tuần theo `major_code` (có fallback tĩnh). |

### 3.1. Nâng cấp **Strict Evidence-Only** cho Labor Market Trend Agent (`taxonomy/trend_agent.py`)
- **Vấn đề trước kiểm toán:** Bản cũ chứa bảng hard-code `CATEGORY_BASELINE_REPRESENTATIVES`, chỉ tiêu lấp nhóm `CATEGORY_TREND_QUOTA` ($\ge 3$ ngành/nhóm), vòng lặp bốc đại ngành từ CSDL, chùm từ khóa `TREND_TOPIC_CLUSTERS` gây bắn chéo ngành không liên quan (VD: *du lịch* đôn *Thú y* / *Thủy sản*), và gán `fallback_article_refs = articles[:2]` làm nguồn dẫn chứng giả.
- **Giải pháp đã áp dụng (`Zero Fabrication`):**
  1. Xóa hoàn toàn `CATEGORY_BASELINE_REPRESENTATIVES`, `CATEGORY_TREND_QUOTA`, `TREND_TOPIC_CLUSTERS`, vòng lặp bốc ngành từ DB và `fallback_article_refs`.
  2. `search_trending_majors_online` chỉ tìm đúng theo `focus_query` Admin nhập (loại bỏ 5 truy vấn cứng ngoài lề).
  3. `_extract_candidates_from_articles` chỉ chấp nhận ngành có tên chuẩn hoặc từ đồng nghĩa 1-1 không mơ hồ (`STRICT_MAJOR_SYNONYMS`, khớp biên từ `(?<!\w)...(?!\w)`, không khớp nhầm từ `"ai"` trong tiếng Việt) xuất hiện trực tiếp trong ít nhất 1 bài báo thật (`evidence_score >= 2.0`), và `sources` chỉ chứa đúng các bài báo nhắc tới ngành đó.
  4. Khi không có ngành nào được đề cập trực tiếp trong bài báo, `run_trend_discovery_agent` trả trung thực `status: "no_matching_majors"` và `trending_majors: []`.
  5. Kiểm thử hồi quy tại `backend/tests/test_trend_evidence.py`.

---

## 4. Danh mục Đầy đủ Tính năng của Hệ thống

### 4.1. Cổng Học sinh (Student Portal)
1. **Xác thực & Bảo mật Tài khoản (`/login`, `/login/callback`):**
   - Đăng nhập Email/Mật khẩu (Argon2id + JWT HS256) và Đăng nhập Google OAuth 2.0 (xác minh chữ ký RS256 từ Google JWKS).
   - **Chính sách mật khẩu mạnh 5 tiêu chí** (tối thiểu 8 ký tự, chữ hoa, chữ thường, số, ký tự đặc biệt) kèm checklist realtime & nút hiện/ẩn mật khẩu.
   - **Đăng ký thường xác nhận qua Email OTP 6 chữ số** (HMAC-SHA256, hiệu lực 10 phút, tối đa 5 lần thử, cooldown 60s, không lưu plaintext password/OTP).
   - **Quên mật khẩu & Đặt lại mật khẩu qua Email OTP** (phản hồi trung tính chống dò email).
   - Ghi nhận đồng ý xử lý dữ liệu cá nhân theo **Luật Bảo vệ Dữ liệu Cá nhân 91/2025/QH15** (`user_consents`).
2. **Hồ sơ Cá nhân (Profile Modal):**
   - Cập nhật Họ tên, **Khối lớp (10 / 11 / 12 / Đã tốt nghiệp)**, **Giới tính**, Lớp học, Trường THPT; thay đổi Khối lớp/Giới tính/Điểm tự động cập nhật đề xuất & khóa cache AI.
3. **Trắc nghiệm Hướng nghiệp 4 bước (`/assessment`):**
   - Bộ **38 câu hỏi 100% trải nghiệm học đường THPT** (30 câu RIASEC + 8 câu Tư duy), nhập điểm học bạ/thi thử và Nguyện vọng.
   - Chế độ xem `Thẻ`, `Danh sách`, `Radar`; nút **Quay lại** về cổng chọn làm bài mới / xem lại; lưu đầy đủ lên PostgreSQL và hydrate lại khi đăng nhập lại.
4. **Khám phá Ngành (`/dashboard` — 2 chế độ tách biệt):**
   - **Chế độ `Thuật toán đề xuất` (mặc định · Tức thì · 0 AI):** Biểu đồ Radar RIASEC, Top 3 nhóm sở thích, Khối thi tốt nhất (Z-Score), Phễu 2 tầng (Lĩnh vực $\rightarrow$ Ngành) với Sub-facet Veto Gate & HA-GAE v3.1.
   - **Chế độ `Đề xuất ngành có AI` (On-Demand + Smart Cache):** Chỉ gọi AI khi người dùng bấm mở, hiển thị rõ trạng thái **`AI đang phân tích...`** kèm spinner, tự lưu CSDL và gắn nhãn **`Đã tải từ lịch sử CSDL · 0 token`** khi mở lại cùng hồ sơ.
   - Tiện ích: **Lịch sử các lần làm bài**, **Làm lại**, **Xuất báo cáo PDF**.
5. **Danh mục 435 Ngành đào tạo (`/majors` & `/majors/:code`):**
   - Tra cứu toàn bộ 435 ngành chuẩn Bộ GD&ĐT theo mã ngành, tên ngành, bộ lọc lĩnh vực; trang chi tiết gồm nội dung đào tạo, khối xét tuyển, cơ hội nghề nghiệp và giải thích phù hợp.
6. **Lộ trình 4 tuần (`/roadmap`):** Kế hoạch trải nghiệm ngành học và ôn tập theo từng tuần.
7. **Trợ lý AI / Cố vấn AI (Drawer & Page):**
   - Hỏi đáp hướng nghiệp, học tập/lập trình, hướng dẫn sử dụng giao diện AI CareerGuide; thanh cuộn ngang chống tràn code/bảng; lớp bảo mật 3 tầng chống prompt injection và lộ thông tin nội bộ.
8. **Tìm kiếm nhanh toàn cục (Command Palette):** Tìm nhanh ngành học & điều hướng trên mọi màn hình.

### 4.2. Cổng Quản trị (Admin Portal)
1. **Quản trị Danh mục Ngành (`/admin/catalog`, `/admin/import`):** Nhập CSV/Excel 435 ngành, đồng bộ Thông tư 09/74, xuất bản danh mục, quản lý cache nội dung ngành.
2. **Kiểm duyệt tri thức HITL (`/admin`):** Duyệt/từ chối tài liệu Stream A (PDF) và Stream B (Tavily discovery) trước khi đưa vào RAG.
3. **Cấu hình LLM Runtime & Kết nối (`LLMConnectionPanel`):** Quản lý API key mã hóa Fernet độc lập JWT, kiểm tra kết nối (probe), chọn nhanh model, không lộ key ra client.
4. **Quản lý Xu hướng Thị trường (`TrendAgentPanel`):** Chạy Trend Agent, gán/chỉnh sửa hạng xu hướng ngành (`TIER_1..3`).

---

## 5. Nhật ký Triển khai Hạ tầng (Vercel + Render + Email)
- **Vercel (`frontend/vercel.json`, `frontend/src/services/api.ts`):**
  - Thêm rewrite `/api/(.*)` $\rightarrow$ `https://ai-careerguide-bny3.onrender.com/api/$1` (same-origin proxy, tránh 404/CORS).
  - Nâng timeout mặc định `20s` $\rightarrow$ `45s` + xử lý lỗi `TIMEOUT` thân thiện cho cold-start Render Free.
- **Render (`render.yaml`):**
  - `startCommand`: `python scripts/init_db.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT` (tự động chạy migration idempotent `20261116_001` $\rightarrow$ `20261119_005_email_otp`).
  - Biến môi trường chuẩn: `DATABASE_URL`, `ENVIRONMENT=production`, `SECRET_KEY` ($\ge 32$ ký tự riêng), `CORS_ORIGINS`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`, `TAVILY_API_KEY`, `MAIL_WEBHOOK_URL`, `MAIL_WEBHOOK_SECRET`.
- **Gửi Email OTP trên Render Free (`backend/app/core/email_service.py`):**
  - Khắc phục giới hạn chặn cổng SMTP (`25/465/587`) của Render Free bằng **Google Apps Script HTTPS Webhook** (chạy qua cổng `443` bằng chính Gmail `aicareerguide67@gmail.com`, gửi mọi email trong ~1 giây, không cần tên miền riêng hay xác minh SĐT), đồng thời hỗ trợ Brevo HTTP API, SMTP (timeout nhanh `6s` cho local/VPS) và Resend API.
