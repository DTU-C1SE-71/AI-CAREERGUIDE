# BE – Quy trình Git Flow, Quản lý tiến độ & Chia nhỏ Task

## 1. Quy trình Git Flow bắt buộc

Dự án áp dụng nghiêm ngặt quy trình tại [GIT_FLOW.md](../../GIT_FLOW.md):
- **`main`:** Nhánh chính thức lưu lịch sử phát hành (production). **Tuyệt đối không commit trực tiếp vào `main`.**
- **`develop`:** Nhánh tích hợp trung gian. Luôn phải ở trạng thái build và chạy pass test.
- **`feature/#<issue>_<mo-ta-ngan>`:** Tách từ `develop` cho từng task riêng (ví dụ: `feature/#10_tt74-excel-importer`). Hoàn thành thì mở Pull Request vào `develop`.
- **`bugfix/#<issue>_<mo-ta-ngan>`:** Tách từ `develop` để sửa lỗi phát sinh trong quá trình phát triển.
- **`release/<version>` & `hotfix/<version>_<mo-ta>`:** Dùng khi chốt phiên bản hoặc vá lỗi khẩn cấp trên production, sau khi xong phải merge vào cả `main` và `develop`.

### Quy tắc Commit (được kiểm tra tự động bởi `.githooks/commit-msg`)
Mọi commit message phải tuân thủ định dạng Conventional Commits:
- `feat(scope): ...`
- `fix(scope): ...`
- `refactor(scope): ...`
- `docs(scope): ...`
- `test(scope): ...`
- `chore(scope): ...`

### Ba bước bắt buộc trước khi Merge PR vào `develop`
1. Từ nhánh đang làm, kéo `develop` mới nhất về (`git pull dtu develop`) và giải quyết triệt để mọi conflict (không tự ý xóa code của thành viên khác).
2. Sau khi hết conflict, chạy kiểm tra biên dịch Python (`python -m compileall backend/app`) và chạy bộ test (`python -m pytest backend/tests/test_scoring_and_gap_engine.py -v`).
3. Đảm bảo CI GitHub Actions (`.github/workflows/ci.yml`) báo xanh (PASS 100%) và có ít nhất 1 thành viên review Approve.

## 2. Quản lý tiến độ không gây Conflict (`progress/<ten-nhanh>.md`)

- **CẤM** dùng chung một file `PROGRESS.md` ở gốc repo rồi commit trên nhiều nhánh khác nhau.
- Mỗi nhánh nếu cần lưu tiến độ để bàn giao cho Agent tiếp theo thì ghi vào `progress/<ten-nhanh>.md` (ví dụ: `progress/feature-10_tt74-excel-importer.md`) hoặc giữ trong `.gitignore`.

## 3. Cách làm việc theo từng chức năng nhỏ

- Khi nhận một yêu cầu lớn (ví dụ: thêm luồng nạp dữ liệu mới hoặc nâng cấp thuật toán):
  1. Liệt kê các bước nhỏ (Schema -> Model/Seed -> Service -> Router -> Unit Test) để người dùng xác nhận trước.
  2. Làm xong từng bước nhỏ thì chạy test kiểm chứng, báo kết quả thật, rồi commit riêng từng bước.
  3. Xóa sạch code thừa, comment lỗi thời và log debug trước khi commit.
