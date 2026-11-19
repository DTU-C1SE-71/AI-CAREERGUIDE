# Bàn giao AI CareerGuide — Chat học tập, hướng nghiệp và đề xuất theo hồ sơ

- Ngày cập nhật: 19/11/2026, múi giờ Asia/Saigon.
- Workspace chính: `E:/CMU-SoftWareEngineering/CAPSTONE PROJECT/capstone 1/AI_CAREERGUIDE`, nhánh `develop`.
- Workspace đã dùng để build/chạy Docker: `E:/CMU-SoftWareEngineering/CAPSTONE PROJECT/capstone 1/AI_CAREERGUIDE_1`, nhánh `feature/sync-careerguide-1`.
- Bản bàn giao trước: `docs/handoffs/2026-11-19-before-chat-and-profile-updates.md`. Đây là lịch sử, có nội dung đã bị thay thế; mật khẩu dạng rõ đã được ẩn trong bản lưu.
- Tài liệu này ghi nhận công việc đã làm và bằng chứng; các đề xuất ở phần tiếp theo chưa phải yêu cầu triển khai đã được người dùng chốt.

## 1. Mục tiêu và yêu cầu đã thống nhất

Chat phải trả lời trực tiếp câu hỏi hướng nghiệp, chọn ngành, nghề nghiệp, mục tiêu tương lai và học tập, bao gồm kiến thức phổ thông, phép tính, bài tập và lập trình. Câu ngoài phạm vi hoặc chưa rõ ý được phản hồi cục bộ để tránh tốn token. Khi mở chat chỉ thực hiện một lượt kiểm tra kết nối tự động cho mỗi lần mở, không tự khóa sau 5 phút hoặc probe lại khi gửi câu hỏi. Phần đề xuất ngành lấy lớp và giới tính từ hồ sơ đã lưu, chỉ hiển thị giải thích, không có selector thay đổi hồ sơ ngay tại Dashboard.

Người dùng đã hỏi về việc dùng mô hình ngữ nghĩa có sẵn để giảm chặn nhầm và độ nặng trên máy. Mới dừng ở tư vấn, chưa yêu cầu tải/cài mô hình, benchmark hoặc train. Yêu cầu mới nhất chỉ là tạo tài liệu bàn giao.

## 2. Trạng thái hiện tại

### 2.1. Những phần đã sửa và đã kiểm chứng trong phiên

