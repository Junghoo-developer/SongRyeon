# Node2 Input Frame Execution 2026-06-21 001

## 목적

2 메타정보 경계관의 입력을 `Node2InputFrame`으로 정리했다.

## 변경 내용

- `dry_run`에서 0이 `node2_input:<turn_id>` DataStore record를 생성한다.
- `Node2InputFrame`에는 2가 읽을 trace/data ID와 핵심 역할별 ID를 넣는다.
- 2는 `node2_input_frame_id`가 주어지면 전체 trace가 아니라 프레임에 적힌 source만 읽는다.
- 기존 전체 trace 순회 방식은 fallback으로 유지했다.
- 기능 지도에 `Node2InputFrame` 설명을 추가했다.

## 확인 결과

```text
python -m compileall -q songryeon_core
OK

python dry_run.py
DRY_RUN_OK
trace_count=15
data_record_count=14
movement_count=11
current_route=2

python main.py smoke-test
SMOKE_TEST_OK
trace_count=15
data_record_count=14
```

## Node2InputFrame 확인

```text
source_trace_count=12
source_data_count=11
route_ids=['route:L', 'route:2']
l_loop_output_ids=[
  'L1:goal_frame',
  'L2:query_frame',
  'tool_result:search_docs:trace_000007',
  'L3:preserved_info_frame'
]
final_memory_packet_id='memory_packet:node_2:final_trace_for_2'
turn_outcome_id='turn_outcome:turn_dry_001'
```

## 해석

이번 변경은 LLM 판단을 추가한 것이 아니다. 코드가 이미 확정된 trace/data ID를 묶어 2의 입력 범위를 고정한 것이다.

나중에 LLM을 붙일 때도 LLM은 전체 저장소를 직접 보지 않고, 이 프레임으로 정리된 입력을 받는다. 따라서 LLM은 요약과 판단을 맡고, 코드와 스키마는 ID, 출처, 존재 여부, 입력 범위를 관리한다.
