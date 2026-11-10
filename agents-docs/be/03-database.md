# BE – Quy tắc về Database, Danh mục 435 ngành & Migration

## 1. Cấu trúc 7 phân hệ Database cốt lõi

Schema chuẩn được định nghĩa tại `backend/app/db/init_database.sql` và các SQLAlchemy Models trong `backend/app/models/`:
1. **Identity & Consent (`identity.py`):** `users`, `student_profiles`, `consent_logs` (lưu vết đồng thuận xử lý dữ liệu theo Luật 91/2025/QH15).
2. **Assessment (`assessment.py`):** `assessment_sessions`, `riasec_responses`, `academic_scores`, `cognitive_responses`.
3. **Taxonomy (`taxonomy.py`):** `majors` (435 ngành cấp IV), `subject_blocks` (A00, A01, D01, B00, C00...), `careers`, `skills`, `major_subject_blocks`, `major_skills`.
4. **Recommender (`recommender.py`):** `recommendation_runs`, `recommended_majors` (lưu kết quả tính toán 3 trụ cột và phân tầng `TARGET`/`REACH`).
5. **Gap & Roadmap (`roadmap.py`):** `student_roadmaps`, `roadmap_milestones` (lộ trình tự học 4 tuần).
6. **HITL Staging (`staging.py`):** `staging_records` (quản lý trạng thái `PENDING`, `APPROVED`, `REJECTED` cho dữ liệu Stream A & Stream B).
7. **Vector Store (`vector.py`):** Bảng lưu trữ vector nhúng (`pgvector`) tách biệt cho Dual-RAG (MOET Circular Index & Academic Roadmap Index).

## 2. Quy tắc quản lý Schema & Seed 435 ngành (Tránh xung đột nhóm)

- **Danh mục chuẩn 435 ngành:**
  - File dữ liệu gốc chuẩn hóa nằm tại `backend/app/db/seeds/moet_taxonomy_tt74.json` và `backend/app/services/taxonomy/tt74_reference.py` gồm đúng **435 ngành đào tạo cấp IV** theo Thông tư `74/2026/TT-BGDĐT`.
  - Mọi thao tác đồng bộ CSDL (`bulk_sync_majors`) phải đảm bảo tính **idempotent** (dựa trên khóa `major_code` 7 chữ số, nếu đã tồn tại thì cập nhật, chưa có thì thêm mới, không tạo bản ghi trùng).
- **Quy tắc đặt tên file Migration / SQL bổ sung:**
  - Không sửa phá vỡ cấu trúc nền trong `init_database.sql`.
  - Khi cần thêm script thay đổi cấu trúc bảng, đặt tên file theo **timestamp** `V<YYYYMMDD>_<HHMM>__<mo_ta>.sql` (ví dụ: `V20261110_1030__add_attempt_history_index.sql`) để 2 thành viên làm trên 2 nhánh không bao giờ bị trùng số phiên bản.
- **Quy tắc Phạm vi Hướng nghiệp Thuần túy (Pure Guidance Scope Guardrail):**
  - Bảng `majors` và các Schema liên quan **tuyệt đối không lưu trữ hoặc lọc theo học phí (`tuition`, `fee`) hay vị trí địa lý (`location`, `city`, `province`)** nhằm tránh thiên kiến kinh tế - xã hội (đã có validator chặn tự động trong `schemas/taxonomy.py`).
- **Múi giờ chuẩn:**
  - Toàn bộ cột thời gian (`created_at`, `updated_at`, `completed_at`) thống nhất sử dụng UTC hoặc múi giờ Việt Nam **`Asia/Ho_Chi_Minh` (`UTC+7`)** và trả ra JSON theo chuẩn ISO-8601.
- **Không xóa cứng (Soft Delete):**
  - Ngành học dùng cờ `is_active = True/False`; tài liệu nạp vào dùng trạng thái `status = PENDING | APPROVED | REJECTED`.
