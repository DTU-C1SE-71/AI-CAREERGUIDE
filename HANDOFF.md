# Handoff — AI CareerGuide

> **Generated:** 2026-11-11T17:52:00+07:00  
> **Project:** `AI_CAREERGUIDE` (`e:\CMU-SoftWareEngineering\CAPSTONE PROJECT\capstone 1\AI_CAREERGUIDE`)  
> **Git Branch & Default Remote:** `develop` @ `5a2dcc5` → `origin` = `https://github.com/DTU-C1SE-71/AI-CAREERGUIDE.git`  
> **Session Summary:** Re-ran the 2026 Macro-Level Trend Hunter against the live Docker stack and persisted **81 trending majors across 23/23 MOET groups** into PostgreSQL (replacing the previous 42-major dataset), verified the full student flow end-to-end with freshly created accounts (assessment → grades → recommendations → dashboard, plus a low-grade TARGET/REACH mix), cleaned the working tree, and re-ran all verification gates green.

---

## 1. Goal

Maintain and continue advancing **AI CareerGuide** — a deterministic + AI-assisted major & career guidance platform for Vietnamese high school students aligned to **MOET Circular 74/2026/TT-BGDĐT (435 Level-IV majors)**. All recommendation scoring locks to the **Pure Guidance Scope** (zero tuition fees or geographic bias) and deterministic 3-pillar weights (`0.45 RIASEC + 0.35 Academic + 0.20 Cognitive`), while Admin governs taxonomy ingestion (Excel/CSV + HITL) and periodic 2026 labor-market Trend Hunter updates stored directly in PostgreSQL.

---

## 2. Current State

### Working & Verified (as of commit `ed39bc3` + admin catalog panel, verification run 2026-11-11)
- **Automated Test Suites (all green after final edit):**
  - `pytest backend/tests -q` (`ENVIRONMENT=test`): **88 passed** (`16.44s`).
  - `py -3 backend/scripts/test_backend_core.py` (`ENVIRONMENT=test`): **10/10 PASSED**.
  - `npm --prefix frontend run build` (`tsc -b && vite build`): **Built cleanly** (`1.64s`) into `frontend/dist/` (only the pre-existing >500 kB chunk-size warning).
- **Docker Compose Local Stack (running & healthy):**
  - `ai_careerguide_db`: `pgvector/pgvector:pg16` (`0.0.0.0:5432`)
  - `ai_careerguide_backend`: FastAPI + Uvicorn `--reload` mounting `./backend:/app` (`0.0.0.0:8000`)
  - `ai_careerguide_frontend`: Nginx serving `./frontend/dist` (`0.0.0.0:3000`, `0.0.0.0:5173`)
- **Database State (`GET http://localhost:8000/api/health/db` & `/api/v1/taxonomy/majors?limit=1000`):**
  - PostgreSQL `majors` table holds **exactly 435 active TT74 majors** (`WHERE is_active = true`; 8 stale TT09 codes are soft-deactivated with `is_active = false`).
- **Git Remotes & Branches:**
  - Default `origin`: `https://github.com/DTU-C1SE-71/AI-CAREERGUIDE.git` (`main` = `526d119`; `develop` = latest handoff/feature commit).
  - Secondary remote `ntanduy`: `https://github.com/ntanduy25/ai-careerguide_2.git` (legacy remote renamed away from `origin`).
- **Trend Hunter Agent (2026 Macro-Level + >= 3/Group + Save-to-DB Flow):**
  - `POST /api/v1/taxonomy/trend-agent/run` (`ADMIN` JWT required): default `auto_save=False`, returns `status="draft_ready"`, `pending_save=True`, **66–86 trending majors** across **23/23 MOET TT74 categories** (see small-category note below).
  - `POST /api/v1/taxonomy/trend-agent/save` (`ADMIN` JWT required): commits reviewed `_trend` JSONB + `industry_outlook` prefix to PostgreSQL `majors`, syncs registry & HITL `StagingRecord`, returns `saved_to_db=True`.
  - Recommender (`backend/app/services/recommender/service.py`) NEVER executes web search; it reads saved `_trend` markers strictly from DB/registry.
