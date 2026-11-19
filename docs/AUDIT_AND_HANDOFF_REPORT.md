# Kiểm toán và bàn giao V9 — AI CareerGuide

> **Cập nhật sau nghiệm thu V9 — 16/11/2026:** Đã sửa địa chỉ chạy local cũ gây HTTP502 và tách riêng trang nhập danh mục. Mã frontend thay đổi sau Source Manifest V9 bên dưới; kết quả 432 backend/8 E2E bên dưới thuộc digest V9, không gắn lại cho thay đổi mới. Xem phần bổ sung cuối báo cáo để biết kiểm chứng mới.

**Kết quả triển khai:** đã hoàn thành các sửa đổi và Final Gate trong phạm vi kiểm chứng dưới đây. Chưa commit, push hay deploy đợt V9. Live provider chưa kiểm thử vì không có key thật trong worktree; đây là lớp kiểm thử riêng, không thay bằng kết quả stub.

- Repo: `ntanduy25/AI-CAREERGUIDE_1`; branch `codex/publish-current-source`.
- Workspace: `C:/Users/dyysi/.codex/worktrees/careerguide1-main/AI_CAREERGUIDE_1`. Đã dùng repo mới theo chỉ định trong hội thoại; đường dẫn repo cũ trong prompt là đường dẫn template.
- HEAD nền: `8fdd26feff1b8045d69646fd146c5e440bb2d6ad`.
- **Source Manifest Digest:** `46297cffa6bed8268f4973397763d8847a08f8bfb4dadfefb0ad400f9d2e9ed7` — 270 file source/test/migration/lockfile/config không nhạy cảm. HEAD + nội dung + danh sách file xóa; loại trừ báo cáo, log, artifact, secret và thư viện skills không thuộc app.
- Manifest trước/sau Final Gate giống nhau. Không kế thừa kết quả integration cũ.
- Recovery/evidence: `C:/Users/dyysi/AI_CAREERGUIDE_CHECKPOINTS/audit-v9-20261116`. Checkpoint gốc 275 file thuộc phạm vi ảnh hưởng, giữ binary, index, staged/unstaged patch, manifest và `restore.py`. Đầu phiên Git sạch. Không sao chép .env hoặc DB gốc vì không sửa chúng.

## Final Gate chạy mới trên digest bàn giao

| Lệnh | Kết quả | Bằng chứng |
|---|---|---|
| `py -3 -m pytest backend/tests -q --tb=short` | **432 passed**, 1 warning dependency, 156.08s | `final-backend.log` |
| `npm --prefix frontend run build` | PASS; tsc + Vite; Vite 1.25s | `final-build.log` |
| `npm --prefix frontend run typecheck` | PASS | `final-typecheck.log` |
| `npm --prefix frontend run lint` | Exit 0, **20 cảnh báo**, không có error | `final-lint.log` |
| `npm --prefix frontend test` | **8 passed** | `final-frontend-test.log` |
| `npm --prefix frontend run test:e2e` | **8 passed**, 1.3 phút | `final-e2e.log` |
| `git diff --check` | PASS | kiểm tra trực tiếp trước và sau gate |
| `py -3 backend/scripts/source_manifest.py --output <manifest.json>` | Digest không đổi | `final-source-manifest.json`, `final-source-manifest-after.json` |

Lệnh backend có `AUDIT_TEST_DATABASE_URL` trỏ tới PostgreSQL 16.15 + pgvector **container riêng** `careerguide_v9_test` trên loopback; conftest không dùng DATABASE_URL của người dùng. Sáu test trong `test_postgres_acceptance.py` thuộc bộ 432 test, không skip ở Final Gate. Các test còn lại dùng DB SQLite tổng hợp và/hoặc unit fixture; không đánh đồng chúng với chứng nhận PostgreSQL.

PostgreSQL fixture xác nhận `current_database`, server version, schema namespace trước ghi; mỗi test dùng schema riêng và DROP đúng schema đó. E2E dùng backend thật + PostgreSQL thật, không mock API nghiệp vụ ở các case core. Ba case UI có điều khiển lỗi mạng/response muộn được ghi rõ, không dùng thay cho bằng chứng lưu DB.

Cảnh báo còn lại: 20 cảnh báo React (effect/setState, fast refresh, static components...) chưa phải lỗi build; 1 cảnh báo Starlette/AnyIO deprecated alias. Không gọi kết quả này là lint không cảnh báo.

## Truy vết 16 miền