- Đã tìm đúng nguyên nhân API key tốt nhưng chat trả mẫu: frontend bundle cũ không gửi `connection_revision`; backend mới cần receipt hợp lệ trước khi gọi `adapter.chat()`. Nhãn “Trực tuyến” của bundle cũ được hardcode, không chứng minh câu hỏi thật đã gọi LLM.
- Đã nối schema/router/frontend cho luồng `/chat/connection`, trả và gửi receipt. Các nguồn cấu hình LLM dùng `resolve_snapshot()`; không ghép credential tùy tiện từ nhiều cấu hình.
- Frontend chỉ probe tự động một lần mỗi lần mở chat, kể cả React StrictMode; đổi ngành/hồ sơ/đường dẫn và gửi câu hỏi không tạo probe mới. Retry sau lỗi là thao tác thủ công. Đóng rồi mở lại tạo một lượt kiểm tra mới.
- Receipt đã bỏ TTL 300 giây và map lưu theo event loop. Dùng nonce + chữ ký HMAC, chuỗi URL-safe dài 65 ký tự, ràng buộc revision cấu hình và `SECRET_KEY`. Không có thời hạn chat 5 phút. Đổi cấu hình hoặc khóa ký làm receipt cũ không hợp lệ.
- `verify_receipt()` chỉ đọc cấu hình và xác minh chữ ký cục bộ; nó KHÔNG gọi provider. Một receipt không phải bảo đảm provider sẽ luôn hoạt động.
- Bộ lọc chạy trước scoring/generation: `allow`, `redirect`, `clarify`, `greeting`. Lời chào, chưa rõ ý, ngoài phạm vi, yêu cầu thông tin nội bộ đều không gọi LLM sinh câu trả lời.
- `render_chat()` trả `REDIRECT` là điểm dừng cuối, không được tiếp tục gọi provider.
- Câu bị lọc và phản hồi tương ứng được loại khỏi lịch sử gửi LLM. Câu nối tiếp chỉ kế thừa từ ngữ cảnh USER phù hợp; lời chào của assistant hoặc ngành đang chọn không tự cấp quyền cho câu ngoài phạm vi.
- Đã mở rộng nhận diện toán học, ký hiệu Unicode, cách viết không dấu/viết tắt, kiến thức môn học và Python/C++/JavaScript/PHP/C/JSON/XML… Không thực thi `eval` hoặc chạy code do người dùng nhập.
- Câu thuần học tập dùng prompt trợ giảng riêng, KHÔNG gọi `guidance_facts()`, KHÔNG scoring hồ sơ cá nhân và KHÔNG chèn catalog/readiness vào prompt. Câu pha hướng nghiệp, như học Python để làm kỹ sư AI, vẫn dùng luồng grounding hướng nghiệp.
- Provider lỗi được phân biệt với phản hồi lọc cục bộ: `is_fallback=true`, `response_source=offline_guidance`, `connection_available=false`. Thành công LLM: `is_ai_generated=true`, `response_source=ai_advisor`. Phản hồi cục bộ: `verified_guidance`.
- Dashboard đã bỏ selector lớp/giới tính, state chỉnh riêng, fallback localStorage cũ và mặc định tự gán Nam/Lớp 12. Chỉ lấy `user.grade_level` và `user.gender` từ AuthContext/hồ sơ đã lưu.
- Banner giải thích lý do theo lớp và giới tính; thiếu thông tin thì nhắc cập nhật hồ sơ. Giới tính chỉ gợi mở thêm cơ hội khi phù hợp, không kết luận năng lực hoặc loại trừ ngành. Chỉ hiển thị trọng số thực tế từ backend khi đủ dữ liệu.
- Backend `/recommender/evaluate` và `/analyze-aspiration` ưu tiên tuyệt đối lớp/giới tính trong `current_user` với tài khoản đã đăng nhập, kể cả khi trường đó thiếu. Payload không được ghi đè. Khách vẫn có thể cung cấp context trong request.

Ví dụ câu trả lời đã xác minh qua HTTP thật sau lần triển khai backend cuối trong phiên:

| Câu hỏi | Kết quả quan sát |
| --- | --- |
| `phép chia là gì` | `is_ai_generated=true`, định nghĩa và ví dụ |
| `code python là gì` | `is_ai_generated=true`, giải thích Python |
| `code python hệ pt bậc 2` | `is_ai_generated=true`, trả mã Python; nội dung mơ hồ có thể được hiểu là hệ phương trình |
| `1+1=` | `is_ai_generated=true`, trả `1 + 1 = **2**` |
| `Python viết công thức nấu mì cho tôi` | `is_ai_generated=false`, phản hồi cục bộ, khoảng 7 ms trong lần kiểm tra |

### 2.2. Trạng thái khi viết tài liệu này

Lúc kiểm tra bàn giao, lệnh `docker ps` KHÔNG kết nối được Docker daemon:

```text
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
```

Chưa xác định nguyên nhân daemon không sẵn sàng; không tự bật Docker trong lượt viết tài liệu. Trước đó backend/frontend/db đã healthy và các kiểm tra HTTP ở bảng trên đã thành công. Không được suy diễn rằng các container hiện vẫn đang chạy.

Cả hai workspace còn nhiều thay đổi chưa commit, gồm thay đổi có trước phiên này. Không commit, reset, merge, push hoặc đồng bộ toàn bộ thư mục theo tài liệu cũ. Các sửa ở phần lõi chat đã được port có chọn lọc giữa hai workspace; hai repository KHÔNG đồng nhất hoàn toàn.