- **Latest persisted 2026 trend run (live DB, verified via SQL + `/trend-agent/status`):**
  - `focus_query`: `dự báo nhu cầu nhân lực thị trường lao động Việt Nam 2026 ngành mũi nhọn AI bán dẫn y tế kinh tế xanh`
  - `total_trending_marked = 81`, `categories_covered = 23/23`, `articles_scanned = 65`, `llm_refined = false`
  - `tier_counts = {TIER_1: 20, TIER_2: 45, TIER_3: 16}`; `THÚ Y = 1`, `DỊCH VỤ XÃ HỘI = 2`; zero `TIER_1` in `THÚ Y` / `NÔNG, LÂM NGHIỆP VÀ THỦY SẢN`; no duplicate codes
  - `saved_at = 2026-11-11T10:35:17Z`; SQL cross-check → `active = 435`, `trend_marked = 81`
- **Student flow E2E (fresh accounts, live API):**
  - Standard profile: register/login → 30 RIASEC + 8 cognitive → submit assessment → 10-subject grades → `POST /recommender/recommend` (0.35 s) → dashboard overview. **13/13 checks passed**: weights locked `0.45/0.35/0.20`, 435 majors evaluated, trend markers byte-identical to DB, no web search triggered (registry mtime unchanged).
  - Low-grade profile (`raw_sum = 15.2`): **88 TARGET + 347 REACH** across the catalog; with `top_k=120` the response is exactly 88 TARGET followed by 32 REACH. **11/11 checks passed**.
- **Admin catalog viewer (`MajorsCatalogPanel.tsx`, new):**
  - Rendered in `AdminHITLDashboard.tsx` above *Kiểm duyệt HITL*, collapsed by default, with `refreshKey` bumped after a successful `confirmImportToDb`.
  - Reads the existing public `GET /api/v1/taxonomy/majors?limit=1000` (active majors only) and filters/paginates client-side: search by code/name/category/degree, category dropdown, trend filter (`Tất cả` / `Có xu hướng` / `Không xu hướng`), 50 rows per page, expandable detail row (description, career list, outlook, trend reason + sources), tier distribution footer.
  - Live API contract verified: **435** active majors, **24** distinct `category` values, **81** trending (`TIER_1: 20 / TIER_2: 45 / TIER_3: 16`), and all 435 rows carry `blocks`, `careers`, `description`, `outlook`.

### Recommender Ordering Semantics (verified — do not "fix" these in tests)
- `service.py:492-502` sorts by `(is_TARGET, is_substituted, score + trend_boost, trend_priority, score, trend?, academic, riasec)` descending. Consequences that look like bugs but are intentional:
  1. **Substituted majors are pinned to the top.** Up to 6 blocked REACH majors with `score_riasec >= 0.65` promote a feasible sibling labelled `"Thay thế vừa sức cho …"`; those siblings legitimately outrank higher-scoring majors, because `is_substituted` is the second sort key.
  2. **REACH disappears on small `top_k`.** `final_pool = eligible_targets if len(eligible_targets) >= top_k else scored_items` (`service.py:491`), so a 40-item request returns TARGET only whenever the catalog has ≥40 feasible majors. To exercise REACH, request `top_k` above the eligible count (88 in the low-grade fixture).
  3. Assertions must therefore compare `score + rank_boost` **only within non-substituted items of the same tier**, with a `1e-6` tolerance for ties. Comparing raw `overall_score` across the whole list produces false inversions (e.g. ranks 4–6 tied at `0.7459` before rank 7 at `0.8167`).

### Operational Notes (current, after 2026-11-11 local run)
- **Working tree:** only the admin catalog panel feature touches source files (`MajorsCatalogPanel.tsx` new, `AdminHITLDashboard.tsx` wiring). `backend/app/db/seeds/moet_taxonomy_active.json` was discarded back to its committed state after the DB save (the runtime `_trend` payload lives in PostgreSQL + the gitignored `trending_majors_registry.json`), and the temporary `trending_majors_registry.test.json` artifact was deleted.
- **Local test accounts** created during E2E remain in the dev database only (`student.e2e.*`, `student.reach.*`, password `StudentTest@2026`); they are not part of the release artifact.
- **Tavily is unconfigured** in the current container (`TAVILY_API_KEY=your_tavily_api_key_here`), so the trend agent falls back to RSS/Bing and caps at 65 articles. The 81-major result above was produced in that mode; setting a real key may widen coverage.

---

## 3. Files in Play

