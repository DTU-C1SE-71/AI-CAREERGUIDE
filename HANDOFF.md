# Handoff — AI CareerGuide

> **Generated:** 2026-11-12T00:05:00+07:00  
> **Project:** `AI_CAREERGUIDE` (`e:\CMU-SoftWareEngineering\CAPSTONE PROJECT\capstone 1\AI_CAREERGUIDE`)  
> **Git Branch & Default Remote:** `develop` → `origin` = `https://github.com/DTU-C1SE-71/AI-CAREERGUIDE.git`  
> **Session Tracking:** Tiếp nối và hoàn tất toàn bộ yêu cầu từ OpenCode session `ses_e34a0a6bfffeaQOm5zvZWD4Zc7`.

---

## 1. Tóm tắt & Bối cảnh Session `ses_e34a0a6bfffeaQOm5zvZWD4Zc7`

### 1.1 Nội dung người dùng đã yêu cầu trong session `ses_e34a0a6bfffeaQOm5zvZWD4Zc7`
1. **Kiểm tra hoạt động Agent hỏi ngành mong muốn (`aspiration_agent.py`)**: Rà soát luồng hoạt động từ nhập nguyện vọng đến đối chiếu tâm lý học & học lực.
2. **Yêu cầu cốt lõi**: *"hãy sửa sao để tăng độ tin cậy nghề đề xuất cao nhất có thể, và không được bịa điểm nếu chưa nhập"*.
3. **Yêu cầu tạo bàn giao**: *"tạo file bàn giao đi"*.

### 1.2 Nguyên nhân session `ses_e34a0a6bfffeaQOm5zvZWD4Zc7` bị gián đoạn
- Trong quá trình thực hiện, LLM provider của OpenCode gặp lỗi rate-limit tài khoản miễn phí (`provider.free-limit`, HTTP 429 trên `deepseek-v4.1-flash-free` & `glm-5.3-flash-free`) và lỗi xác thực (HTTP 401 trên `gpt-6.1-terra`).
- Agent tại session đó đã kịp áp dụng phần lớn logic backend nhưng bị dừng đột ngột trước khi hoàn tất frontend type, test suite và ghi file `HANDOFF.md`.
- Hiện tại, **Antigravity đã đọc toàn bộ dữ liệu lịch sử của session đó từ SQLite `opencode.db`**, đồng bộ toàn bộ logic frontend/backend, bổ sung test tự động và hoàn tất bàn giao.

---

## 2. Chi tiết các nâng cấp đã hoàn thành (Tăng độ tin cậy & Chống bịa điểm)

### 2.1 Tuyệt đối KHÔNG bịa điểm khi học sinh chưa nhập học bạ
- **Lỗ hổng cũ:** Trong `backend/app/services/recommender/service.py:356`, khi học sinh chỉ làm bài trắc nghiệm RIASEC mà chưa nhập điểm từng môn, hệ thống đã tự gán cứng `raw_block_sum = 21.5` để tính tuyển sinh. Điều này dẫn đến việc hệ thống tự bịa ra điểm khối thi và đưa ra kết luận `TARGET` hoặc `REACH` thiếu căn cứ.
- **Giải pháp chuẩn hóa:**
  - `backend/app/services/recommender/engine.py:evaluate_admission_feasibility`: Thêm tham số `has_academic_data: bool = True`. Nếu `has_academic_data=False`, hệ thống trả về `feasibility_tier="UNKNOWN"`, `best_block_score=None`, `score_gap=None`, và thông báo: *"Chưa nhập điểm học lực nên hệ thống không thể xác nhận ngành này đạt hay thiếu điểm chuẩn."*
  - `backend/app/services/recommender/service.py`: Khi học sinh chưa nhập điểm môn nào (`not has_any_grades`), đặt `raw_block_sum = None`, truyền `has_academic_data=False`, trả về thông điệp XAI giải thích rõ ràng.
  - `backend/app/services/recommender/aspiration_agent.py`: Khi `not has_academic_data`, gán `alignment_status="NEED_ACADEMIC_DATA"`, nhãn `"Khớp Thiên hướng · Chưa đủ điểm để xác nhận khả thi"`, chỉ đối chiếu sở thích trắc nghiệm với Holland code và nhắc nhở học sinh nhập điểm để có kết luận tuyển sinh.
  - `frontend/src/types/assessment.ts`: Mở rộng kiểu `feasibility_tier: "TARGET" | "REACH" | "UNKNOWN"` và `alignment_status` hỗ trợ `"NEED_ACADEMIC_DATA"`.
  - `frontend/src/components/xai/AspirationAlignmentCard.tsx`: Hiển thị badge màu hổ phách (amber) `"Chưa có điểm"` (thay vì mặc định nhầm sang `"Thử thách (REACH)"`), kèm icon la bàn điều hướng.

