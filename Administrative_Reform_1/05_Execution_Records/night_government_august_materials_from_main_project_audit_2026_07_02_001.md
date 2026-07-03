# Night Government August Materials From Main Project Audit 2026-07-02 001

## 작업 목적

사용자 요청에 따라 SongRyeon 본점의 심야정부 관련 문서와 코드 흔적을 정밀 탐사하고, SongRyeon Core의 8월 심야정부 완성에 필요한 재료를 철학 문서로 정리했다.

## 읽은 본점 근거

- `SongRyeon_Project/AGENTS.md`
- `SongRyeon_Project/ANIMA_DOCS_INDEX.md`
- `SongRyeon_Project/Administrative_Reform_1/00_Philosophy/ANIMA_SLEEP_STACK_V1.md`
- `SongRyeon_Project/Administrative_Reform_1/00_Philosophy/ANIMA_SLEEP_STACK_V2.md`
- `SongRyeon_Project/Administrative_Reform_1/00_Philosophy/ANIMA_V4_MIDNIGHT_GOVERNMENT_PROPOSAL.md`
- `SongRyeon_Project/Administrative_Reform_1/03_Maps/01_Function_Maps/ANIMA_MIDNIGHT_DMN_REORG10A_INVENTORY_2026_05_26.md`
- `SongRyeon_Project/Administrative_Reform_2/02_Department_Studies/D2_DAY_NIGHT_STATE_SEPARATION_AND_ZERO_SUPPLY_AUDIT_2026_06_19.md`
- `SongRyeon_Project/Administrative_Reform_2/02_Department_Studies/D3_NIGHT_COREEGO_SOURCE_AUTHORITY_BOUNDARY_AUDIT_2026_06_19.md`
- `SongRyeon_Project/Administrative_Reform_2/02_Department_Studies/D7_NIGHT_MEMORY_PROMOTION_AND_GRAPH_PRIVACY_AUDIT_2026_06_19.md`
- `SongRyeon_Project/Administrative_Reform_2/02_Department_Studies/D8_MIDNIGHT_GOVERNMENT_PROPORTIONAL_COUNCIL_SCOPE_AUDIT_2026_06_19.md`
- `SongRyeon_Project/Administrative_Reform_2/02_Department_Studies/D9_COREEGO_LOCAL_COUNCIL_PROPORTIONAL_IDENTITY_AUDIT_2026_06_19.md`
- `SongRyeon_Project/Administrative_Reform_2/02_Department_Studies/D10_NIGHT_COREEGO_TRACEABILITY_REPLAY_REQUIREMENTS_2026_06_19.md`
- `SongRyeon_Project/Administrative_Reform_2/02_Department_Studies/GOVERNOR_MIDNIGHT_COREEGO_PROPORTIONAL_COUNCIL_SYNTHESIS_2026_06_19.md`
- `SongRyeon_Project/Administrative_Reform_2/03_V5_Constitution_Materials/ANIMA_MIDNIGHT_COREEGO_TRACE_REPLAY_FIXTURE_REPORT_2026_06_20.md`
- `SongRyeon_Project/Core/_archive_v3_midnight/midnight_reflection.py`
- `SongRyeon_Project/Core/_archive_v3_midnight/midnight/rem_governor.py`

## Core에 반영한 철학 문서

- `Administrative_Reform_1/00_Philosophy/Night_Government_August_Materials_From_Main_Project_2026_07_02.md`
- `Administrative_Reform_1/00_Philosophy/Night_Government_Graph_Memory_Philosophy_2026_06_30.md`
- `Administrative_Reform_1/00_Philosophy/README.md`

## 정리한 핵심

- 본점의 Sleep Stack은 밤이 낮의 정책/도구/기억 사용을 준비한다는 큰 비전을 제공한다.
- Core는 이 비전을 당장 route/tool/final authority로 열지 않고, graph memory의 source/version/summary/validity/R-guide 정리로 좁힌다.
- 8월 Core 심야정부의 핵심 재료는 `NightJobLedger`, `SourceVersionLineage`, `SummaryInvalidationLedger`, `LeafSummaryGraphNode`, `SourceKindBundleSummary`, `TimeBundleSummary`, `CoreEgoGuideSummary`다.
- 밤 산출물은 기본적으로 advisory/candidate/summary material이며, 낮의 route/tool/answer mode/final evidence 권한을 직접 갖지 않는다.
- dynamic source가 바뀌면 완료된 옛 summary는 삭제하지 않고 invalidated로 남기며, pending summary는 `superseded_before_run`으로 닫고 LLM 호출을 하지 않는다.
- 시간축은 기본 골격으로 유지하고, 의미축은 R-loop 수요가 실제로 관측된 뒤 demand-driven으로 연다.

## 검증

문서 작업만 수행했다.

실행 예정 검증:

```powershell
git diff --check
```

