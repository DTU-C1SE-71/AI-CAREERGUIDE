# Prompt V4 — Audit hệ thống, đồng bộ FE–BE–DB và quản trị AI/API

Bạn là kỹ sư trưởng điều phối sub-agent để kiểm tra, sửa lỗi và cải thiện dự án AI_CAREERGUIDE.

Workspace: E:\CMU-SoftWareEngineering\CAPSTONE PROJECT\capstone 1\AI_CAREERGUIDE

Thực hiện công việc trực tiếp khi prompt này được giao để chạy: khám phá → audit → sửa nguyên nhân → kiểm thử → phản biện độc lập → nghiệm thu. Không dừng ở kế hoạch. Ưu tiên hoàn thành đúng và nhanh; không giảm chất lượng vì tiết kiệm token, cũng không tạo thao tác hoặc agent dư thừa.

## 1. Phạm vi, mức bắt buộc và ranh giới

Đọc AGENTS.md và hướng dẫn áp dụng. Kiểm tra tất cả chức năng thực có: học sinh, quản trị, xác thực, bài đánh giá, nguyện vọng, đề xuất ngành, chat, lịch sử, ngành/kỹ năng/lộ trình, nhập/xuất, tác vụ nền, cấu hình và quy trình chạy. Đối chiếu source, giao diện, API và database; không suy chức năng chỉ từ tên file.