Đối chiếu tại thời điểm bàn giao:

- Giống nội dung: `chat_scope.py`, `guidance_rag.py`, `counselor_connection.py`, `services/recommender/router.py`, `TwoTierFunnelRecommendation.tsx` và các test mới liệt kê bên dưới.
- Khác nội dung: `Dashboard.tsx`, `AIChatAdvisor.tsx`, `schemas/rag.py`, `services/llamaindex_rag_orchestrator/router.py`. Một số khác biệt là giới hạn request/history và thay đổi riêng của workspace. Luồng chính vẫn đã được sửa ở cả hai; đọc diff trước khi port, không copy đè mù.
- Chi tiết drift đã đọc: main giới hạn chat 4.000 ký tự, schema history 12 phần tử, frontend gửi 10 lượt; runtime giới hạn 12.000 ký tự và 64 phần tử. Runtime route chat có `Cache-Control: no-store`; main route chat chưa có header đó. `Dashboard.tsx` còn khác phần catalog (main 597 dòng, runtime 767 dòng tại lúc bàn giao). Đây không phải yêu cầu tự ghi đè hoặc sửa thêm trong lượt tạo tài liệu.

## 3. Tệp liên quan

Đường dẫn dưới đây tương đối với từng workspace; nơi build Docker là `_1`.

| Tệp | Vai trò |
| --- | --- |
| `backend/app/services/llamaindex_rag_orchestrator/chat_scope.py` | Bộ lọc cục bộ, ngữ cảnh, biểu thức toán, chủ đề học tập/nghề nghiệp; `classify_chat_message()`, `is_academic_question()` |
| `backend/app/services/llamaindex_rag_orchestrator/guidance_rag.py` | `chat_with_career_counselor()`, gate trước LLM, prompt gia sư/hướng nghiệp, lọc history, nguồn phản hồi/fallback |
| `backend/app/services/llamaindex_rag_orchestrator/guidance_boundary.py` | Bằng chứng hồ sơ, quyền sở hữu, `in_scope()`, `render_chat()`, `forbidden_request()`; render dùng lại classifier |
| `backend/app/services/llamaindex_rag_orchestrator/counselor_connection.py` | Probe cố định `Reply with exactly OK.`, coalesce/cache/rate cap, ký và xác minh receipt không TTL |
| `backend/app/services/llamaindex_rag_orchestrator/router.py` | API `/chat/connection`, `/chat`, facade quản trị LLM |
| `backend/app/schemas/rag.py` | Request có `connection_revision`; response phân biệt AI/local/fallback và trạng thái kết nối |
| `backend/app/services/ai_config/service.py`, `adapter.py` | Nguồn snapshot cấu hình thực tế và HTTP provider; không in credential |
| `backend/app/core/ai_runtime.py`, `config.py` | Snapshot/validation/runtime settings; không đính kèm `.env` vào tài liệu |
| `frontend/src/pages/AIChatAdvisor.tsx` | Open lifecycle, một probe tự động, manual retry, gửi receipt, hiển thị nguồn phản hồi |
| `frontend/src/services/api.ts` | `requestJSON()`, timeout/abort và xử lý phiên |
| `frontend/src/pages/Dashboard.tsx` | Context đề xuất đọc từ hồ sơ, không có UI ghi lớp/giới tính tại Dashboard |
| `frontend/src/components/xai/TwoTierFunnelRecommendation.tsx` | Banner `profile-recommendation-context`, lý do đề xuất theo hồ sơ, không selector |
| `frontend/src/context/AuthContext.tsx` | Nạp `/identity/me`, giữ lớp/giới tính trong user |
| `frontend/src/components/profile/UserProfileModal.tsx` | Nơi sửa/lưu hồ sơ thực sự qua `/identity/profile` |
| `frontend/src/utils/assessmentPayload.ts`, `hooks/useSelectedAssessment.ts` | Chuẩn hóa bài làm và lựa chọn snapshot; đọc khi sửa context |
| `backend/app/services/recommender/router.py` | Bảo đảm evaluate/analyze-aspiration dùng demographics đã lưu của tài khoản |
| `backend/app/services/recommender/horizon_gender_engine.py`, `service.py` | Thuật toán hiện có và điều kiện nudge; không đổi thuật toán chỉ để khớp lời văn UI |
| `backend/tests/test_academic_chat_scope.py` | Ca học tập trong ảnh, biến thể, routing gia sư không nạp hồ sơ, mixed intent, off-topic |
| `backend/tests/test_chat_scope_gate.py` | Câu không hợp lệ không gọi provider kể cả có receipt; lọc history, REDIRECT và provider failure |
| `backend/tests/test_connection_session_receipt.py` | Không hết hạn 5 phút, không phụ thuộc worker state, chống sửa receipt, config rotation |
| `backend/tests/test_counselor_connection.py` | Có tại runtime `_1`; probe/coalesce/rate bound/routes, đã đổi fixture receipt |
| `backend/tests/test_guidance_boundaries.py` | Quyền truy cập, bằng chứng, giới hạn request và ranh giới hướng nghiệp |
| `backend/tests/test_recommender_profile_context.py` | Hồ sơ đã đăng nhập thắng payload, profile thiếu không lấy payload bù, khách giữ context |
| `frontend/e2e/chat-session.spec.ts` | Một probe/open, quá 6 phút vẫn chat, thay hồ sơ không probe, lỗi chỉ retry thủ công |
| `frontend/e2e/profile-recommendation.spec.ts` | Lớp 10/Nam, Lớp 12/Nữ, thiếu profile, stale storage không ghi đè, không ghi profile từ Dashboard |
| `docker-compose.yml`, `frontend/Dockerfile`, `frontend/nginx.conf` | Build/runtime; compose được chạy từ `_1`; image không tự nhận sửa source |