| Miền | Hiện trạng đầu phiên | Task / owner | Bằng chứng nghiệm thu | Kết quả |
|---|---|---|---|---|
| 1 Kiến trúc | FastAPI/SQLAlchemy + React/Vite; aliases /api,/api/v1 | T4 root | map dưới đây; cả canonical/legacy config dùng một service | PASS |
| 2 Backend/services | false success khi lỗi lưu, alias lỗi biến | T1/T4 | test_stream_a_integrity, route_regressions, importer rollback | PASS |
| 3 FE–BE | mock auth/staging, roadmap DTO lệch | T3 frontend + root | core E2E lưu/reload cấu hình, khảo sát, lịch và tiến độ | PASS |
| 4 DB/migration | create_all startup; schema gốc thiếu cột | T4 root | 3 version, fresh/upgrade/idempotent, Unicode row preserved trên PG16 | PASS |
| 5 Auth/RBAC | Admin/email fallback, Google trust client, mutation công khai | T1 security | real login + role DB; 21 hành động × 2 alias × guest/student; revoke/expiry/IDOR | PASS |
| 6 Hướng nghiệp | neutral vẫn 97%; alias cũ tự điền điểm; FE thiếu→0/3 | T3/T5 + runtime | readiness, evidence, legacy19, gap snapshot, PG snapshot/clear | PASS |
| 7 AI/RAG | SDK rời rạc, nguồn/vector/UUID giả khi lỗi | T4 security/root | ingestion20+, loopback embedding/chat, provider errors no fabricated result, deterministic guards | PASS |
| 8 AI runtime | RAM settings, ghép ENV, không CAS/encryption | T2 runtime | runtime49+, PG CAS, real trend consumer A→B, restart subprocess, ciphertext/reveal | PASS |
| 9 FE state | cache chung, late response, fake save | T3 frontend | 2 tab revision, late probe, logout/tab, navigation/back, body timeout handling | PASS |
| 10 Hành trình học sinh | survey/reload/roadmap thiếu test thực | T3/T4 | Browser survey30+8, điểm trống, submit200, reload, personalize4 tuần, progress DB reload | PASS |
| 11 Admin riêng | /admin trong student layout, staging giả | T3 frontend | /admin/governance,catalog,trends,ai-settings; search/paging; actual save/load/error | PASS |
| 12 Responsive/a11y | chưa nghiệm thu | T3 frontend | Chromium1440/375, keyboard focus, labels/status/alert, no overflow, screenshots | PASS trong phạm vi đã đo |
| 13 Hiệu năng | entry JS1,888.70kB | T3/root | entry274.60kB; cùng workload435 ngành đo trước/sau | PASS đo lường, không cam kết SLA |
| 14 Dead code/config | old DTO/config RAM, mock auth/staging | T2/T3/root | bỏ code qua consumer/import/route search; giữ file không rõ mục đích | PASS theo phạm vi đã sửa |
| 15 Integration/E2E | baseline271 chủ yếu unit/mock | T4 + mọi owner | final432 + PG6 + browser8 + unitFE8, tất cả chạy mới | PASS |
| 16 Review độc lập | chưa có | 3 agents + root | review chéo auth/runtime/frontend; redteam malformed publish/missing match/race; counterexamples giữ assertions | PASS |

## Acceptance ledger chi tiết

Cột Task/Write-owner và dependency kế thừa kế hoạch `docs/plans/2026-11-16-v9-audit.md`. Shared auth/DB/config/HTTP/grade normalization làm vô hiệu toàn bộ evidence tích hợp cũ; Final Gate chạy lại từ đầu. Không dùng một bài PASS để đóng cả nhóm.

