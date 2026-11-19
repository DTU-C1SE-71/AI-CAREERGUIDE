# Audit và triển khai thuật toán hướng nghiệp — 16/11/2026

## Kết luận

Luồng trước sửa chưa liên kết đầy đủ dữ liệu bài làm với các phần tư vấn. Có trường hợp thiếu câu trả lời tư duy vẫn nhận điểm phù hợp tối đa, chat dùng cách chuẩn hóa RIASEC khác scorer, xem lịch sử không giữ cùng hồ sơ, và dữ liệu chưa đủ nguồn vẫn có thể xuất hiện dưới nhãn an toàn. Vì vậy không thể kết luận kết quả cũ luôn phù hợp hoặc vừa sức.

Bản sửa dùng dữ liệu gốc và trạng thái bằng chứng chung. Sở thích, phong cách tự khai, học lực, nguyện vọng và điều kiện tham chiếu có vai trò riêng. Thiếu dữ liệu không tự biến thành điểm tốt. Kết quả là gợi ý có điều kiện; không phải xác suất trúng tuyển, chứng nhận năng lực hay quyền hành nghề.

## Arena đã hoàn thành

- Run: `run-20261115-173436-s899909`, seed `899909`.
- 16 phương án, 4 vòng loại, 91 công việc spawn/attack/defend/judge theo kế hoạch. Chạy theo đợt 3 agent do giới hạn đồng thời của môi trường; không phải 16 agent chạy cùng lúc.
- Champion: **a007**, chiến lược **Working backwards / Smallest version first / Edge cases first**.
- Chung kết: **67–59** trước a008. Đây là điểm chấm phương án trong Arena, không phải độ chính xác của hệ thống.
- Nguồn kiểm tra: `.arena/run-20261115-173436-s899909/arena.json` và bản giải pháp đầy đủ `.arena/run-20261115-173436-s899909/r4/r4-m01.a007.solution.md`.
- Điều chỉnh khi triển khai: giữ danh mục DB có dữ liệu là nguồn chính thức; không gộp seed để hồi sinh ngành đã bỏ khỏi danh mục. Seed chỉ dùng khi chưa có dữ liệu DB. Lỗi DB trả lỗi có kiểm soát.

## Hành vi được triển khai

| Phần | Hành vi mới |
|---|---|
| Holland | Hiển thị đủ R, I, A, S, E, C và số câu đã trả lời; ba mã chỉ là tóm tắt nhóm nổi bật khi có cơ sở. |
| Bằng chứng | Giữ dữ liệu gốc, phân biệt thiếu/thiếu một phần/đủ nhưng chưa phân hóa. Không tự điền đáp án tư duy. |
| Xếp hạng | Chỉ đưa trụ cột có bằng chứng vào trọng số; điểm trụ cột thiếu là null. Chiến lược nguyện vọng tác động trọng số nhưng không vượt điều kiện học lực. |
| Nguyện vọng | Giữ mục tiêu người dùng, đối chiếu nghề với ngành đang hoạt động; lựa chọn cần cải thiện được tách khỏi đề xuất hiện tại. |
| Giá trị làm việc | Chỉ tính khi danh mục có thuộc tính tương ứng. Thiếu dữ liệu thu nhập/ổn định được thông báo, không bịa tác động. |
| Điều kiện học lực | Đối chiếu trước top-k, yêu cầu nguồn/thang điểm/phương thức/tổ hợp phù hợp; giữ độ chính xác điểm gốc. Không có nguồn thì UNKNOWN. |
| Hồ sơ | Dashboard, chi tiết ngành, chat và phân tích kỹ năng dùng cùng builder/resolver; trường rỗng chủ động xóa dữ liệu cũ. Cả hồ sơ mới nhất và lịch sử lấy điểm/loại điểm từ cùng snapshot; fallback điểm cũ chỉ dành cho snapshot legacy thiếu trường điểm. |
| Kỹ năng | Điểm môn học chỉ gợi ý nội dung nền tảng. Chỉ diagnostic có kết quả hoặc thang đo rõ ràng mới xác nhận kỹ năng; danh mục kỹ năng thiếu không có nghĩa đã sẵn sàng. |
| Tư vấn | Trả lời từ danh mục và scorer, nhận cách gọi nghề thông thường, giải thích thiếu bằng chứng và lập kế hoạch khám phá theo giờ đã chọn. |
| Lỗi mạng | Không thay bằng lời khuyên giả lập hay điểm phù hợp tự tạo. Lưu bài chờ tối đa 8 giây, giữ bản cục bộ khi lỗi và chỉ báo đồng bộ khi nhận ID máy chủ. |

## Giới hạn agent đã áp dụng

