# ORDER_105 Memory Selection to Node2 Handoff 실행 기록

## 작업 일시

2026-06-26

## 목표

`MemoryRelevanceSelectionFrame`을 route=2 handoff와 node_3 input brief에 전달하되, selector 판단을 code fact처럼 보이게 만들지 않는다.

핵심 경계는 다음이다.

```text
handoff: id/status/count/source만 보존
boundary: selection_reason을 LLM selector의 mixed info로 보존
brief: 선택 결과 material을 전달하되 선택된 과거 턴 내용을 요약하지 않음
```

## 변경 파일

- `songryeon_core/core/schemas.py`
- `songryeon_core/nodes/node_2_handoff.py`
- `songryeon_core/nodes/node_2_metainfo_boundary.py`
- `songryeon_core/runtime/dry_run.py`
- `songryeon_core/runtime/smoke_test.py`
- `songryeon_core/runtime/terminal_view.py`

## 구현 내용

### 1. Node2InputFrame source_data_ids 보강

`run_dry_turn()`의 `Node2InputFrame.source_data_ids`에 다음 selector frame id를 추가했다.

```text
memory_packet:node_1:pre_route_report:memory_relevance_selection
```

기존 `memory_packet:node_1:pre_route_report`, route ids, `memory_packet:node_2:final_trace_for_2`, `turn_outcome:*`도 유지된다.

### 2. Node2HandoffFrame selection summary

`Node2HandoffFrame`에 다음 절대 요약 필드를 추가했다.

```text
memory_relevance_selection_frame_id
memory_relevance_selection_status
memory_relevance_candidate_count
memory_relevance_selected_count
memory_relevance_info_class
memory_relevance_generated_by
memory_relevance_llm_call_data_id
```

handoff는 `selection_reason`을 해석하거나 싣지 않는다.
selection frame id가 있으면 `Node2HandoffFrame.source_data_ids`에도 반드시 포함된다.

### 3. node_2 boundary mixed 보존

`MemoryRelevanceSelectionFrame`이 다음 조건을 만족할 때만 `selection_reason`을 `MetainfoBoundary.mixed_info`로 보존한다.

```text
info_class=mixed
source_mode=source_bundle
claim_alignment=multi_source_bundle
generated_by=LLM:...
```

생성되는 mixed info는 다음 식별을 가진다.

```text
info_kind=memory_relevance_selection_reason
field_path=selection_reason
source_data_id=<memory relevance selection frame id>
source_mode=source_bundle
claim_alignment=multi_source_bundle
```

failed/no-candidates 같은 code status close는 selector LLM 의미 판단으로 승격하지 않는다.

### 4. Node3InputBriefFrame material

`Node3MemorySelectionMaterial`을 추가하고 `Node3InputBriefFrame.memory_selection_material`로 전달한다.

selected일 때는 다음을 보존한다.

```text
selected_memory_count
memory_selection_status
memory_selection_reason
memory_selection_info_class
memory_selection_source_mode
memory_selection_claim_alignment
selected_candidate_turn_ids
source_memory_item_ids
source_data_id
generated_by
```

`node3_brief_llm_payload()`는 raw source id와 selected turn id를 LLM payload에 직접 넣지 않고, count/status/reason/info_class/source_mode/claim_alignment/generated_by만 전달한다.

### 5. none_selected/failed 안전

`none_selected`, `failed`, no-candidates 경로에서는 다음을 검증한다.

```text
selected_memory_count=0
selected_candidate_turn_ids=[]
```

따라서 failed selector나 none_selected selector가 선택된 기억 material처럼 node_3에 전달되지 않는다.

### 6. terminal/runtime 출력

runtime view에 다음 형태의 줄을 추가했다.

```text
memory_relevance_selection: status=... / candidates=... / selected=... / generated_by=...
```

selector frame 영역, route=2 handoff 영역, node_3 brief material 영역에서 사람이 상태를 확인할 수 있다.

## Smoke 확인값

`python main.py smoke-test` 결과에 다음 확인값이 추가됐다.

```text
memory_selection_handoff_status=selected
memory_selection_handoff_selected_count=1
memory_selection_boundary_mixed=true
memory_selection_node3_selected_count=1
memory_selection_no_raw_answer_leak=true
```

기존 ORDER_104 확인값도 유지된다.

```text
recent_memory_relevance_selection_selected=selected
recent_memory_relevance_selection_none=none_selected
recent_memory_relevance_selection_failed=failed
recent_memory_relevance_selection_no_candidates=none_selected
recent_memory_relevance_selection_info_class=mixed
```

## 검증

```powershell
python -m compileall songryeon_core main.py
```

통과.

```powershell
python main.py smoke-test
```

최초 1회 실패:

```text
AssertionError: final answer must not expose raw memory selection ids
```

원인은 구현 누수가 아니라 smoke 입력 문장 자체가 `turn_prev_001` raw id를 포함해, 답변의 사용자 입력 반영과 raw id 누수 검사가 충돌한 것이다.
선택 fake adapter는 후보 첫 개를 고르므로 사용자 입력에서 raw id를 제거하고 같은 selected 경로를 재검증했다.

최종 재실행은 통과.

```text
SMOKE_TEST_OK
```

## 비범위 유지

이번 작업에서 다음은 하지 않았다.

- 선택된 과거 대화 원문 요약
- 선택된 과거 대화 자동 답변 삽입
- 장기기억 DB
- vector DB
- embedding 기반 memory search
- memory graph
- 오래된 대화 요약
- 관련성 heuristic fallback
- 키워드/문자열 유사도 selector

## 남은 위험

- `selected_candidate_turn_ids`는 brief frame 내부에는 보존된다. 최종 답변 누수는 renderer/LLM payload 경계로 막았지만, 이후 node_3 본문 생성 정책을 확장할 때 계속 확인해야 한다.
- 현재 node_3에는 선택된 과거 턴의 원문 내용이 전달되지 않는다. 선택 결과를 실제 답변 재료로 쓰는 정책은 별도 발주가 필요하다.
- no-candidates frame은 `info_class=absolute_status` 성격의 code status close다. LLM selector가 판단한 selected/none_selected와 계속 구분해야 한다.