## 4. Những cách đã gây lỗi và lý do

1. **Chỉ kiểm tra API key hoặc probe “OK”.** Probe thành công không chứng minh đường chat thật gọi LLM. Đã tái hiện frontend cũ thiếu receipt → HTTP 200 nhưng `verified_guidance`, không phải AI. Cần kiểm tra payload, bundle đang phục vụ và response metadata.
2. **Chỉ sửa source mà không build lại frontend Docker.** Nginx tiếp tục phục vụ bundle cũ. Phải build/recreate đúng workspace runtime, kiểm tra asset đang được index tham chiếu.
3. **Receipt lưu memory + TTL 300 giây.** Mất hiệu lực sau 5 phút/worker reset; người dùng phải kiểm tra lại không cần thiết. Đã thay bằng receipt HMAC gắn revision; xác minh cục bộ không tốn provider token.
4. **Effect kiểm tra kết nối phụ thuộc toàn bộ hồ sơ và StrictMode.** Có thể tạo hai probe khi mở hoặc lặp khi profile/path đổi. Đã tách effect phụ thuộc `open`, trì hoãn task 0 ms có cleanup; bỏ auto retry khi send trả 409.
5. **`render_chat()` đã redirect nhưng nhánh generation vẫn chạy.** Chặn ở UI/render không đủ. Đã có preflight local và điều kiện chặn `REDIRECT` trước `adapter.chat()`.
6. **Whitelist chỉ gồm từ nghề nghiệp hoặc yêu cầu phải có chữ “học”.** Chặn nhầm bốn ví dụ trong ảnh, cả `1+1=` từng bị test yêu cầu từ chối. Hợp đồng hiện tại cho phép học tập thuần túy; không khôi phục yêu cầu cũ đó.
7. **Ngoại lệ “bài tập” bỏ qua toàn bộ blacklist.** Có thể cho qua “bài tập: nấu mì/đoán số xổ số/uống thuốc”. Đã giới hạn ngoại lệ theo đúng chủ đề: phân tích văn học, xác suất, giải thích khoa học; request hành động ngoài lề vẫn bị lọc.
8. **Bỏ dấu rồi dùng từ đơn làm quyết định.** `nghề/nghe`, `toán/toàn`, `lương/lượng` gây nhầm. Đã giữ kiểm tra dấu gốc ở điểm cần thiết và bổ sung regression về năng lượng/lượng giác.
9. **Dùng career grounding cho câu gia sư.** Đưa mẫu “chọn ngành”, Holland/readiness vào system prompt làm lệch câu trả lời. Câu thuần học tập nay tách prompt, không nạp hồ sơ; mixed career vẫn grounding.
10. **Selector demographics ở Dashboard + defaults trong localStorage.** Có thể hiển thị/sửa sai hồ sơ, nuốt lỗi lưu profile. Đã bỏ selector/state/fallback; server cũng không nhận context ghi đè từ client đã đăng nhập.

