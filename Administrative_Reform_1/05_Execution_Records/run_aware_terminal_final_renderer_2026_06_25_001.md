# Run-Aware Terminal/Final Renderer - 2026-06-25-001

## Source Order

- `Administrative_Reform_1/04_Orders/ORDER_098_RUN_AWARE_TERMINAL_FINAL_RENDERER_V0.md`

## Context

채팅방 이동으로 작업 루틴이 끊긴 뒤, 현재 저장소 상태를 재확인했다.

`ORDER_096`의 same-turn L reroute controller와 `ORDER_097`의 L tool budget max 5는 실행 기록과 smoke-test 기준으로 이미 통과 상태였다.

이 기록은 `ORDER_098` 관련 코드 상태와 검증 결과를 고정하기 위한 복구 기록이다.

## Observed Scope

현재 코드에는 `ORDER_098`의 핵심 보강이 반영되어 있다.

- `terminal_view.py`는 실제 L 실행 수, 차단된 same-turn L reroute 요청, L 내부 revision 상태를 구분해 표시한다.
- `terminal_view.py`의 run-scoped 조회는 최신 L run record를 우선 선택하고 legacy ID fallback을 유지한다.
- `node_2_handoff.py`는 문서 수를 `reportable_document_count`, `raw_document_extract_record_count`, `empty_document_extract_record_count`로 분리한다.
- `Node2HandoffFrame.read_doc_count`는 호환 필드로 유지하되 `reportable_document_count`와 같은 값이어야 한다.
- `node_2_handoff.py`의 route path는 실제 L run과 controller에 의해 차단된 `route=L` 요청을 구분한다.
- `node_3_input_brief` reporting rules와 LLM payload에는 최종 응답자가 내부 node 자기정체성으로 말하지 않도록 경계가 추가되어 있다.
- smoke-test에는 위 count 분리, latest run 우선, raw internal ID 비노출, reporter identity boundary 검사가 포함되어 있다.

## Count Semantics

`ORDER_098`의 read_doc 혼동은 다음 기준으로 분리된다.

- `reportable_document_count`: 본문 text가 있어 최종 보고 재료로 쓸 수 있는 문서 수.
- `raw_document_extract_record_count`: `read_doc` / `read_artifact` 계열 원시 추출 기록 수.
- `empty_document_extract_record_count`: 원시 추출 기록 중 본문 text가 비어 있는 기록 수.
- `read_doc_count`: 호환 필드이며 현재 의미는 `reportable_document_count`와 같다.

따라서 `documents=2`와 raw extract `3`이 함께 있을 수 있다.
이 경우 2는 보고 가능 문서 수이고, 3은 빈 기록을 포함한 원시 읽기/추출 시도 기록 수다.

## Route Display Semantics

terminal/runtime 표시는 다음 세 가지를 섞지 않아야 한다.

- 실제 실행된 L run.
- same-turn top-level L reroute controller가 차단한 추가 `route=L` 요청.
- L 내부 continuation/revision.

현재 route path는 실제 L run까지만 `L:L1_L2_tools_L3(run=N)`으로 표시하고, 실행되지 않은 추가 요청은 `L:top_level_reroute_blocked_by_controller` 계열로 표시한다.

## Verification

```powershell
python -m compileall songryeon_core main.py
```

Result: passed.

```powershell
python main.py smoke-test
```

Result: passed. `SMOKE_TEST_OK`.

Observed smoke fields:

```text
runtime_count_reportable_documents=2
runtime_count_raw_extract_records=3
runtime_count_empty_extract_records=1
same_turn_l_reroute_default_run_count=1
same_turn_l_reroute_policy_run_count=2
same_turn_l_reroute_third_run_blocked=true
same_turn_l_reroute_final_reason=CODE_STATUS:same_turn_L_reroute_max_runs_reached
```

## Next Operator Note

다음 작업자는 새 기능을 넓히기 전에 이 상태를 기준점으로 삼는다.

당장 필요한 다음 행동은 대규모 구현이 아니라 다음 중 하나다.

1. `ORDER_098` 완료 상태를 사람이 직접 리뷰한다.
2. 실제 qwen-turn 출력에서 terminal/final 문구가 사람이 오해하지 않게 보이는지 확인한다.
3. 통과 상태가 맞다면 `ORDER_099` 또는 다음 발주서를 새로 쓰기 전, 변경 범위를 먼저 문서화한다.
