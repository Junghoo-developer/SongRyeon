# ORDER 100 Recent Turn Capsule Read Window - 2026-06-25-001

## Source Order

- `ORDER_100_RECENT_TURN_CAPSULE_READ_WINDOW_PACKET_V0`

## Implemented Scope

0 기억공급관의 `pre_route_report` memory packet에 최근 `TurnStateCapsule` 색인 item을 추가했다.

읽기 창은 코드 상수로 고정했다.

```text
RECENT_TURN_CAPSULE_READ_WINDOW=3
```

`ZeroState.previous_turn_capsules`의 최근 3개만 읽는다.

장기기억 DB, 벡터 DB, 그래프 DB, W/R, scheduler는 사용하지 않았다.

## MemoryItem Format

추가 item은 다음 형식을 따른다.

```text
item_type=previous_turn_capsule_index
text=COPIED_FIELDS:turn_id=...;trace_count=...;movement_count=...;user_input_trace_id=...;final_response_trace_id=...
source_trace_ids=[actual user_input_trace_id, actual final_response_trace_id]
source_data_ids=[]
```

`source_trace_ids`는 해당 trace ID가 capsule의 `trace_event_ids`에 실제로 있을 때만 넣는다.
없는 trace ID는 만들지 않는다.

기존 `trace_evidence` memory item은 `pre_route_report`에 유지된다.

## Changed Files

- `songryeon_core/nodes/node_0_memory_supplier.py`
- `songryeon_core/runtime/dry_run.py`
- `songryeon_core/runtime/smoke_test.py`

## Smoke Coverage

새 smoke는 이전 capsule 4개를 주입하고 다음을 확인한다.

- recent capsule read window N=3
- read capsule count=3
- `memory_packet:node_1:pre_route_report.memory_items`에 `previous_turn_capsule_index` 3개 존재
- 가장 오래된 4번째 capsule은 제외
- 각 item text가 `COPIED_FIELDS` 구조 필드만 포함
- 각 item `source_trace_ids`가 실제 capsule trace ID만 포함
- 각 item `source_data_ids=[]`
- `llm_semantic_summary_status=not_run`
- 기존 `trace_evidence` item 유지

## Verification

```powershell
python -m compileall .\songryeon_core
```

Result: passed.

```powershell
@'
from songryeon_core.runtime.smoke_test import run_smoke_tests
print(run_smoke_tests())
'@ | python -
```

Result: passed. `SMOKE_TEST_OK`.

Observed ORDER_100 smoke fields:

```text
recent_capsule_read_window=3
recent_capsules_read_count=3
recent_capsule_item_type=previous_turn_capsule_index
recent_capsule_trace_evidence_kept=True
recent_capsule_llm_summary_status=not_run
```