## 5. Bằng chứng kiểm thử và cách chạy lại

Các số bên dưới là kết quả đã chạy trong phiên sửa code, KHÔNG phải vừa chạy lại khi viết bàn giao:

- Runtime `_1`: **116 passed** cho học tập, scope gate, guidance boundaries, counselor connection và session receipt sau sửa học tập cuối.
- Main: **104 passed** cho cùng nhóm trừ `test_counselor_connection.py` chỉ có tại `_1`.
- Context đề xuất theo hồ sơ: **29 passed** ở mỗi workspace cho profile context, guest boundary, horizon/gender và snapshot coherence.
- Playwright trên Docker frontend sau thay banner: **5 passed** cho chat session và profile recommendation; HTTP bị mock, không dùng dữ liệu người dùng thật hoặc LLM.
- `npm run typecheck` pass hai workspace; Docker frontend build pass khi cập nhật banner; lần sửa học tập cuối chỉ build/recreate backend.
- Các test đỏ trước sửa đã tái hiện: missing receipt schema; StrictMode 2 probe; stale demographics storage; 4 câu học tập bị chặn. Ảnh QA desktop/mobile banner từng được lưu ở Temp, không phải artifact lâu dài.

Backend runtime, dùng DB test tổng hợp do `backend/tests/conftest.py` thiết lập:

```powershell
cd "E:\CMU-SoftWareEngineering\CAPSTONE PROJECT\capstone 1\AI_CAREERGUIDE_1"
$env:ENVIRONMENT = "test"
py -3 -m pytest backend/tests/test_academic_chat_scope.py backend/tests/test_chat_scope_gate.py backend/tests/test_guidance_boundaries.py backend/tests/test_counselor_connection.py backend/tests/test_connection_session_receipt.py -q
py -3 -m pytest backend/tests/test_recommender_profile_context.py backend/tests/test_recommender_guest_boundary.py backend/tests/test_horizon_gender_engine.py backend/tests/test_assessment_snapshot_coherence.py -q
```

Frontend khi có máy chủ cục bộ đang chạy:

```powershell
cd "E:\CMU-SoftWareEngineering\CAPSTONE PROJECT\capstone 1\AI_CAREERGUIDE_1\frontend"
npm run typecheck
$env:E2E_BASE_URL = "http://127.0.0.1:5173"
npx playwright test e2e/chat-session.spec.ts e2e/profile-recommendation.spec.ts
```

Main từng thiếu package Playwright đã cài trong `node_modules`; test source main đã được chạy bằng runner ở `_1`, không cài thêm dependency trong phiên. Không lấy một lần pass cũ làm kết luận cho thay đổi mới.

