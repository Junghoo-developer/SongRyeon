# order_139_graph_memory_foundation_2026_06_30_001

## 1. 작업 요약

ORDER_139에 따라 TurnStateCapsule 기반 graph memory foundation과 RLoopGraphGuidePacket v0를 추가했다.

이번 작업은 외부 graph DB, 심야정부 worker, R route, R1/R2/R3 loop를 열지 않았다.

구현 범위:

- `GraphMemoryNodeFrame`, `GraphMemoryEdgeFrame`, `GraphMemorySnapshotFrame`, `CoreEgoTimeAxisFrame`, `RLoopGraphGuidePacketFrame` schema 추가.
- `TurnStateCapsule` 좌표에서 `graph:raw_capsule:{turn_id}` raw node를 deterministic/idempotent하게 생성.
- `graph:core_ego:root -> graph:axis:time -> graph:time_bundle:{batch_id} -> graph:raw_capsule:{turn_id}` edge 구조 생성.
- raw node의 `summary_depth=0`, `source_leaf_count=1`, `source_summary_count=0` 보존.
- snapshot 기반 `RLoopGraphGuidePacketFrame` 생성 및 DataStore 보존.
- dry-run/smoke/runtime summary에 graph memory guide count/status 노출.

## 2. 읽은 기준 문서

- `AGENTS.md`
- `Administrative_Reform_1/01_Maintenance_System/SCHEMA_METAINFO_POLICY_v0.md`
- `Administrative_Reform_1/00_Philosophy/Night_Government_Graph_Memory_Philosophy_2026_06_30.md`
- `Administrative_Reform_1/00_Philosophy/R_Loop_Graph_Guide_Philosophy_2026_06_30.md`
- `Administrative_Reform_1/05_Execution_Records/night_government_mvp_removed_2026_06_30_001.md`
- `Administrative_Reform_1/04_Orders/ORDER_138_INTEGRATION_BASELINE_AND_DIRTY_WORKTREE_RECONCILIATION_V0.md`

## 3. 구현 위치

- Schema:
  - `songryeon_core/core/schema_parts/graph_memory.py`
  - `songryeon_core/core/schema_parts/__init__.py`
  - `songryeon_core/core/schemas.py`
- Builder/recording:
  - `songryeon_core/core/graph_memory.py`
- Runtime exposure:
  - `songryeon_core/runtime/dry_run.py`
  - `songryeon_core/runtime/terminal_view.py`
  - `songryeon_core/runtime/smoke_test.py`
- Tests:
  - `tests/test_order_139_graph_memory_foundation.py`

## 4. 메타정보 경계

Raw capsule node는 의미 기억 text를 만들지 않는다.

담는 값:

- node id
- source turn id
- trace count
- movement count
- user/final trace anchor
- source trace ids
- summary/source count 계산 필드
- char budget status

RLoopGraphGuidePacket은 다음 상태로 고정했다.

```text
generated_by = CODE:GRAPH_MEMORY_GUIDE_BUILDER
info_class = absolute
semantic_judgement_status = not_run
recommended_traversal_hints_status = not_run
```

LLM traversal hint와 의미축은 생성하지 않았다.

## 5. 금지 항목 확인

- `songryeon_core/night_government` 패키지 재생성 없음.
- `MemoryRecord`, `NightGovernmentPacket`, `MemoryActivationItem` 재사용 없음.
- 독립 JSONL memory DB 생성 없음.
- Neo4j/SQLite/vector DB 연결 없음.
- CoreEgo 의미축 생성 없음.
- R1/R2/R3 loop 구현 없음.
- node_1 R route 연결 없음.
- node_3 최종 답변에 graph guide 자동 주입 없음.
- summary를 raw node 속성에 덮어쓰기 없음.

## 6. 검증 결과

작업 전 체크:

- `git status --short --branch`: clean, `codex/integration-night-baseline-20260630`
- `python -m compileall songryeon_core main.py`: 통과
- `python -m pytest`: 120초 제한에서는 timeout
- `python main.py smoke-test`: 120초 제한에서는 timeout

작업 후 체크:

- `python -m compileall songryeon_core main.py`: 통과
- `python -m pytest tests/test_order_139_graph_memory_foundation.py`: `6 passed`
- `python -m pytest`: `83 passed in 339.37s`
- `python main.py smoke-test`: `SMOKE_TEST_OK`
- `git diff --check`: 통과

작업 전 timeout은 실패로 판정하지 않고, 전체 pytest/smoke가 120초보다 오래 걸리는 기준선 특성으로 기록한다.