### 2.2 Mở rộng kho từ khóa & cụm ngành nghề thực tế (Career Synonym Clusters)
Bổ sung các cụm nghề đa dạng vào `CAREER_SYNONYM_CLUSTERS` trong `aspiration_agent.py` để học sinh gõ bất kỳ nghề nào cũng map chuẩn xác vào danh mục 435 ngành TT74:
- `PERFORMING_ARTS_MUSIC`: Ca sĩ, thanh nhạc, nhạc sĩ, diễn viên, nghệ thuật biểu diễn, idol... (`7210205`, `7210201`...).
- `CULINARY_HOSPITALITY_TOURISM`: Đầu bếp, nấu ăn, ẩm thực, quản trị nhà hàng, khách sạn, barista, tiếp viên hàng không... (`7810202`, `7810201`, `7810101`).
- `AVIATION_TRANSPORT`: Phi công, hàng không, quản lý bay, khai thác vận tải... (`7520120`, `7840102`, `7840101`).
- `SPORTS_PHYSICAL_EDU`: Huấn luyện viên thể thao, vận động viên, giáo dục thể chất, y sinh thể thao... (`7810301`, `7810302`, `7720607`).
- `MEDIA_CREATOR`: Sáng tạo nội dung số, YouTuber, TikToker, KOL, KOC, streamer... (`7320104`, `7320105`, `7320106`).
- `SECURITY_DEFENSE`: Công an, cảnh sát, an ninh, bộ đội, quân sự... (`78601xx`).

### 2.3 Bảo vệ kết luận LLM chống ảo giác (Safe LLM Verdict)
- Thêm hàm `_is_safe_llm_verdict(text, ...)` trong `aspiration_agent.py` để kiểm tra đầu ra từ mô hình AI, ngăn chặn LLM tự sinh các con số điểm số ảo hoặc bịa đặt dữ liệu học bạ không có trong ngữ cảnh.

### 2.4 Bổ sung tính năng Bỏ qua Nguyện vọng & Tối ưu giao diện tinh gọn (Clean Minimalist UI)
- **Cho phép bỏ qua nguyện vọng (Skip flow):**
  - Học sinh có thể chọn **"Bỏ qua bước này"** ngay tại banner phía trên hoặc nút **"Bỏ qua & Xem kết quả"** ở thanh điều hướng cuối trang.
  - Khi bấm bỏ qua, hệ thống không bắt buộc nhập liệu, tự động đồng bộ hồ sơ đánh giá và chuyển ngay sang Dashboard để xem kết quả phân tích theo RIASEC, Học lực và Tư duy.
- **Tối ưu hiển thị chỉ những gì cần thiết:**
  - Tập trung 100% vào ô nhập nghề mơ ước kèm icon tìm kiếm, nút xóa chọn nhanh và 8 chip gợi ý phổ biến.
  - Các mục phụ như "Giá trị công việc" (Mục 2) và "Chiến lược đối chiếu điểm chuẩn" (Mục 3) được thu gọn trong Accordion `Tùy chỉnh thêm giá trị & chiến lược điểm số (Không bắt buộc)`, mặc định đóng để giao diện thoáng đãng, không gây choáng ngợp cho học sinh.
  - Tự động hiển thị huy hiệu *"Đã tùy chỉnh"* nếu học sinh đã từng chọn các mục nâng cao này.

### 2.5 Dọn dẹp Repo Git & Loại bỏ Remote thừa / Script rác
- **Xóa 5 script probe/test tạm thời không còn dùng:**
  - `script_check_live.py`: script thăm dò kết nối LLM tạm thời ở root.
  - `script_probe_live.py`: script kiểm tra timeout probe tạm thời ở root.
  - `script_test_probe.py`: script test endpoint probe ở root.
  - `backend/check_db_status.py`: script test raw connection DB độc lập ở backend.
  - `backend/scripts/inspect_db.py`: script đọc SQLite `careerguide.db` cũ (hệ thống hiện dùng PostgreSQL).
- **Gỡ bỏ remote sai lệch (`ntanduy`):**
  - Đã xóa remote `ntanduy` khỏi cấu hình git cục bộ.
  - Chỉ giữ lại duy nhất remote chính thức của tổ chức: `origin` = `https://github.com/DTU-C1SE-71/AI-CAREERGUIDE.git`.
- **Cập nhật `.gitignore`:**
  - Bổ sung quy tắc bỏ qua `script_*.py`, `check_*.py`, `scratch/` để chống commit nhầm các file test ad-hoc trong tương lai.

---

## 3. Kiến trúc hệ thống & Danh mục tệp (Files in Play)