Khi cần chạy lại Docker, bật Docker Desktop/Linux engine trước; kiểm tra `docker info`. Các lệnh build đã dùng, chỉ chạy khi cần vận hành hoặc áp dụng sửa mới:

```powershell
cd "E:\CMU-SoftWareEngineering\CAPSTONE PROJECT\capstone 1\AI_CAREERGUIDE_1"
docker compose build backend frontend
docker compose up -d --no-deps --wait backend frontend
docker ps
```

Nếu chỉ thay backend: `docker compose build backend` rồi `docker compose up -d --no-deps --wait backend`. Nginx có thể cần reload/recreate nếu proxy giữ IP backend cũ; kiểm tra qua cổng frontend trước khi kết luận.

Các cổng trước đó: frontend `5173` và `3000`, backend `8000`, PostgreSQL loopback `55432`. Tên container: `careerguide-v9-frontend-1`, `careerguide-v9-backend-1`, `careerguide-v9-db-1`. Không xóa volume DB để sửa lỗi runtime. Không ghi credential hoặc mật khẩu vào báo cáo.

## 6. Hạn chế còn lại và hướng cải thiện đang cân nhắc

Bộ lọc hiện tại vẫn là regex/khái niệm/ngữ cảnh; chưa có bộ phân loại ngữ nghĩa cục bộ. Có thể tiếp tục chặn nhầm cách diễn đạt mới hoặc cho nhầm câu ngoài phạm vi. Các hàm `classify_chat_message()` và `is_academic_question()` vẫn quyết định hai bước, cần chú ý chúng không lệch nhau khi thay đổi.

Phương án đã giải thích cho người dùng:

1. Dùng encoder đa ngôn ngữ đã huấn luyện sẵn chạy cục bộ để so ý nghĩa với tập ví dụ có nhãn; KHÔNG bắt buộc train model mới.
2. Duy trì quy tắc nhỏ cho trường hợp chắc chắn, kèm kết quả chưa chắc để hỏi lại; không gọi thêm LLM chỉ để phân loại nếu muốn giữ mục tiêu tiết kiệm token.
3. Có thể gộp thành một kết quả định tuyến chung: action, topic, score/reason/version; dùng chung cho gate, prompt và history.
4. Thử chế độ quan sát trước, không ảnh hưởng quyết định production; đo chặn nhầm/cho nhầm, tiếng Việt không dấu/viết tắt/câu pha trộn và CPU/RAM/p95.
5. Sau khi có dữ liệu có nhãn mới cân nhắc fine-tune SetFit. Cosine similarity không phải xác suất; ngưỡng phải được chọn bằng đánh giá, không mặc định 0.8.