| File | Role / Key Symbols |
|------|-------------------|
| `backend/app/main.py` | FastAPI entrypoint; `/health/db` counts `SELECT COUNT(*) FROM majors WHERE is_active = true;` |
| `backend/app/core/config.py` | Environment & LLM settings (`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `LLM_MODEL`, `TAVILY_API_KEY`) |
| `backend/app/core/llm_client.py` | Dynamic provider `/models` max output token & context window resolution (`resolve_model_token_limits`) |
| `backend/app/core/dependencies.py` | RBAC guards including `require_admin_actor` (enforces `role == "ADMIN"` HS256 JWT) |
| `backend/app/schemas/taxonomy.py` | `TrendAgentRunRequest` (`auto_save=False`, `max_length=400`, 2026 default query), `TrendDraftMajorItem`, `TrendAgentSaveRequest`, `TrendTierUpdateRequest` |
| `backend/app/services/taxonomy/trend_agent.py` | 2026 Trend Hunter Agent: `TREND_TOPIC_CLUSTERS`, `CATEGORY_TREND_QUOTA`, `CATEGORY_BASELINE_REPRESENTATIVES`, `search_trending_majors_online` (6 RSS + 2 Bing + 2 Tavily, cap 65 articles), `_extract_candidates_from_articles`, `_refine_tiers_with_llm` (Lựa chọn 3 2026 System Prompt), `_build_classified_trend_map` (with `cat_max_tier` clamp), `run_trend_discovery_agent`, `save_trending_majors_to_db`, `get_trending_status_async` |
| `backend/app/services/taxonomy/service.py` | `bulk_sync_majors(db, majors_data, deactivate_missing=False)` batched scalar SQL sync + `_trend` preservation; `list_majors`, `load_seed_majors` |
| `backend/app/services/taxonomy/router.py` | `/taxonomy/majors`, `/taxonomy/sync-tt09`, `/taxonomy/import-excel` (`replace_catalog` + strict HTTP 500 error propagation), `/taxonomy/publish-majors`, `/taxonomy/trend-agent/{status,run,save,majors/{code},clear}` |
| `backend/app/services/taxonomy/tt74_reference.py` | Excel/CSV parser & 3-tier CIP + Holland RIASEC enrichment (`parse_excel_or_csv_sheets`, `auto_enrich_major_record`) |
| `backend/app/services/recommender/engine.py` | Deterministic 3-pillar engine (`0.45 / 0.35 / 0.20`), physics spelling normalization, failing grade & prerequisite subject cutoffs, zero cross-block substitution |
| `backend/app/services/recommender/aspiration_agent.py` | Post-quiz Career Aspiration alignment agent (`analyze_career_aspiration`) |
| `backend/app/services/recommender/service.py` | `calculate_3pillar_recommendations`: reads saved DB `_trend` priority boosts inside same feasibility tier (`TARGET` strictly before `REACH`, baseline `overall_score >= 0.45`) |
| `backend/tests/test_scoring_and_gap_engine.py` | Main test suite covering scoring constraints, aspiration agent, `TestTrendHunterAgent` (23-category & `>= 3/group` assertions), and `TestExcelBulkImportPersistence` |
| `frontend/src/components/admin/TrendAgentPanel.tsx` | Admin Trend Hunter UI: full-width 2026 search bar, 4 `TREND_QUERY_PRESETS`, Draft preview banner, local draft tier adjustment, **Lưu vào CSDL** (`handleSaveToDb`) & **Hủy nháp** (`handleDiscardDraft`), `[Nhóm ngành] / [Ngành đại diện] / [Cấp độ vĩ mô]` table |
| `frontend/src/components/admin/MajorsCatalogPanel.tsx` | Admin read-only catalog viewer: loads `GET /api/v1/taxonomy/majors?limit=1000`, client-side search/category/trend filters, 50-row pagination, expandable detail row (`description`, `careers`, `outlook`, `trend_reason` + sources), tier distribution summary; collapsed by default, `refreshKey` reload after Excel import |
| `frontend/src/pages/AdminHITLDashboard.tsx` | Excel/CSV import + HITL governance UI (`confirmImportToDb` validates `persisted_to_db`, reports `deactivated`, refreshes `/health/db`, and bumps `catalogRefreshKey`); hosts `TrendAgentPanel` and `MajorsCatalogPanel` |

---

## 4. What Has Been Tried & Root Causes Fixed (Do Not Repeat These Mistakes)

### 1. Silent `MissingGreenlet` Crash on Excel/CSV 435-Major Import (Fixed in `ade55d3`)
- **Symptom:** Uploading a 435-major `.xlsx`/`.csv` showed "435 ngành saved" on UI, then page reload showed `CSDL: 109 ngành`.
- **Root Cause:** `bulk_sync_majors` inserted a new `Major`, called `await db.flush()`, and immediately accessed `major_obj.subject_blocks` / `major_obj.careers` — triggering synchronous SQLAlchemy lazy-loading (`MissingGreenlet` under `asyncpg`). Meanwhile `router.py` caught `except Exception: pass` and still returned HTTP 200, and `AdminHITLDashboard.tsx` ignored `persisted_to_db: false`.
- **Rule Going Forward:** NEVER access unloaded ORM relationships on newly constructed async models in `bulk_sync_majors`; keep using scalar batch `SELECT` queries (`in_`), never swallow DB commit exceptions in routers, and always validate `persisted_to_db` + refresh `/health/db` on the frontend.

### 2. Active Catalog Showing 443 Instead of 435 Majors After Import (Fixed in `5f08223`)
- **Symptom:** CSV had 435 TT74 majors, but DB count jumped to 443 after import.
- **Root Cause:** DB started with 109 TT09 majors, 8 of which (`7210405`, `7320201`, `7480202`, `7510102`, `7510605`, `7580301`, `7720116`, `7810103`) do not exist in TT74 (`435 + 8 = 443`), and `/health/db` did `SELECT COUNT(*) FROM majors;` without `WHERE is_active = true`.
- **Solution:** `bulk_sync_majors(..., deactivate_missing=True)` (auto-enabled when importing `>= 20` majors) soft-deactivates absent legacy codes without breaking FK relations, and `/health/db` counts `WHERE is_active = true`. Do not switch `deactivate_missing=True` to unconditional on `< 20` rows or the 2-row sample template `MOET_Major_Import_Template_Standard.xlsx` would deactivate 433 majors.

### 3. Trend Hunter Category Minimum `>= 3` vs Actual TT74 Catalog Counts (Solved in `e6f2e02`)
- **Critical Fact:** Out of 23 concrete MOET categories (excluding `Khác`), **21 have 5–44 majors**, whereas **`DỊCH VỤ XÃ HỘI` only has 2 majors (`7760101`, `7760104`)** and **`THÚ Y` only has 1 major (`7640101`)** in `moet_taxonomy_tt74.json`.
- **Rule:** Quota logic enforces `min(3, available_majors_in_category)`. Never invent fake major codes to force 3 rows into `DỊCH VỤ XÃ HỘI` or `THÚ Y`. All codes in `TREND_TOPIC_CLUSTERS` and `CATEGORY_BASELINE_REPRESENTATIVES` were audited against TT74 with **0 missing codes** (stale `7480202` and `7510605` were replaced by `7480208` and `7340123`).

### 4. Old Query Overwriting UI 2026 Default Prompt (Fixed in `5a2dcc5`)
- **Symptom:** Updating frontend `useState` default still showed `"ngành nghề xu hướng khát nhân lực Việt Nam"` cut off in the UI.
- **Root Cause:** `loadSavedStatus()` blindly ran `if (res.focus_query) setFocusQuery(res.focus_query)`, overwriting the new default with the old saved query from DB, inside a narrow `w-64` input.
- **Solution:** `TrendAgentPanel.tsx` only hydrates `res.focus_query` if `/202[6-9]/` matches, and puts the full-width input bar + `TREND_QUERY_PRESETS` on its own dedicated row.

### 5. Docker `.env` Not Updating on `docker compose restart`
- **Important:** `docker compose restart` reuses existing container environment variables. Whenever `.env` changes (`OPENAI_API_KEY`, `LLM_MODEL`, `OPENAI_BASE_URL`, `TAVILY_API_KEY`), ALWAYS recreate the container:
  `docker compose up -d --force-recreate backend`

### 6. Git Remote Mix-up
- Ensure future pushes always target **`origin`** (`https://github.com/DTU-C1SE-71/AI-CAREERGUIDE.git`), NOT `ntanduy` (`ntanduy25/ai-careerguide_2.git`).

### 7. PowerShell 5.1 Corrupts Vietnamese Text on Both Sides of the Wire
- **Symptom A (outbound):** `Invoke-RestMethod -Body ($obj | ConvertTo-Json)` sent the 2026 `focus_query` with `?` characters; the draft then contained mojibake category names.
- **Symptom B (inbound):** `Invoke-RestMethod` decodes `application/json` responses **without** `charset` as Latin-1, so `THÚ Y` printed as `THÃ Y` even though the payload was valid UTF-8.
- **Also:** `COPY (…) TO '/tmp/x.json'` escapes quotes in text format and produces invalid JSON; `psql -A -t -o file -c "SELECT json_agg(…)"` writes raw JSON instead.
- **Rules:** drive the FastAPI endpoints with Python `requests` (with `PYTHONIOENCODING=utf-8` and `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` for display), never trust PowerShell console output as evidence of stored text, and validate UTF-8 JSON with Python before drawing conclusions.

---

## 5. Next Steps

1. **Optional UI smoke pass:** hard-refresh (`Ctrl+Shift+R`) the Admin page to confirm (a) the trend panel hydrates the saved 2026 run (81 majors, `Phủ 23/23 nhóm ngành`, `THÚ Y = 1`, `DỊCH VỤ XÃ HỘI = 2`), (b) the new **Danh mục ngành đào tạo trong hệ thống** panel expands to 435 rows / 24 groups / 81 trending with working search, filters, pagination and row detail, and (c) the student dashboard shows `TrendBadge` markers matching the new tiers. Web search must not fire from either page.
2. **Release:** open a PR from `develop` to `main` (`526d119`) on `https://github.com/DTU-C1SE-71/AI-CAREERGUIDE.git` (use the compare URL manually — `gh` CLI is not installed). Backend test suites, core verification script and frontend build are green as of this handoff. GitHub currently reports **2 high Dependabot vulnerabilities** on the default branch; review before/after merge.
3. **Housekeeping (deferred, optional):** delete the dev-only `student.e2e.*` / `student.reach.*` accounts if a pristine seed user count is needed. Note `backend/tests/test_scoring_and_gap_engine.py:1317` was re-checked this session and already has no trailing whitespace — the earlier note was stale.

---

## 6. Verification Commands

```powershell
# Run full backend pytest suite (use ENVIRONMENT=test to isolate from live DB/registry)
$env:ENVIRONMENT="test"; py -3 -m pytest backend/tests -v

# Run core verification script
$env:ENVIRONMENT="test"; py -3 backend/scripts/test_backend_core.py

# Clean temporary test registry artifact if created by ad-hoc runs
Remove-Item -Force -ErrorAction SilentlyContinue "backend/app/db/seeds/trending_majors_registry.test.json"

# Rebuild frontend bundle (served directly by Docker Nginx via ./frontend/dist)
npm --prefix frontend run build

# Recreate backend container if .env changed
docker compose up -d --force-recreate backend

# Check live DB count and saved trend status
Invoke-RestMethod -Uri "http://localhost:8000/api/health/db"
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/taxonomy/trend-agent/status"
```

---

## 7. Key Constraints

- **Pure Guidance Scope:** Never add or mention tuition fees or geographic location filtering in scoring, recommender explanations, trend agent prompts, or UI.
- **Deterministic 3-Pillar Lock:** Keep `0.45 * RIASEC + 0.35 * Academic + 0.20 * Cognitive`; trending priority markers may only break/boost ranking *within* the same feasibility tier (`TARGET` strictly before `REACH`) when baseline `overall_score >= 0.45`.
- **Manual Trend Execution Only:** Web search + LLM trend classification must ONLY execute when an authenticated `ADMIN` triggers `POST /api/v1/taxonomy/trend-agent/run`. Student evaluation only reads persisted DB/registry data.
- **PII & Legal Compliance (Law 91/2025/QH15):** Sanitize any student/prompt PII before calling external LLMs.
- **LLM Output Token Policy:** Dynamic token ceiling via `resolve_model_token_limits()` (do not hardcode small `max_tokens` caps that truncate structured JSON responses).
- **Platform:** Windows PowerShell workspace; note `Select-String` does not support bash glob `**/*.py` directly in PowerShell 5.1 (pipe `Get-ChildItem -Recurse`).