| ID | Tiêu chí | Test/bằng chứng trên mã cuối | Kết quả |
|---|---|---|---|
| A01 | Admin/email giả không được cấp token | auth_security unknown_admin,google_email_only,forged_signature | PASS |
| A02 | Guest/expired/revoked/inactive/nonexistent/DB down | auth_security malformed,expired,db_role,nonexistent; PG revoke | PASS |
| A03 | Sensitive mutation mọi alias | auth_security all_existing_admin_actions; admin_routes; config main_aliases | PASS |
| A04 | IDOR hồ sơ/snapshot/guidance | auth cross_user; PG student_snapshot_ownership | PASS |
| B01 | Đủ6 chiều, missing/partial/neutral, không điền giả | aspiration_readiness; recommender_evidence neutral highgrades; legacy; FE8 | PASS |
| B02 | Precision, score kind, active, hardgate trước topK | aspiration_readiness+integration; active_catalog; v9_redteam | PASS |
| B03 | Snapshot cùng nguồn/clear/Unicode/lỗi lưu | snapshot_coherence; legacy copy-on-write; gap_snapshot; PG Unicode+empty | PASS |
| D01 | Persist/encryption/thiếu key/rotation/restart | ai_config_runtime persistence,key missing,bootstrap,rotation,restart; PGmigration | PASS |
| D02 | KEEP/REPLACE/CLEAR không ENV/SDK fallback | clear_never_uses_sdk_env; env_profile_is_explicit; replace masks; browserCLEAR | PASS |
| D03 | Host/scheme/port/exact path/model traversal | canonicalization/model param tests; direct_apply path/tenant rejection | PASS |
| D04 | Composite revision/cipher changes/CAS409 | runtime concurrent,external_secret_change; PG concurrent canonical/alias update | PASS |
| D05 | Task snapshot/in-flight/restart/newconsumer | running_request snapshot; subprocess restart; PG real trend consumer A→B oldA | PASS |
| D06 | DNS/privateIP/redirect/time/rate/concurrency/token | runtime SSRF,307 sink,timeoutDNS,totalcall,probe limit,concurrency3; safecaps | PASS |
| D07 | Reveal/Admin/no-store/audit/timeout/navigation | actual API auth+reveal; browser reveal15s/navigation/back/logout/401 | PASS |
| C01 | Admin modules và trạng thái thật | browser core config/catalog/navigation; error boundary; no dummy staging | PASS |
| C02 | Draft/persisted/runtime/stale probe | browser two-tabs,late-probe, persisted history stale; API metadata | PASS |
| C03 | Account change/double-submit/back/unmount | browser cross-tab logout/back, button guards; PG concurrent progress; abort/token comparisons | PASS trong cases đã ghi |
| C04 | Mobile/keyboard/console | browser width375/1440 + focus/overflow; core config console/pageerror empty | PASS trong Chromium |
| Q01 | PG16 fresh/upgrade/idempotent/constraints | test_postgres_acceptance migrations + real FK users/auth/staging | PASS |
| Q02 | Đo performance, không suy đoán | baseline-build/final-build + benchmark_recommendations.py | PASS |
| Q03 | Dọn code có reference evidence | removed old LLM DTO+imports, RAM mutation/probe SDK, fake auth/staging paths; full gate | PASS |
| Q04 | Independent review/counterfactual | security reviewer/runtime reviewer/frontend reviewer; v9_redteam + new targeted tests | PASS |

## Các lỗi chính đã sửa

- **P0:** email chứa “admin” + mật khẩu bất kỳ không còn tạo ADMIN; Google identity không tin email/profile client; bearer role không thay quyền DB; mất DB fail closed.
- **P1:** JWT bắt buộc sub/iat/exp; guard cho taxonomy import/publish/sync và assessment seed trên cả alias; response validation không echo body/password/API key.
- **P1:** config mã hóa riêng JWT, CAS atomic, target binding bao gồm path, không gửi key qua redirect/SSRF hoặc model traversal; CLEAR không hồi sinh ENV; key thiếu không phá ciphertext.
- **P1:** catalog GET không auto-seed; inactive/empty không hồi sinh; publish/import thiếu mã/tên bị chặn trước purge; bảo toàn inactive. DB là nguồn xu hướng chính thức, không ghi lại seed/registry trước commit.
- **P1:** bỏ fake OAuth/local JWT/plaintext password storage, fake staging và optimistic success khi lỗi. Wizard không điền câu thiếu=3 hay học bạ thiếu=0; lịch sử không bịa điểm/ngành.
- **P1:** neutral/unverified interest không công bố match cao; legacy assessment tạo snapshot mới, giữ thiếu dữ liệu, chuẩn hóa alias và precision; skill mastery chỉ từ diagnostic. Gap engine đọc cùng snapshot, clear không lấy điểm cũ.
- **P1:** StreamA lưu DB lỗi trả lỗi/rollback thay vì UUID giả; StreamB thiếu provider/nguồn không tự bịa học liệu/vector. HITL quyền+row lock+CAS, quyết định và xuất bản atomic.
- **P2:** sửa roadmap personalize DTO, lịch4 tuần, tiến độ reloadDB/clear; serialize double-submit bằng User row lock; sửa GET recommender biến chưa định nghĩa và không che503 thành hồ sơ trống.

## Bản đồ hệ thống và AI consumers