| File | Vai trò & Điểm chạm chính |
|------|---------------------------|
| `backend/app/services/recommender/aspiration_agent.py` | Agent đối chiếu nghề mơ ước: Cụm từ khóa mở rộng, chống bịa điểm `NEED_ACADEMIC_DATA`, bộ lọc an toàn `_is_safe_llm_verdict` |
| `backend/app/services/recommender/engine.py` | Động cơ tuyển sinh 3 trụ cột: Hỗ trợ `has_academic_data=False` → tier `UNKNOWN`, không suy đoán điểm khối |
| `backend/app/services/recommender/service.py` | Luồng tính điểm recommender: Loại bỏ việc gán cứng `21.5đ`, trả về `UNKNOWN` khi chưa có học bạ |
| `backend/tests/test_scoring_and_gap_engine.py` | Bộ test backend: Thêm `test_aspiration_no_grades_returns_need_academic_data_and_unknown_tier` và `test_aspiration_expanded_career_clusters` |
| `frontend/src/types/assessment.ts` | TypeScript types: Cập nhật `feasibility_tier` (`UNKNOWN`) và `alignment_status` (`NEED_ACADEMIC_DATA`) |
| `frontend/src/components/xai/AspirationAlignmentCard.tsx` | UI thẻ đối chiếu nguyện vọng: Hiển thị badge Amber `"Chưa có điểm"` và tone màu tương ứng |
| `backend/app/services/taxonomy/trend_agent.py` | Agent tìm kiếm xu hướng thị trường 2026, quota tối thiểu 3 ngành/nhóm, lưu CSDL |
| `frontend/src/components/admin/TrendAgentPanel.tsx` | Giao diện Admin chạy/duyệt/lưu ngành xu hướng 2026 vào PostgreSQL |
| `frontend/src/components/admin/MajorsCatalogPanel.tsx` | Bảng tra cứu danh mục 435 ngành TT74 & trạng thái xu hướng cho Admin |
| `backend/app/services/major_insight/` | Cụm Agent phân tích chuyên sâu ngành: nội dung đào tạo, vị trí nghề nghiệp, phân tích ưu/nhược điểm học tập sinh viên |
| `frontend/src/components/xai/MajorInfoCards.tsx` & `SkillAnalysisCard.tsx` | Thẻ hiển thị chuyên sâu thông tin ngành và đánh giá kỹ năng cá nhân hóa tại trang chi tiết ngành |
| `.agents/skills/arena/` | Tournament skill `arena`: Thi đấu phân loại giải pháp AI đa tác nhân với số lượng tác nhân tinh gọn (Mặc định 8, Quick 4, Wave 4) |

---

## 4. Kết quả kiểm thử & Nghiệm thu (Verification Gates)

Toàn bộ các cổng kiểm định chất lượng đều đạt chuẩn tuyệt đối:
1. **Pytest Backend:**
   ```bash
   $env:ENVIRONMENT="test"; py -3 -m pytest backend/tests -v
   # Kết quả: 106/106 passed (100%), bao gồm cả 16 test cho major_insight
   ```
2. **Arena Skill Unit Tests:**
   ```bash
   py -3 .agents/skills/arena/test_bracket.py
   # Kết quả: 29/29 passed (100%), kiểm thử chuẩn xác giải đấu 8 tác nhân & 4 tác nhân quick
   ```
3. **Frontend Production Build:**
   ```bash
   npm --prefix frontend run build
   # Kết quả: tsc -b && vite build thành công (3.13s), không có lỗi TypeScript
   ```
4. **Database Health & Active Majors:**
   - PostgreSQL đang lưu trữ chính xác **435 ngành hoạt động** theo TT74/2026/TT-BGDĐT.
   - 81 ngành được gán nhãn xu hướng vĩ mô 2026 phủ kín 23/23 nhóm ngành.

---

## 5. Lệnh xác thực khi tiếp quản dự án

```powershell
# 1. Chạy toàn bộ test suite backend
$env:ENVIRONMENT="test"; py -3 -m pytest backend/tests -v

# 2. Chạy test suite của arena skill
py -3 .agents/skills/arena/test_bracket.py

# 3. Build kiểm tra TypeScript và bundle Frontend
npm --prefix frontend run build

# 4. Kiểm tra trạng thái CSDL và API sức khỏe
Invoke-RestMethod -Uri "http://localhost:8000/api/health/db"
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/taxonomy/trend-agent/status"
```

---

## 6. Các quy tắc cốt lõi cần duy trì (Key Constraints)

- **Không bịa điểm:** Học sinh chưa nhập điểm thì chỉ tư vấn thiên hướng sở thích (RIASEC), tuyệt đối không suy đoán điểm khối tuyển sinh hoặc kết luận TARGET/REACH.
- **Pure Guidance Scope:** Không đưa tiêu chí học phí hoặc vị trí địa lý vào bộ lọc hay thuật toán xếp hạng.
- **Trọng số chuẩn hóa:** Khóa chặt công thức 3 trụ cột `0.45 RIASEC + 0.35 Điểm số + 0.20 Nhận thức`.
- **Git Remote mặc định:** Remote chính thức là `origin` = `https://github.com/DTU-C1SE-71/AI-CAREERGUIDE.git`.