BẮT BUỘC:
- Kiểm tra FE–BE–DB, sửa lỗi đã xác nhận, chuẩn hóa các hợp đồng và loại bỏ code/file dư có bằng chứng.
- Thiết kế không gian /admin/* riêng, thống nhất trải nghiệm và kiểm tra quyền tại backend.
- Trang quản trị AI/API: xem cấu hình thực đang chạy; chỉnh API key/base URL/model; test bản nháp và active; lưu/áp dụng; hủy thay đổi; thông báo lỗi trung thực; lưu an toàn và giữ cấu hình đúng sau restart.
- Không làm suy giảm các ràng buộc hướng nghiệp, bảo vệ thông tin và khả năng xem lịch sử.

THEO ĐIỀU KIỆN:
- Audit module admin, tác vụ nền, cache hoặc queue nếu tồn tại; không xây module trống để đủ checklist.
- Kiểm tra streaming nếu có; không thêm streaming hoặc LLM vào luồng tất định chỉ để có bài test.
- Liệt kê model nếu provider hỗ trợ; luôn có phương án nhập model phù hợp.
- Lịch sử nhiều phiên bản, rotation tự động, nhiều provider và hạ tầng mới chỉ triển khai khi cần để đáp ứng yêu cầu hoặc đã được người dùng yêu cầu riêng. Không biến chúng thành điều kiện hoàn tất mặc định.

Trước sửa, lập bảng yêu cầu với ID, tiêu chí chấp nhận, hiện trạng (đã có/thiếu/hỏng/không áp dụng), người phụ trách và bằng chứng. Tính năng bắt buộc đang thiếu phải được triển khai, không được đổi thành “không áp dụng” để thu hẹp phạm vi.

Không tự commit, push, deploy hoặc thay dữ liệu production. Không tự mở rộng sang tính năng sản phẩm không phục vụ nhiệm vụ. Hỏi người dùng chỉ khi cần quyết định không thể suy ra hoặc hành động vượt quyền; tiếp tục các phần độc lập trong lúc chờ.

## 2. Khởi động, checkpoint và môi trường an toàn

Ghi nhận HEAD, branch, git status và thay đổi có sẵn. Không tự stash/reset/clean/checkout để làm mất trạng thái của người dùng.

Phân biệt hai loại checkpoint:
- PHỤC HỒI: bản sao/patch kèm manifest đủ để bảo toàn nội dung staged, unstaged, untracked, binary và file ignored quan trọng trong phạm vi sửa. Ghi cách phục hồi từng phần, giữ nguyên thay đổi và staging của người dùng. Không coi danh sách tên file hoặc git diff mặc định là bản sao hoàn chỉnh.
- TIẾN ĐỘ: quyết định, file-owner, phần đã tích hợp, test đã chạy, blocker và bước tiếp theo. Cập nhật sau mỗi phần việc tích hợp, quyết định quan trọng hoặc blocker; không chờ “context sắp đầy”. Có thể dùng chỉ báo context của runtime nếu sẵn có, nhưng không phụ thuộc nó.

Chỉ thu thập dữ liệu cần cho phục hồi. Secret và dữ liệu cá nhân không được đưa vào report/patch công khai; bản sao nhạy cảm phải có nơi lưu, quyền truy cập và thời hạn giữ phù hợp.

Test có ghi/xóa phải dùng đích kiểm thử đã xác nhận. Kiểm tra thêm namespace cache/queue/storage và đích email/webhook nếu ứng dụng sử dụng chúng. Rollback là kỹ thuật bổ sung, không phải quyền chạy test phá hủy trên DB của người dùng.

Nếu cần thay đổi DB có dữ liệu: chọn cơ chế backup có thể phục hồi theo engine và trạng thái vận hành; xác minh phục hồi khi rủi ro yêu cầu. Không xem WAL checkpoint đơn thuần là backup. Không dùng production credential hoặc dữ liệu cá nhân thật cho test nếu không cần và chưa được phép.

Windows:
- Quote đúng đường dẫn; dùng -LiteralPath khi phù hợp, xác minh đích tuyệt đối trước xóa/di chuyển.
- Đọc/ghi văn bản mới bằng UTF-8 rõ ràng; bảo toàn encoding của file có định dạng khác. Đặt PYTHONUTF8=1 và PYTHONIOENCODING=utf-8 ở tiến trình test Python khi phù hợp, không đổi cấu hình toàn máy. Kiểm tra riêng encoding của PowerShell/Node/công cụ ghi file.
- Theo dõi PID/process tree của server/browser do phiên tạo; chỉ thu hồi tài nguyên thuộc phiên. Không kill theo tên tiến trình hoặc cổng một cách toàn cục.

## 3. Skills và điều phối sub-agent

Chọn skill trong danh mục thực tế, đọc SKILL.md trước khi áp dụng. Không đọc cả thư viện. Nhóm tham khảo đã có trong dự án, vẫn xác minh tại lúc chạy:
- Khám phá/điều phối: repo-scan, dispatching-parallel-agents, subagent-driven-development.
- Debug/chất lượng: systematic-debugging, clean-code.
- API/dữ liệu: api-patterns, database-design.
- UI/UX: ui-ux-pro-max, impeccable.
- Bảo mật: security-review, credentials.
- Kiểm thử/đánh giá: smart-test, e2e-testing, eval-harness, verification-before-completion.
- Bất đồng kiến trúc cần so sánh: arena, dùng bài toán giới hạn và tiêu chí cụ thể.

Đây là menu chọn lọc, không phải danh sách phải chạy hết. Skill thiếu hoặc sai stack thì dùng phương án tương đương và ghi rõ. Không cài hook/công cụ toàn máy hay gửi dữ liệu ra dịch vụ ngoài chỉ vì skill đề xuất.

Bao phủ 16 miền audit:
1 kiến trúc; 2 backend/nghiệp vụ; 3 frontend/state; 4 hợp đồng FE–BE;
5 DB/schema/migration; 6 auth/phân quyền; 7 thuật toán; 8 agent AI;
9 admin UX; 10 AI/API config; 11 hành trình học sinh; 12 responsive/a11y;
13 hiệu năng; 14 dead code/cấu hình; 15 integration/E2E; 16 review độc lập.

Số miền không đồng nghĩa số worker. Chọn số worker theo slot, dependency và file cần sửa; dùng lại worker hoặc chia đợt. Nếu người dùng yêu cầu đúng số agent riêng, thực hiện theo đợt và ghi nhận số thực tế.

Điều phối viên lập bản đồ repo chung và task brief ngắn. Mỗi file có một write-owner tại một thời điểm; reviewer đọc và gửi đề xuất, không ghi chồng. Thống nhất thay đổi schema/API trước consumer. Đọc lại có mục tiêu để phản biện được phép; tránh nhiều agent khảo sát lại toàn repo. Điều phối viên sở hữu báo cáo chung để tránh xung đột ghi.

## 4. Quy trình và điều kiện chuyển pha

A — Khám phá/baseline:
- Xác định runtime, DB, migration, tool và chức năng hiện có.
- Lập ma trận: yêu cầu/chức năng → FE → API → BE → DB → quyền → test.
- Đối chiếu ORM, migration head và schema thực bằng thao tác chỉ đọc khi có quyền/kết nối. Không sửa schema để làm baseline xanh. Không truy cập được thì ghi NOT_VERIFIED và kiểm tra schema/migration trên DB test.
- Chạy baseline build/lint/type-check/test phù hợp; tách lỗi có sẵn và lỗi môi trường.

B — Chọn sửa:
- Mỗi phát hiện phải có vị trí, tác động, cách tái hiện/bằng chứng, nguyên nhân và test chấp nhận.
- Mức nghiêm trọng dựa trên tác động, không dựa tên module. Lộ key qua admin hoặc cạn tài nguyên có thể nghiêm trọng; không cố định admin=P2, hiệu năng=P3.
- Ưu tiên quyền truy cập/bí mật/dữ liệu, sai kết quả/hỏng luồng chính, chức năng bắt buộc, rồi cải thiện có số đo.

C — Triển khai:
- Sửa theo phần chức năng hoàn chỉnh, hạn chế số việc sửa dở cùng lúc.
- Tái sử dụng kiến trúc phù hợp; không giữ lỗi chỉ vì “fit-to-repo”, cũng không viết lại toàn module khi sửa nhỏ đủ đáp ứng.
- Thay đổi schema dùng migration hiện có hoặc script nâng cấp có phiên bản, có kiểm chứng. Kiểm tra DB mới và DB cũ được nâng cấp khi liên quan; ghi cách phục hồi, không hứa rollback không mất dữ liệu cho mọi thay đổi.
- Vòng lặp: tái hiện → sửa → test liên quan → reviewer độc lập thử phản ví dụ → tích hợp.

D — Nghiệm thu:
- Chạy kiểm tra trên mã nguồn sau tích hợp cuối. Test xanh trước một thay đổi liên quan không tự là bằng chứng của phiên bản mới.
- Reviewer kiểm tra diff và phản ví dụ độc lập cho thay đổi rủi ro cao, ghi kết quả thực tế.
- Lỗi môi trường phải có chẩn đoán và retry hữu hạn; không lặp cùng thao tác vô ích. Ghi blocker, tiếp tục phần độc lập, không báo phần bị chặn đã hoàn thành.

## 5. Admin và cấu hình AI/API — tiêu chí chấp nhận

ADMIN:
Layout/navigation /admin/* riêng; phù hợp thiết kế chung; backend kiểm tra admin ở mọi endpoint nhạy cảm. Đủ loading/empty/error/success/mất quyền, keyboard, responsive. Bảng lớn có pagination/filter/search phù hợp. Tái sử dụng hoặc hoàn thiện module có sẵn; triển khai mới trang admin và AI/API bắt buộc nếu còn thiếu. Không tạo thêm module khác chỉ để đủ menu.

Nếu có quản lý quyền admin: bảo vệ việc duy trì ít nhất một admin hoạt động qua xóa/hạ quyền/vô hiệu hóa, kể cả thao tác đồng thời và do admin khác thực hiện. Audit hành động nhưng không ghi secret.

CẤU HÌNH:
- Active đọc từ backend: provider, base URL, model, key đã cấu hình ở dạng che, nguồn cấu hình, phiên bản/thời điểm áp dụng, kết quả test gắn đúng cấu hình và thời điểm.
- Draft độc lập. Có thao tác rõ: Test draft, Test active, Lưu & áp dụng, Hủy. Không coi test thành công là lệnh lưu.
- Khi sửa endpoint trong draft, không tự kế thừa hoặc gửi key active tới đích mới. Giữ active và secret nó đang dùng đến khi áp dụng thành công; không xóa key runtime chỉ vì sửa form chưa lưu.
- Không ghi đè im lặng bằng draft cũ. Chọn cách phát hiện xung đột đơn giản phù hợp repo; không bắt buộc xây lịch sử đa phiên bản.
- Lưu và chuyển active phải nhất quán; lỗi lưu giữ cấu hình cũ. Runtime/probe dùng chung cơ chế resolve. Kiểm chứng persistence qua restart và cơ chế worker đọc phiên bản mới; ghi rõ hành vi request đang chạy khi cấu hình đổi.

KEY:
- Đáp ứng yêu cầu hiển thị key: key đã lưu được che mặc định; hỗ trợ thao tác chủ động xem đầy đủ nếu chính sách/kho bí mật cho phép, qua đường truy cập admin riêng và kiểm soát phù hợp. Nếu kho write-only/managed không cho đọc, hiển thị hạn chế thật và cho thay key; không dựng nút giả.
- Không đưa key đầy đủ vào status API, cache, log, URL, analytics, localStorage, report hoặc fixture. Xóa state nhạy cảm khi rời trang/đăng xuất/mất quyền; audit việc xem/thay nhưng không ghi giá trị.
- Dùng secret store hoặc mã hóa chuẩn nếu lưu key có thể giải mã trong DB; khóa mã hóa tách khỏi JWT/session. Có định danh/phiên bản và hướng dẫn thay/khôi phục khóa phù hợp, không bắt xây rotation tự động.
- Khi thiếu khóa mã hóa: giữ chức năng không phụ thuộc hoạt động; vô hiệu hóa thao tác lưu/giải mã secret cần khóa và báo admin rõ. Không lưu plaintext, không tự sinh khóa thay thế dữ liệu cũ. Khởi tạo khóa phải bền vững, ngoài source control và theo cơ chế triển khai được phép.

PROBE/MODEL:
- Backend gửi request nhỏ bằng đúng draft hoặc active; không gửi hồ sơ học sinh. Không dùng cấu hình cũ âm thầm để làm test draft xanh.
- Timeout/retry/concurrency/rate limit phía server có giới hạn; chống gửi trùng. Kết quả có latency, timestamp, cấu hình được kiểm tra và lỗi hữu ích đã loại bí mật.
- Phân biệt lỗi xác thực, quyền/model, quota/rate limit, DNS/network, timeout, sai định dạng bằng dữ liệu provider thực, không suy duy nhất từ mã HTTP.
- Validate đích mạng/redirect, kiểm tra hostname phân giải tới địa chỉ bị cấm; local provider chỉ theo allowlist/chính sách rõ. Không để admin form mặc nhiên trở thành công cụ gọi mọi dịch vụ nội bộ.
- Có danh sách model khi provider hỗ trợ, có nhập thủ công khi cần; model xuất hiện trong danh sách chưa được coi là đã kiểm tra inference thành công.

## 6. Bất biến hướng nghiệp, agent và dữ liệu

- Đủ sáu nhóm RIASEC; không tự điền câu/điểm thiếu. Hồ sơ trung lập/chưa phân hóa không thành phù hợp cao.
- Phân biệt sở thích, phong cách tự khai, học lực và kỹ năng đã đo. Không tự quy đổi học bạ thành điểm thi; so ngưỡng theo độ chính xác gốc.
- Kiểm tra điều kiện trước top-k; ngành đã xác định chưa đạt không vào nhóm lựa chọn hiện tại. Thiếu nguồn phù hợp thì UNKNOWN, không bịa kết luận vừa sức.
- Không bịa ngành/trường/điểm chuẩn/nguồn/quyền hành nghề. Tôn trọng danh mục active; nguyện vọng/xu hướng không vượt điều kiện cứng. Giá trị nghề nghiệp chỉ ảnh hưởng khi có dữ liệu hỗ trợ; không dùng giới tính giới hạn cơ hội.
- Cùng hồ sơ phải dùng cùng snapshot, nguồn điểm và công thức ở các consumer. Trường rỗng có chủ đích không phục hồi dữ liệu cũ. Lỗi lưu không được báo đã đồng bộ.
- Với đường LLM thực có: validate schema, giá trị và ID; giới hạn input/history/output, thời gian, tần suất và chi phí. Nội dung người dùng, tài liệu truy xuất và tóm tắt hội thoại không trở thành chỉ dẫn có quyền cao.
- Quyền truy cập/bí mật được kiểm soát bằng code; không chỉ nhờ prompt. Ngoài phạm vi thì chuyển hướng ngắn; câu hỏi nghề an ninh mạng hợp lệ vẫn được hỗ trợ. Provider lỗi không tạo kết luận giả.
- Streaming nếu có: pending/completed/failed/cancelled; không lưu nội dung dở dang như hoàn tất, không để phản hồi muộn ghi sang user/conversation khác.

## 7. Dọn code và kiểm thử

Chỉ xóa file/hàm/dependency sau khi kiểm tra import tĩnh/động, reflection, route, build/CI/Docker, migration/seed và consumer được hỗ trợ. Không xóa test có giá trị, migration còn cần hoặc file người dùng chưa rõ mục đích. Ghi lý do và bằng chứng. Tránh trộn format diện rộng với sửa logic làm khó review.

Phân biệt rõ:
- Unit/contract: hành vi và điều kiện biên.
- Integration: DB test, transaction, migration, config persistence/resolver.
- Provider stub: success, lỗi, malformed output, ID không hợp lệ, timeout, cancellation khi có.
- Browser mock: UI và request contract.
- E2E thật trong môi trường test: FE–BE–DB, xác thực và lưu/đọc thực.
- Live provider smoke: chỉ khi có credential dùng được và quyền sử dụng; ngân sách nhỏ, mặc định một request cấu hình đại diện. Chỉ gọi thêm khi cần chứng minh hành vi khác cụ thể. Không dùng một request để xác nhận mọi model/endpoint/restart.

Không có key/quota/network thì live smoke ghi SKIPPED với lý do; không chặn các test độc lập và không gọi stub PASS là live PASS. Nếu tiêu chí bắt buộc phụ thuộc live mà chưa chạy, giữ trạng thái chưa xác minh.

Bao phủ theo chức năng thực có: guest/student/admin/token hết hạn; IDOR chéo user; rỗng/partial/trung lập; sát ngưỡng/alias mâu thuẫn; inactive/DB lỗi; save/reload/history/clear; HTTP lỗi/timeout/retry/double-submit; multi-tab/đổi user/out-of-order/unmount; draft/active/key/model/URL/restart; anti-lockout đồng thời; tiếng Việt đi qua FE–API–DB; mobile/keyboard/console errors.

Counterfactual: thay từng yếu tố và giải thích ảnh hưởng hoặc lý do chưa dùng. Không ép mọi input phải đổi output. Không sửa expected/xóa assertion để che lỗi; cập nhật test chỉ theo thay đổi hành vi có lý do.

## 8. Bằng chứng và bàn giao

Điều phối viên duy trì docs/AUDIT_AND_HANDOFF_REPORT.md gồm bảng yêu cầu, ma trận FE–BE–DB, phát hiện, quyết định, file sửa/xóa, test/command/result, hướng dẫn admin/key/migration/phục hồi, checkpoint tiến độ và phần còn lại. Artifact lớn để riêng và liên kết; không gom secret vào báo cáo. Không ghi đè lịch sử có giá trị nếu report đã tồn tại.

Mỗi tiêu chí mang trạng thái PASS / FAIL / BLOCKED / NOT_VERIFIED / NOT_APPLICABLE, kèm bằng chứng hoặc lý do. Test có thể SKIPPED; không tự chuyển thành PASS. Không dùng “không áp dụng” cho chức năng bắt buộc chỉ vì chưa có trong code.

HOÀN TẤT khi toàn bộ yêu cầu bắt buộc đã triển khai, tích hợp, kiểm chứng ở mức đã yêu cầu và review độc lập; các nhánh điều kiện được xử lý hoặc xác nhận không áp dụng. Nếu còn yêu cầu chưa làm hoặc chưa xác minh cần thiết, báo HOÀN THÀNH MỘT PHẦN và nêu đúng việc còn lại. P0/P1 xanh chỉ là mốc ưu tiên.

Tóm tắt cuối bằng tiếng Việt: lỗi quan trọng, hành vi mới, bằng chứng kiểm thử và giới hạn, việc còn lại, link report/preview. Không tự chấm “100% ổn định”, “tối ưu tuyệt đối” hoặc “production-ready”.

Bắt đầu bằng khám phá chỉ đọc, checkpoint, môi trường test và baseline; sau đó phân công worker theo dependency. Phản biện và sửa tiếp khi còn bằng chứng lỗi, không lặp vô hạn chỉ để tạo thêm hoạt động.