| FE/flow | API (cả /api và /api/v1) | Service / bảng | Quyền |
|---|---|---|---|
| Login/AuthContext | identity/login,google-login,google/callback,me | identity; users,user_consents | JWT + DB active role; signedGoogleclaims |
| AssessmentWizard | assessments/submit,assessment/* | modular/legacy; submissions,responses,student_assessments,student_grades,diagnostics | guest tính không lưu; user chỉ chính mình |
| Dashboard/MajorDetail | recommender/evaluate,recommend; major-insights/* | canonical evidence/catalog; assessment,majors,insights | owned snapshot; regenerate/delete Admin |
| AIChatAdvisor | rag-governance/chat,explain-recommendation | guidance_boundary facts/render | guest/owned evidence; **tất định** |
| Roadmap | roadmap/*; guidance-personalize | gap/roadmap + canonical profile | progress/personalize chính user |
| Admin catalog/trends | taxonomy mutations/trend-agent | taxonomy/trend; majors | Admin DB |
| Admin HITL | rag-governance/staging,ingest,discover | streamA/B/HITL; staging,roadmap,knowledge_embeddings | Admin DB; lock/CAS khi duyệt |
| Admin AI | admin/ai-config + legacy llm-status/test/update | ai_config; ai_runtime_config,ai_config_audit | Admin DB, no-store |

Provider consumers thật: StreamA vision, StreamB extraction, HITL embedding, semantic-search embedding, TrendAgent refinement, model capability lookup và probe. Tất cả LLM/embedding qua immutable ConfigSnapshot + HTTP adapter; không thêm LLM vào chat/explain/personalize/aspiration tất định. Tavily/Jina/RSS là consumer tìm nguồn cố định riêng; không truyền dữ liệu hồ sơ học sinh. Nội dung provider/RAG là dữ liệu, không lệnh điều khiển; schema/ID/source được xác minh trước publish.

## Migration và schema hiện hữu

Đã đọc schema DB hiện hữu bằng `BEGIN READ ONLY`; PostgreSQL16.15, 24 bảng, thiếu users.gender/grade_level/school_class/school_name và 2 bảng AI mới. Không sửa DB đó. Migration được nghiệm thu trên DB riêng:

- `20261116_001_base`: tạo bảng còn thiếu cho DB mới/legacy.
- `20261116_002_profile_columns`: bổ sung cột hồ sơ thiếu.
- `20261116_003_ai_runtime`: bảng config/audit.

Các version lưu trong schema_migrations; PG advisory transaction lock; không DDL khi HTTP startup. Upgrade test cố ý bỏ cột và bảng trong schema tổng hợp, chạy lại migration hai lần, giữ user tiếng Việt. Sau test không còn schema `audit_v9_%`.

Runtime revision cuối E2E: `7413cae807232275f952a8fa8eb7bb7037f79bd5b79bddf0ebf07f7ca805c05a`; runtime=persisted revision, sync_state=current. Đây là DB tổng hợp đã dọn, không phải config production.

## Vận hành Admin và khóa

1. Cài requirements backend và `npm --prefix frontend ci`. Cấu hình DB/SECRET_KEY riêng qua ENV/secret store. Production từ chối signing key mặc định/yếu.
2. Backup DB bằng pg_dump và xác minh restore trước migration dữ liệu thật. Chạy `py -3 backend/scripts/init_db.py`. Chỉ khi khởi tạo danh mục/câu hỏi, chạy `py -3 backend/scripts/seed_catalog.py`; không tự nạp lại sau thao tác Admin.
3. Tạo Admin bằng `py -3 backend/scripts/create_admin.py --email <email> --name <ten>`; mật khẩu nhập ẩn, không có mặc định. CLI từ chối tài khoản đã tồn tại. Docker startup không tạo demo Admin. Scripts demo chỉ được chạy tường minh trong test.
4. `/admin/governance`: rà soát staging; `/admin/catalog`: tìm/lọc/phân trang/nhập; `/admin/trends`: chạy bản nháp rồi lưu; `/admin/ai-settings`: Draft/Active/Apply/Cancel/Reveal.
5. ENV profile phải nguyên khối `LLM_PROTOCOL`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_AUTH_MODE`, `LLM_API_KEY`. Không trộn biến OPENAI/XAI cũ. Protocol hỗ trợ: `openai_compatible`; auth BEARER hoặc NONE. Model embedding được chụp cùng task từ EMBEDDING_MODEL và tham gia revision.
6. Tạo Fernet key qua `cryptography.fernet.Fernet.generate_key()` trong terminal/secret store riêng; cấp `AI_CONFIG_ENCRYPTION_KEY` và ID. Không dùng JWT key. Khi thiếu/sai khóa, status báo LOCKED và giữ ciphertext; không tự sinh khóa thay.
7. KEEP yêu cầu revision/binding đúng; đổi host/port/path tenant cần REPLACE. Ô key mới luôn trống. CLEAR không khôi phục ENV. Chuyển ENV là chuyển cả profile có binding đã xác minh.409 yêu cầu tải lại; probe cũ chỉ là lịch sử.
8. Reveal POST Admin/no-store, audit action/revision không key; tự ẩn15s và clear khi rời trang/back/logout/401. Không ghi key vào storage/URL/log/artifact. Tests dùng secret tổng hợp.
9. Apply hiệu lực ở tác vụ mới vì resolver đọc DB mỗi task/worker; task đang chạy giữ snapshot tới xong hoặc timeout. Không đóng client đang dùng; không thêm message bus. Restart giữ config DB; ENV thay đổi cần restart.
10. Mặc định HTTPS/IP công khai, chặn query/userinfo/fragment/path traversal và redirect. Dev/test dùng allowlist **base URL chính xác**; production không chấp nhận private allowlist. Probe6/phút/actor, HTTP3 slot mỗi event loop, probe8s/16token, inference≤4096token/≤30s; không tự retry.
11. Xoay key: dừng worker, backup DB có khả năng restore, giữ key cũ. Cấp key cũ qua AI_CONFIG_ENCRYPTION_KEY/ID, key mới qua NEW_AI_CONFIG_ENCRYPTION_KEY/ID; chạy `py -3 backend/scripts/rotate_ai_config_key.py`. Giao dịch mã hóa lại giữ credential/binding, tăng revision, audit IDs. Cập nhật ENV mới rồi restart. Nếu commit thành công nhưng ENV chưa đổi, worker LOCKED cho tới cấu hình đúng. Thiếu cả key cũ và backup không thể hứa khôi phục secret.
12. Phục hồi code từng phần: `py -3 <checkpoint>/restore.py <relative-file> ...`; giữ index/staging hiện tại. Checkpoint còn giữ index gốc và patch. File mới trong phiên chỉ xóa sau đối chiếu diff. Migration cộng thêm: có thể giữ bảng mới khi lùi code; muốn lùi DB phải restore backup engine, không tùy tiện DROP dữ liệu.

## Hiệu năng và dọn dẹp

Build entry JS từ1,888.70kB (gzip566.46kB) xuống274.60kB (gzip85.09kB); route/features tải lazy, không chunk trên500kB. Đây là số byte build, không phải phép đo LCP hoặc mạng thực.

Benchmark cùng435 ngành, profile và5 warm runs: baseline median192.55ms, bản cuối đo trước freeze174.40ms. Máy Windows dùng chung có nhiễu; không tuyên bố mức tăng tốc đảm bảo. Không đổi thuật toán để chạy nhanh theo số dòng.

Đã dừng đúng PID backend14440/frontend19964/stub6848; xóa container test có label riêng và volume/tmpfs; xóa258 SQLite DB tổng hợp, test registry, ảnh tạm (ảnh bằng chứng giữ trong checkpoint). Xóa metadata test cuối. Một số **thư mục rỗng** trong `%TEMP%` còn lại: bộ duyệt tự động chặn lệnh xóa thư mục với lý do “blocked by policy”; không còn DB/secret hay tiến trình test trong đó. Không can thiệp container/dịch vụ khác. Checkpoint phục hồi và log/bằng chứng được giữ để bàn giao.

## Giới hạn và nhánh có điều kiện

- Live provider và Google OAuth thật: SKIPPED do không có credential live được cấu hình trong worktree. Stub/Google signed synthetic test không chứng nhận mọi provider/model hoặc console OAuth production.
- Anti-lockout quản lý tài khoản: NOT_APPLICABLE vì không có endpoint/menu thay role/disable/deleteAdmin; không thêm menu rỗng. Auth kiểm quyền hiện tại trong DB, revoke bên ngoài bị chặn ở request mới.
- Streaming/queue/distributed cache: NOT_APPLICABLE vì repo không triển khai. Reveal/probe/inference dùng HTTP không streaming.
- Browser nghiệm thu Chromium1440/375 và keyboard; chưa chứng nhận WCAG toàn diện hay Firefox/Safari.
- Progress roadmap serialize qua User row lock cho mọi writer hiện có; chưa thêm unique(user,major) để cưỡng chế direct SQL hoặc dữ liệu trùng từ trước. Không chạy sửa dữ liệu người dùng.
- repo-scan chỉ là installer nên dùng inventory trực tiếp. ui-ux-pro-max script có SyntaxError với Python3.11, dùng checklist đã đọc. Impeccable detector trả `[]`. Modern Web Guidance `forms`: explicit label/fieldset, aria-live và chống double-submit; không cài hook/skill mới.

## File thêm/sửa/xóa

`M` là sửa, `??` là file mới chưa stage. Không có commit đợt V9. Chi tiết diff giữ tại workspace; danh sách sau gồm cả tài liệu không nằm trong digest.

| Trạng thái | File |
|---|---|
| `M` | `.env.example` |
| `M` | `backend/app/core/config.py` |
| `M` | `backend/app/core/dependencies.py` |
| `M` | `backend/app/core/llm_client.py` |
| `M` | `backend/app/core/security.py` |
| `M` | `backend/app/main.py` |
| `M` | `backend/app/models/__init__.py` |
| `M` | `backend/app/models/taxonomy.py` |
| `M` | `backend/app/modules/assessment/router.py` |
| `M` | `backend/app/modules/assessment/service.py` |
| `M` | `backend/app/schemas/assessment.py` |
| `M` | `backend/app/schemas/identity.py` |
| `M` | `backend/app/schemas/rag.py` |
| `M` | `backend/app/schemas/recommender.py` |
| `M` | `backend/app/schemas/roadmap.py` |
| `M` | `backend/app/services/assessment/router.py` |
| `M` | `backend/app/services/assessment/service.py` |
| `M` | `backend/app/services/gap_roadmap_engine/router.py` |
| `M` | `backend/app/services/gap_roadmap_engine/service.py` |
| `M` | `backend/app/services/identity/service.py` |
| `M` | `backend/app/services/llamaindex_rag_orchestrator/guidance_rag.py` |
| `M` | `backend/app/services/llamaindex_rag_orchestrator/hitl_governance.py` |
| `M` | `backend/app/services/llamaindex_rag_orchestrator/router.py` |
| `M` | `backend/app/services/llamaindex_rag_orchestrator/stream_a_ingest.py` |
| `M` | `backend/app/services/llamaindex_rag_orchestrator/stream_b_discovery.py` |
| `M` | `backend/app/services/recommender/catalog.py` |
| `M` | `backend/app/services/recommender/engine.py` |
| `M` | `backend/app/services/recommender/router.py` |
| `M` | `backend/app/services/recommender/service.py` |
| `M` | `backend/app/services/taxonomy/router.py` |
| `M` | `backend/app/services/taxonomy/service.py` |
| `M` | `backend/app/services/taxonomy/trend_agent.py` |
| `M` | `backend/app/services/taxonomy/tt74_reference.py` |
| `M` | `backend/requirements.txt` |
| `M` | `backend/scripts/init_db.py` |
| `M` | `backend/scripts/seed_tt09.py` |
| `M` | `backend/scripts/setup_database.py` |
| `M` | `backend/tests/test_active_catalog_contract.py` |
| `M` | `backend/tests/test_assessment_snapshot_coherence.py` |
| `M` | `backend/tests/test_dual_rag_and_ingestion.py` |
| `M` | `backend/tests/test_guidance_boundaries.py` |
| `M` | `backend/tests/test_insight_evidence_boundary.py` |
| `M` | `backend/tests/test_major_insight_agents.py` |
| `M` | `backend/tests/test_recommender_evidence_coherence.py` |
| `M` | `backend/tests/test_scoring_and_gap_engine.py` |
| `M` | `docker-compose.yml` |
| `M` | `frontend/package-lock.json` |
| `M` | `frontend/package.json` |
| `M` | `frontend/src/components/admin/LLMConnectionPanel.tsx` |
| `M` | `frontend/src/components/admin/MajorsCatalogPanel.tsx` |
| `M` | `frontend/src/components/admin/TrendAgentPanel.tsx` |
| `M` | `frontend/src/components/assessment/AcademicInputForm.tsx` |
| `M` | `frontend/src/components/layout/MainLayout.tsx` |
| `M` | `frontend/src/context/AssessmentContext.tsx` |
| `M` | `frontend/src/context/AuthContext.tsx` |
| `M` | `frontend/src/hooks/useRoadmap.ts` |
| `M` | `frontend/src/index.css` |
| `M` | `frontend/src/pages/AIChatAdvisor.tsx` |
| `M` | `frontend/src/pages/AdminHITLDashboard.tsx` |
| `M` | `frontend/src/pages/AssessmentWizard.tsx` |
| `M` | `frontend/src/pages/Dashboard.tsx` |
| `M` | `frontend/src/pages/GoogleCallback.tsx` |
| `M` | `frontend/src/pages/Login.tsx` |
| `M` | `frontend/src/pages/MajorDetail.tsx` |
| `M` | `frontend/src/pages/RoadmapView.tsx` |
| `M` | `frontend/src/routes/AdminRoute.tsx` |
| `M` | `frontend/src/routes/AppRoutes.tsx` |
| `M` | `frontend/src/routes/PrivateRoute.tsx` |
| `M` | `frontend/src/services/api.ts` |
| `M` | `frontend/src/types/assessment.ts` |
| `M` | `frontend/src/types/roadmap.ts` |
| `M` | `frontend/src/utils/assessmentPayload.ts` |
| `M` | `frontend/vite.config.ts` |
| `M` | `pytest.ini` |
| `??` | `backend/app/core/ai_runtime.py` |
| `??` | `backend/app/db/migrations.py` |
| `??` | `backend/app/models/ai_config.py` |
| `??` | `backend/app/schemas/ai_config.py` |
| `??` | `backend/app/services/ai_config/__init__.py` |
| `??` | `backend/app/services/ai_config/adapter.py` |
| `??` | `backend/app/services/ai_config/router.py` |
| `??` | `backend/app/services/ai_config/service.py` |
| `??` | `backend/scripts/audit_fixture.py` |
| `??` | `backend/scripts/audit_http_stub.py` |
| `??` | `backend/scripts/benchmark_recommendations.py` |
| `??` | `backend/scripts/create_admin.py` |
| `??` | `backend/scripts/rotate_ai_config_key.py` |
| `??` | `backend/scripts/seed_catalog.py` |
| `??` | `backend/scripts/source_manifest.py` |
| `??` | `backend/tests/conftest.py` |
| `??` | `backend/tests/test_admin_routes_and_catalog.py` |
| `??` | `backend/tests/test_ai_config_runtime.py` |
| `??` | `backend/tests/test_auth_security.py` |
| `??` | `backend/tests/test_gap_snapshot_coherence.py` |
| `??` | `backend/tests/test_ingestion_evidence.py` |
| `??` | `backend/tests/test_legacy_assessment_evidence.py` |
| `??` | `backend/tests/test_postgres_acceptance.py` |
| `??` | `backend/tests/test_route_regressions.py` |
| `??` | `backend/tests/test_stream_a_integrity.py` |
| `??` | `backend/tests/test_trend_evidence.py` |
| `??` | `backend/tests/test_v9_redteam.py` |
| `??` | `docs/AUDIT_AND_HANDOFF_REPORT.md` |
| `??` | `docs/plans/2026-11-16-v9-audit.md` |
| `??` | `frontend/e2e/admin-and-student.spec.ts` |
| `??` | `frontend/playwright.config.ts` |
| `??` | `frontend/src/components/admin/AdminLayout.tsx` |
| `??` | `frontend/src/routes/LazyPages.tsx` |
| `??` | `frontend/src/types/aiConfig.ts` |
| `??` | `frontend/src/utils/assessmentEvidence.ts` |
| `??` | `frontend/src/utils/roadmapSchedule.ts` |
| `??` | `frontend/tests/assessment-evidence.test.ts` |
| `??` | `frontend/tests/roadmap-schedule.test.ts` |

## Tự đánh giá bàn giao

Accuracy4/5: fresh432+8+8 và digest khớp; live compatibility chưa đo. Completeness4/5: đủ16 miền/các case bắt buộc áp dụng, còn giới hạn browser và warning nêu rõ. Clarity4/5: có ledger và lệnh tái hiện, báo cáo dài do yêu cầu truy vết. Actionability4/5: có migration/bootstrap/rotation/restore, cần operator cấp key thực. Conciseness4/5: phần trả lời ngắn, chi tiết tách vào báo cáo. Điểm4.0 chỉ là tự đánh giá, không thay review/test.


## Bổ sung: lỗi 502 ở cổng cũ và chia nhỏ Admin (16/11/2026)

**Nguyên nhân đã tái hiện:** `127.0.0.1:5173`/`:3000` chạy container frontend cũ, bind source từ E:/.../AI_CAREERGUIDE, vẫn proxy tới backend cũ đang restart do lỗi schema. API danh mục trả502. Bản worktree V9 trên5174/backend8000 dùng DBcareerguide1_dev riêng55432 trả200/435ngành. Không phải danh mục V9 bị mất dữ liệu.

**Sửa runtime:** giữ nguyên container/source/DB cũ. Dừng đúng `ai_careerguide_frontend`; thêm `careerguide1-dev-gateway` chỉ bindloopback5173/3000, proxy tới frontendV9 5174 cùng HTTP/WebSocket, authheaders giữ nguyên. Cấu hình local ignored `scratch/local-proxy/nginx.conf`; bảnnginx gốc được backup. Không migrate, purge hay reseed DB người dùng trong lần sửa này. Backend cũ còn restart nhưng không nằm trên đường phục vụ bản mới.

**Sửa frontend:**
- `/admin/catalog`: chỉ tra cứu danh mục đã lưu, search/filter/pagination và nút đi tới nhập dữ liệu.
- `/admin/import`: file mẫu, hướng dẫn, tải lên, chọnsheet, xemtrước, lưu và liên kết quay về danh mục.
- `/admin/governance`, `/admin/trends`, `/admin/ai-settings`: chức năng riêng. Sidebar nhóm Dữ liệu/AI, không menu học sinh trong Admin.
- Catalog tải tất cả các trang500rows tới tối đa10000; không cắt thầm1000dòng, không trả dữliệu một phần khi lỗi. Error/loading không báo sai0ngành; retry/abort có kiểm chứng.

**Kiểm chứng mới:** build+TypeScript PASS;12unitfrontend PASS (4cases mới gồm1201dòng, errorpage2,abort,duplicate/sizeguard); gitdiffcheckPASS; trìnhduyệt Chromium qua5173 thật đăngnhậpAdmin→5trang→435ngành→page2/search→template+preview_only khôngghiDB→mobile375nooverflow,0pageerror. Riêng UI controlled502 kiểm headerkhông0+filtersdisabled, reloadthật khôi phục435. Không chạy lại432backend vì không đổi backend; không gọi kiểmchứngmới là fullV9FinalGate. Cả5173/5174/3000 fresh API200435 và guestconfig401. Reviewđộclập xác nhận routing/auth và splitUI.

**Recovery/evidence:** `C:/Users/dyysi/AI_CAREERGUIDE_CHECKPOINTS/admin-routing-20261116-220451`: ảnhdesktopcatalog/import/mobile,manifest,nginxgốc,index/diffs và verification.txt. Stagingngười dùng giữ nguyên. Hoànnguyênruntime khi cần: dừngcareerguide1-dev-gateway rồi khởiđộngai_careerguide_frontend (bảncũ vẫn cần sửabackendtrước khi dùng). Không chạyhaifrontend trùngcổng. Không commit/push.


## Bổ sung: cấu hình Xingchi và phối màu Admin (16/11/2026)

Theo yêu cầu trực tiếp, đã cấu hình profile DATABASE local cho `https://api.xingchiapi.com/v1` bằng credential người dùng cấp. Credential chỉ nằm trong ciphertext Fernet, không ghi source, .env, report, URL, ảnh hoặc log. Xác nhận DB đích `careerguide1_dev` loopback55432, Admin còn active, backup scoped hai bảng AI bằng pg_dump custom format trước thay đổi, kiểm định pg_restore --list. Backup/UIcheckpoint ACL riêng: `C:/Users/dyysi/AI_CAREERGUIDE_CHECKPOINTS/ai-admin-style-20261116-234239`. Git staging giữ nguyên; không commit/push.

Model listing live trả đúng hai ID `gpt-6.1-sol` (6.1 Sol), `gpt-6-astra` (6 Astra). Default runtime chọn Astra theo ảnh người dùng. UI có hai nút chọn nhanh chỉ đổi bản nháp, không tự Apply/probe/đổi binding/key. Model tùy chỉnh vẫn được nhập trực tiếp. Phiên backend mới đọc lại đúng cấu hình đã lưu.

**Giới hạn live đã xác nhận:** cả hai chat probe bị403; body error code `client_not_allowed` cho biết máy chủ chỉ cho coding client và không cho ứng dụng/SDK gọi trực tiếp. Không giả mạo User-Agent/coding-client để vượt hạn chế. Đã thêm phân loại `CLIENT_NOT_ALLOWED` với thông báo cố định, không echo lỗi thô/secret; status keySET không được mô tả là inference thành công. Cần provider cho phép API dành cho ứng dụng hoặc endpoint/key khác để inference hoạt động. Không kiểm chứng embedding/vision của provider này; không thay luồng tư vấn tất định bằng LLM.

Admin được phối navy–cyan/sky với sidebar đậm, nền sáng, thẻ có phân cấp/độ nổi, trạng thái và typography đồng bộ. Bố cục5trang riêng giữ nguyên; CSS chỉ scopedAdmin. Model đang chọn trong draft tách rõ model đang áp dụng. Native controls, focus, label và nút phụ typebutton được giữ; không auto-submit khi đổi model. ModernWebGuidance forms/browser-ui-theming áp dụng cho trường cónhãn, accent-color,focus và nativefile-selector; Impeccable detect trả[] sau các thay đổi.

Kiểm chứng mới: `pytest backend/tests/test_ai_config_runtime.py` **49pass**, gồm regressions403client-not-allowed qua loopback synthetic và secret không echo; frontend build/TypeScript PASS,12unit PASS, diffcheckPASS. Browser thật1440/768/375 không tràn ngang,0pageerror,435ngành; chọnSol→cancel giữAstra/runtime/revision và không thêm POST/PUT, key không nằm DOM/localStorage. Kiểm tra screenshot một lượt, sửa batch CSS specificity ôcóicon + cardmodelmobile, xác nhận lại. Chỉ đọc trạng thái live và probe synthetictext, không Reveal key thật hay chạy testmutations vào credentiallive. Không gắn lại digestV9 cũ cho các sửa đổi mới.
