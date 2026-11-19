# Nguyện vọng — kết quả triển khai và kiểm chứng

Ngày: 15/11/2026.

## Kết quả

- Bước Nguyện vọng hiển thị đủ R–I–A–S–E–C, tên tiếng Việt, mức sở thích và số câu trả lời. Dữ liệu thiếu/tạm tính không biến thành điểm giả. Nguyên nhân cũ: `topHollandPreview` dùng `.slice(0, 3)`.
- Tách nghề đơn, giữ nguyện vọng khi đổi trường lựa chọn; trường tự sinh cũ được xóa khi sửa nghề. Nguyện vọng nhiều nghề có lựa chọn xác nhận riêng.
- Ngành mục tiêu, ngành đạt mốc hiện tại và ngành chưa đủ dữ liệu được trình bày riêng. Không dùng TARGET cũ, LLM hoặc nhánh dự phòng để xác nhận khả thi.
- Một hồ sơ dữ liệu được dùng xuyên suốt. Xóa điểm/nguyện vọng được tôn trọng; dữ liệu lịch sử không hồi sinh qua backend hoặc local storage.
- Chỉ so điểm đúng nguồn/phương thức, đúng tổ hợp và điều kiện môn; kiểm tra trước làm tròn/kẹp điểm. Thiếu nguồn xác minh trả UNKNOWN.
- Catalog DB đang hoạt động là nguồn chính, kể cả catalog admin nhập thay thế. Không thêm lại ngành đã bị admin loại. Khi không có catalog DB mới dùng seed. Analyzer nhận đầy đủ catalog đang hoạt động trước giới hạn hiển thị.

## Arena

8 đối thủ, 3 vòng, 43 lượt xử lý; seed 264329. Trọng tài độc lập chọn a003, điểm chung kết được bracket tính: 95–92,5.

Chiến lược: Systems thinking + Smallest version first + User empathy first.

Phương án thắng xử lý được phản biện về điểm giả khi thiếu đáp án, tham chiếu không cùng phương thức, mất độ chính xác điểm, tổ hợp mặc định, trộn dữ liệu lịch sử và nguyện vọng mơ hồ.

Bản đầy đủ: `.arena/run-20261115-091223-s264329/r3/r3-m01.a003.solution.md`.
Hồ sơ vòng đấu: `.arena/run-20261115-091223-s264329/arena.json`.

## Kiểm chứng cuối

- `ENVIRONMENT=test; py -3.11 -m pytest backend/tests -q --tb=short`: **219 passed**, 2 warnings đã tồn tại ở baseline (Starlette deprecation, AsyncMock tại test nhập Excel); thêm cảnh báo cấu hình pytest-asyncio.
- `npm.cmd run build`: thành công; còn cảnh báo kích thước bundle.
- `npm.cmd run lint`: exit 0; 25 warnings. Log đầy đủ `.arena/frontend-lint.txt`.
- `node .arena/browser-qa.cjs`: **28 assertions passed**, desktop 1440px, mobile 390px, thiếu/sai đáp án, chế độ xem lại, đổi nghề, bàn phím, lỗi lưu và response thật từ backend được mô phỏng trên trình duyệt.
- `node .arena/browser-save-qa.cjs`: **36 assertions passed**, lưu thành công, chọn nghề mơ hồ, response trễ, reload, hồ sơ chỉ có điểm và lịch sử cũ, xóa dữ liệu có chủ ý.
- API đang chạy trên localhost trả NO_CURRENT_OPTIONS / MATCHED / PARTIAL cho hồ sơ thử; không phát sinh lưu dữ liệu người dùng thật.
- `git diff --check`: sạch. Các chỉnh sửa sẵn có được giữ; đối chiếu độc lập AcademicInputForm, Sidebar, ExplanationBox không thay đổi so với baseline.

Ảnh: `.arena/aspiration-after-1440.png`, `.arena/aspiration-after-390.png`, `.arena/aspiration-result.png`.

## Giới hạn dữ liệu cần biết

Seed catalog có 435 ngành và **0 `readiness_reference` đã xác minh**. Vì vậy dữ liệu thực hiện có được trình bày là mục tiêu/khám phá, không được gắn nhãn đạt mốc hiện tại. Đây là trạng thái thiếu căn cứ đối chiếu, không phải kết luận học sinh không có khả năng theo nghề.

Bộ lọc READY_REFERENCE đã được kiểm tra bằng reference tổng hợp chỉ dành cho test. Để có lựa chọn đạt mốc ở dữ liệu thực, cần nguồn backend đã xác minh: ID, nguồn, loại điểm phù hợp, phương thức hỗ trợ SUM_THREE_SUBJECTS, tổ hợp được khai báo, cutoff/minimum; nguồn tuyển sinh cần trường, chương trình và năm. Không tự gắn verified cho các điểm heuristic cũ. Các phương thức có trọng số/quy đổi khác tiếp tục UNKNOWN.

## Modern Web Guidance

Áp dụng guide `forms`: nối nhãn với input và dùng radio/checkbox gốc, fieldset/legend, trạng thái disabled và focus để điều khiển được bằng bàn phím; hướng dẫn: “always associate `<label>` with its input using `for` and `id`”.

## Tự đánh giá

| Tiêu chí | Điểm | Bằng chứng / giới hạn |
|---|---:|---|
| Chính xác | 4/5 | 219 test + 64 xác nhận; nguồn tuyển sinh thực chưa được xác minh nên fail closed. |
| Đầy đủ | 4/5 | Đủ 6 nhóm, arena8, bộ lọc và lưu/xem lại; chưa thể xác nhận ngành thực khi thiếu reference tương thích. |
| Rõ ràng | 4/5 | Phân vùng mục tiêu/hiện tại/thiếu dữ liệu; người dùng vẫn cần chọn trường/phương thức để kết luận sát hơn. |
| Khả dụng | 4/5 | Build/API/browser hoạt động; để danh sách READY có ý nghĩa thực tế cần bổ sung dữ liệu nguồn. |
| Ngắn gọn | 4/5 | Loại nhánh fallback/LLM sai lệch; thay đổi tích hợp nhiều file vì dữ liệu đi qua cả hai lớp. |

Trung bình 4,0/5. Việc cần làm tiếp thuộc dữ liệu: nhập và xác minh reference phù hợp, không nới bộ lọc để tạo kết quả giả.
