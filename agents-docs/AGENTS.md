# AGENTS.md – AI CareerGuide Backend (`backend/`)

Backend của hệ thống **AI CareerGuide – Tư vấn hướng nghiệp & Đề xuất ngành học XAI cá nhân hóa** (Đồ án Capstone C1SE.71 – Đại học Duy Tân).
Hãy trả lời và viết docstring/comment bằng **tiếng Việt**.

> **Nguyên tắc "Chưa chốt":** Mục nào ghi "chưa chốt" nghĩa là nhóm chưa quyết định. Agent **bắt buộc phải hỏi người dùng trước**, tuyệt đối không tự ý chọn.

Hướng dẫn chi tiết được chia thành các file nhỏ trong `agents-docs/be/`. **Đọc file liên quan đến việc đang làm trước khi bắt đầu:**

| Khi nào | Đọc file |
|---|---|
| Luôn đọc đầu tiên: stack (FastAPI, SQLAlchemy 2.0, LlamaIndex), lệnh chạy/test, các mục **chưa chốt** | [agents-docs/be/01-stack-va-lenh.md](be/01-stack-va-lenh.md) |
| Dựng môi trường, chạy Docker, tách DB Test riêng, xử lý lỗi khi khởi chạy | [agents-docs/be/02-dung-moi-truong.md](be/02-dung-moi-truong.md) |
| Đụng tới schema 7 module, 435 ngành TT74/2026, pgvector, quy tắc migration timestamp | [agents-docs/be/03-database.md](be/03-database.md) |
| Viết thuật toán 3 trụ cột XAI, Z-Score, Phễu 2 tầng, Gap Engine, HITL Staging | [agents-docs/be/04-nghiep-vu-srs.md](be/04-nghiep-vu-srs.md) |
| Viết API mới, bảo mật Zero-PII, Argon2id, tách DTO/Schema, mã lỗi cố định | [agents-docs/be/05-bao-mat-va-cau-truc.md](be/05-bao-mat-va-cau-truc.md) |
| Commit, merge theo Git Flow, ghi tiến độ không conflict, hoặc nhận task dài | [agents-docs/be/06-git-va-quy-trinh.md](be/06-git-va-quy-trinh.md) |

## Quy tắc bắt buộc (tóm tắt)

- **Danh mục 435 ngành chuẩn:** Hệ thống sử dụng **435 ngành đào tạo cấp IV** theo Thông tư `74/2026/TT-BGDĐT` (`backend/app/db/seeds/moet_taxonomy_tt74.json`). Không quay về con số 108 ngành cũ.
- **Thuật toán 3 trụ cột tất định (Deterministic XAI):** Điểm tương thích ngành $S(u,m) = 100 \times (0.45 \cdot S_{\text{RIASEC}} + 0.35 \cdot S_{\text{Academic}} + 0.20 \cdot S_{\text{Cognitive}})$ phải tính toán toán học 100% ở Python, **tuyệt đối không để LLM tự bịa điểm số hay tự xếp hạng ngành**.
- **Chặn đề xuất khi chưa có dữ liệu bài test:** Nếu học sinh chưa hoàn thành khảo sát đầu vào, API trả về mã lỗi `422 CHUA_HOAN_THANH_BAI_TEST` hoặc trạng thái rỗng, tuyệt đối không trả về danh sách ngành mặc định/ngẫu nhiên.
- **Zero-PII Guardrails (Luật 91/2025/QH15 & NĐ 13/2023):** Không bao giờ gửi họ tên, email, SĐT, trường lớp của học sinh sang API LLM/Tavily bên ngoài. Mọi prompt phải đi qua bộ lọc `Zero-PII Sanitizer`.
- **Tách Database Test:** Khi chạy `pytest`, bắt buộc chạy trên môi trường cô lập (`ENVIRONMENT=test` với SQLite in-memory hoặc DB `careerguide_test`), không chạm vào DB dev/production.
- **Repo Public:** Không commit `.env`, API Key (`OPENROUTER_API_KEY`, `TAVILY_API_KEY`, `GOOGLE_CLIENT_SECRET`, `SECRET_KEY`).
- **Git Flow:** Không commit thẳng vào `main` hay `develop`. Mọi thay đổi đi từ nhánh `feature/#<issue>_<mo-ta>` qua Pull Request vào `develop`.

## Ghi tiến độ (tránh conflict khi merge)

**Tuyệt đối không commit chung một file `PROGRESS.md` ở gốc repo** vì sẽ gây conflict liên tục khi các thành viên merge nhánh vào `develop`:

- **Cách tổ chức file tiến độ:** Lưu riêng theo từng nhánh tại `progress/<ten-nhanh>.md` (thay `/` bằng `-`, ví dụ nhánh `feature/#12_xai-recommender` lưu vào `progress/feature-12_xai-recommender.md`), hoặc thêm `PROGRESS.md` và `progress/` vào `.gitignore`.
- **Đầu phiên:** Kiểm tra nhánh hiện tại (`git branch --show-current`), đọc file `progress/<ten-nhanh>.md` tương ứng (nếu có), chạy `git log --oneline -10` và `git status` để biết đang làm tới đâu.
- **Sau mỗi chức năng nhỏ:** Cập nhật `progress/<ten-nhanh>.md` theo mẫu tại [agents-docs/PROGRESS.md](PROGRESS.md) cùng lúc với commit.
- Chỉ ghi những gì đã thật sự xảy ra (kết quả chạy `pytest`, kết quả build, lỗi nguyên văn), không ghi phỏng đoán.