1. Danh mục ngành đang hoạt động là nguồn chung cho xếp hạng, giải thích, chat, insight và roadmap. Ngành không tồn tại trả 404.
2. Người dùng chỉ đọc hồ sơ của tài khoản đã xác thực. Khách không chọn được ID hồ sơ lưu; body không thể đổi chủ hồ sơ.
3. Câu hỏi ngoài phạm vi và yêu cầu lấy khóa/cấu hình/prompt/hồ sơ người khác được chuyển về tư vấn hướng nghiệp. Hỏi nghề an ninh mạng vẫn hợp lệ.
4. Chat, giải thích và insight cá nhân dùng nội dung tất định từ sự kiện đã kiểm tra. Không đưa văn bản tùy ý của mô hình vào kết luận tuyển sinh.
5. Status/cấu hình/probe LLM chỉ dành cho quản trị viên. Đổi endpoint phải có khóa riêng; không gửi khóa lưu sẵn tới endpoint do người gọi đổi.
6. Giới hạn độ dài dữ liệu, lịch sử, giờ học và ngân sách probe. Cache gắn với chủ hồ sơ, dữ liệu gốc, danh mục và phiên bản chính sách.
7. Roadmap mẫu công khai là gợi ý chưa xác minh; bỏ nguồn học liệu giả. Nội dung kỹ năng do client gửi không tự trở thành thiếu hụt đã đo.

## Kiểm chứng

- Backend: **271 test đạt, 2 cảnh báo, 16,55 giây** với `ENVIRONMENT=test; py -3.11 -m pytest backend/tests -q --tb=short`. Cảnh báo còn lại thuộc Starlette/anyio deprecation và AsyncMock của test Excel; không có test thất bại.
- Frontend: `npm.cmd run build` thành công; `npm.cmd run lint` thành công với **23 cảnh báo, 0 lỗi**. Còn cảnh báo kích thước bundle và các mẫu React hiện hữu.
- Browser: **104 assertion đạt** — submission/sync 36, coherence 18, lưu/chọn lịch sử 44, nhãn/readiness/progress bars 6.
- Browser kiểm tra cả lỗi HTTP, timeout, ID lưu thành công, giữ điểm khi offline, raw payload, lựa chọn lịch sử và loại bỏ phản hồi chat đến muộn.
- `git diff --check` đạt.
- Các test dùng fixture/mock và DB kiểm thử; không gọi mô hình trả phí. Browser chặn API bằng fixture, chưa phải E2E với tài khoản/DB triển khai thật.

## Giới hạn còn lại và phần nên phát triển tiếp

- Danh mục hiện chưa cung cấp đầy đủ mốc tuyển sinh đã xác minh theo trường, chương trình, năm, phương thức và loại điểm. UNKNOWN là kết quả đúng khi thiếu nguồn; chưa thể đảm bảo mọi ngành hiển thị đều vừa sức.
- Trọng số và mức đóng góp sở thích/giá trị làm việc là heuristic, chưa được hiệu chỉnh bằng dữ liệu kết quả học tập hoặc tuyển sinh thực tế. Không so sánh điểm giữa hai hồ sơ có độ phủ bằng chứng khác nhau như tiến bộ năng lực.
- Cần quy trình nhập, duyệt và làm mới dữ liệu tham chiếu; lưu nguồn, thời điểm, phiên bản và điều kiện áp dụng. Không dùng điểm học bạ như điểm thi nếu chưa có quy đổi được xác minh.
- Nên xây bộ đánh giá có chuyên viên hướng nghiệp chấm độc lập: tính liên quan của ngành, khả năng đáp ứng điều kiện, mức rõ ràng của giải thích, tỷ lệ từ chối nhầm và mức hài lòng người dùng. Arena không thay thế kiểm định này.
- Chat tất định giảm rủi ro và chi phí nhưng độ linh hoạt diễn đạt còn hạn chế. Nếu bổ sung LLM, chỉ cho chọn ý định và ID sự kiện có schema; kết luận/điểm/thứ hạng vẫn do hệ thống kiểm tra và render.
- Các test trình duyệt hiện kiểm tra hợp đồng API được mô phỏng. Cần nghiệm thu thêm với tài khoản và DB triển khai thật trước phát hành.

## Các điểm vào mã nguồn

- `backend/app/services/recommender/catalog.py`, `evidence.py`, `readiness.py`, `service.py`.
- `backend/app/services/llamaindex_rag_orchestrator/guidance_boundary.py`, `guidance_rag.py`, `router.py`.
- `backend/app/services/major_insight/service.py` và `backend/app/services/gap_roadmap_engine/`.
- `frontend/src/utils/assessmentPayload.ts`, `frontend/src/hooks/useSelectedAssessment.ts`.
- `frontend/src/components/assessment/HollandInterestSummary.tsx`, `frontend/src/pages/AIChatAdvisor.tsx`, `MajorDetail.tsx`, `Dashboard.tsx`.