Ứng viên đã tra tài liệu: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`. Trọng số gốc khoảng 471 MB; file ONNX INT8 khoảng 118 MB. Dung lượng file KHÔNG phải lượng RAM khi inference. Có thể chạy CPU, không bắt buộc GPU.

Nguồn để kiểm tra lại trước khi cài:

- Model: https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
- Các file ONNX: https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2/tree/main/onnx
- Tối ưu CPU/ONNX: https://www.sbert.net/docs/sentence_transformer/usage/efficiency.html
- SetFit: https://huggingface.co/docs/setfit/index

Quan sát máy trong lượt trao đổi trước, chỉ là số đo tại một thời điểm: Intel i7-11370H, 4 nhân/8 luồng; RAM tổng 15.7 GiB; Windows báo còn trống khoảng 0.75 GiB; Docker giới hạn khoảng 7.61 GiB. Lúc đó backend khoảng 89 MiB, frontend 8 MiB, DB 38 MiB; giới hạn Docker không phải RAM thực dùng. Không hứa độ trễ hoặc RAM của classifier khi chưa benchmark.

**Chưa tải mô hình, chưa thêm ONNX Runtime/Sentence Transformers/SetFit, chưa train hoặc fine-tune, chưa sửa dependency cho phương án này.** Không biến câu hỏi tư vấn thành quyền tự tải/cài hoặc thay bộ lọc đang chạy.

## 7. Các bước tiếp theo cho phiên mới

1. Đọc tài liệu này, `git status` ở hai workspace và diff các tệp dự định sửa. Giữ nguyên thay đổi của người dùng; không quay lại cơ chế chặn toán học hoặc selector Dashboard trong tài liệu lịch sử.
2. Nếu người dùng muốn chạy/kiểm tra ứng dụng, xác minh Docker daemon trước. Daemon đang không truy cập được ở thời điểm bàn giao, đây chưa phải bằng chứng API key hay code chat lỗi.
3. Nếu tiếp tục lỗi phân loại: tái hiện nguyên văn câu người dùng trong test với receipt hợp lệ và adapter mock; kiểm tra cả gate và prompt/history. Câu ngoài phạm vi phải được chứng minh không gọi provider, không chỉ nhìn reply.
4. Nếu người dùng chọn phương án mô hình ngữ nghĩa: chốt phạm vi thử nghiệm cục bộ; đánh giá RAM trống, dataset và chất lượng tiếng Việt; thử bản lượng tử hóa với tài nguyên có giới hạn và so sánh baseline trước khi đổi production. Chưa có model đã được lựa chọn/benchmark chính thức.
5. Chỉ chạy test liên quan đến thay đổi mới. Không lặp toàn bộ suite hoặc provider probe khi không có lý do; không phát sinh nhiều lượt test thật làm tốn token.
6. Khi cần deploy sửa mới, build đúng `_1`; kiểm tra cả backend HTTP và frontend proxy/bundle. Không merge/push chỉ vì báo cáo cũ liệt kê là bước tiếp theo.

## 8. Ràng buộc và việc cũ chưa kết luận

- Phản hồi tiếng Việt, ngắn gọn, làm việc đến kết quả; không liên tục hỏi lại quyền cho công việc đã được yêu cầu.
- Không có yêu cầu trong phiên này cho phép tự gửi tin nhắn ra ngoài, commit/push/merge, cài classifier hoặc thay credential.
- Câu hợp lệ không cần phải đề cập nghề nghiệp: kiến thức môn học, giải bài, code và phép tính đều thuộc phạm vi đã được người dùng xác nhận.
- Không dùng LLM sửa điểm/thứ hạng/điều kiện tuyển sinh; phần giải thích demographics phải đúng thuật toán hiện có, không suy diễn giới tính là năng lực.
- Giữ bước phân loại không tốn provider token nếu chưa có chỉ đạo mới. Probe một lần khi mở chat vẫn là một request provider nhỏ, không đồng nghĩa toàn bộ chat không tốn token.
- Profile là nguồn lớp/giới tính của tài khoản; không âm thầm dùng giá trị cũ trong localStorage hoặc mặc định giả lập.
- Không sao chép `.env`, token, API key, mật khẩu quản trị vào handoff. Báo cáo cũ có credential dạng rõ đã được ẩn trong bản lưu.
- Docstring cũ trong `guidance_boundary.py` về việc không có model sinh prose trên path có thể không còn phản ánh nhánh conversational mới. Đọc implementation/test, không suy luận bảo đảm riêng tư chỉ từ docstring. Luồng hướng nghiệp có thể gửi tóm tắt đã xử lý sang provider; luồng gia sư không nạp hồ sơ.
- Bản v5.1 cũ có bản thảo 38 câu hỏi micro-swipe và kế hoạch seed/merge. Phiên này không triển khai hoặc nghiệm thu lại các mục đó. Giữ bản thảo trong archive; không tự seed DB hoặc coi mọi câu hỏi đã được áp dụng chỉ dựa trên báo cáo cũ.

Có thể mở phiên mới với lời nhắn: **“Đọc HANDOFF.md, kiểm tra trạng thái hiện tại và tiếp tục phần tôi yêu cầu.”**
