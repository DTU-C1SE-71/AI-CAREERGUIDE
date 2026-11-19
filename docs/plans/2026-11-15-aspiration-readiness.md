# Aspiration readiness implementation plan

**Goal:** Show all six Holland groups and prevent unsupported academic recommendations in Nguyện vọng.
**Architecture:** Implement arena champion a003 with one resolved profile, deterministic aspiration output and a fail-closed readiness contract. Existing heuristic cutoffs remain catalog context, never silently verified admission evidence. The source catalog currently has no verified comparable reference metadata; such cases remain UNKNOWN with useful next steps.
**Tech Stack:** React/TypeScript, FastAPI/Pydantic, pytest, Playwright.

Winner: `.arena/run-20261115-091223-s264329/r3/r3-m01.a003.solution.md`. Full tournament: 8 competitors, 3 rounds, 43 jobs; winner a003, final weighted score 95 vs 92.5.

## Shared integration contract
- New backend module `app.services.recommender.readiness` exports `build_interest_evidence(answers, legacy_vector=None)`, `validate_readiness_grades(raw)` -> {scores, errors}, `evaluate_current_readiness(*, raw_grades, admitted_blocks, block_source, major_code, major_name, category='', score_context=None, reference=None)` -> dict.
- InterestEvidence status COMPLETE/PARTIAL/MISSING/LEGACY_UNVERIFIED, groups {code,percent:number|null,answered:number|null,total:5}. Order R I A S E C.
- Readiness dict status READY_REFERENCE/NEEDS_IMPROVEMENT/UNKNOWN; reason, message, block, block_score, benchmark_cutoff, min_recommended, missing_subjects, violations, gaps; reference_kind, reference_id, reference_method, score_kind, block_source, policy_version='aspiration-v1'. Values unknown without evidence are null. Optional evaluated_blocks/source info acceptable.
- MajorRecommendationItem adds readiness: dict default UNKNOWN; schema defaults feasibility_tier UNKNOWN, constraint_passed false. Legacy scoring/ranking remains separate from current recommendations.
- Analyzer accepts optional interest_evidence, never infers COMPLETE from a vector, and uses only m.readiness.status READY_REFERENCE for current/substitute/bridge. Defaults fail closed. No LLM call for aspiration verdict.
- Aspiration payload adds match_status EMPTY/MATCHED/UNRECOGNIZED/AMBIGUOUS, interest_evidence, current_options, exploration_options, intent_candidates [{id,label,canonicalDreamJob,evidence}]. alignment_score/brief overall_match/riasec_fit/academic_fit allow null. Additional alignment status NO_CURRENT_OPTIONS, UNRECOGNIZED_ASPIRATION, AMBIGUOUS_ASPIRATION acceptable (frontend string union extensible).
- Brief readiness same dict; relation_reason string; current_options only verified READY_REFERENCE. dream_majors are goals; exploration_options unknown related goals/catalog, never current. Keep old response keys for readers.
- Backend server-owned references loaded only from seed key `readiness_reference` or verified server configuration; absence = UNKNOWN. Client cannot send verification metadata. Input score_context defaults TRANSCRIPT (existing form is school grades).

## Work ownership
1. Readiness agent: new readiness.py, schemas/recommender.py readiness/default fields, tests/test_aspiration_readiness.py. Test grade precision, malformed/boolean/alias conflicts, missing blocks/references/context mismatch, all admitted blocks and interest evidence.
2. Analyzer agent: aspiration_agent.py and tests/test_aspiration_matching.py. Resolve intent independently of strategy, fail-closed lists and deterministic output, preserve goal, scoped aliases/ambiguity. Do not edit service or schema.
3. Frontend agent: CareerAspirationStep, new HollandInterestSummary, AssessmentWizard small edits, types/assessment, AspirationAlignmentCard, Dashboard small edits. Preserve existing user changes. Full six-group display, atomic chips, stale field clear, truthful distinct result sections, no fallback claims, stale-request protection.
4. Root: service.py profile resolution/readiness/whole-catalog integration, endpoint explicit empty handling, integration tests, reconcile agents and run checks.

## Verification
- Baseline: backend 121 passed (2 existing warnings); frontend build passed.
- Meaningful new tests must fail against old behavior, then pass with implementation.
- ENVIRONMENT=test; `py -3.11 -m pytest backend/tests -q`.
- `npm.cmd run build`; changed-file oxlint plus repo lint report if preexisting failures.
- Browser fixture `.arena/browser-before.cjs`; inspect desktop and 390px mobile. Verify six groups, missing/partial scores, draft edit and labels, keyboard controls, stale API/no API states.
- Review source diff, preserve `.arena/preexisting.patch`, do not commit without user request.
