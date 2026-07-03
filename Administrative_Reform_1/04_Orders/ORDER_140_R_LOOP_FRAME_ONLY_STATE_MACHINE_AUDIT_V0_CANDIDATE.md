# ORDER_140_R_LOOP_FRAME_ONLY_STATE_MACHINE_AUDIT_V0_CANDIDATE

## Candidate Status

이 문서는 후보 발주서로 작성되었고, 2026-06-30 사용자 승인 후 frame-only 구현으로 승격되었다.

구현 기록:

- `Administrative_Reform_1/05_Execution_Records/order_140_r_loop_frame_state_machine_2026_06_30_001.md`

초기 후보 상태의 금지선은 계속 유지한다.

이 발주서는 R루프를 실제 route로 여는 작업이 아니다.

## 1. 목표

R루프의 R1/R2/R3/controller/return summary를 코드로 바로 구현하기 전에, 필요한 frame과 상태기계만 설계하고 감사한다.

이번 후보 발주의 핵심은 다음이다.

```text
R루프를 실행하지 않는다.
R루프가 실행된다면 어떤 frame과 상태 전이가 필요한지 먼저 고정한다.
```

## 2. 선행 조건

- ORDER_139가 완료되어 graph memory foundation과 RLoopGraphGuidePacket의 기본 형태가 존재해야 한다.
- `Administrative_Reform_1/00_Philosophy/R_Loop_Graph_Guide_Philosophy_2026_06_30.md`를 읽어야 한다.
- `Administrative_Reform_1/00_Philosophy/Night_Government_Graph_Memory_Philosophy_2026_06_30.md`를 읽어야 한다.

## 3. 제안 frame

후보 frame:

```text
R1GraphGoalFrame
RLoopBudgetFrame
R2GraphNodeSelectionFrame
R3GraphInspectionFrame
RLoopContinuationFrame
RLoopReturnSummaryFrame
```

이번 후보 발주가 구현으로 승격되더라도, 처음에는 dataclass/schema와 validator/fake test까지만 다룬다.

## 4. R1 역할

R1은 graph guide와 사용자 질문을 보고 탐색 목표와 예산을 정한다.

후보 필드:

```text
graph_search_goal
required_information_granularity
allowed_summary_depth
max_traversal_depth
max_branch_switches
max_node_reads
max_context_tokens
stop_condition
source_graph_guide_packet_id
source_data_ids
source_trace_ids
generated_by
info_class
semantic_judgement_status
```

R1의 목표/예산 이유가 LLM 산출이면 relative/mixed다.

코드는 R1의 의미 판단을 대신하지 않는다.

## 5. R2 역할

R2는 후보 graph node 중 하나를 고른다.

후보 필드:

```text
selection_scope
available_graph_node_ids
selected_graph_node_id
selection_reason
expected_information_granularity
expected_source_kind
source_r1_goal_frame_id
generated_by
info_class
semantic_judgement_status
```

R2가 선택할 수 있는 node id는 code가 제공한 `available_graph_node_ids` 안으로 제한한다.

허용 목록 밖 ID는 schema 실패다.

## 6. R3 역할

R3는 선택된 graph node를 검사한다.

후보 필드:

```text
inspected_graph_node_id
node_kind
child_node_count
child_node_ids
summary_depth
source_leaf_count
current_information_granularity
sufficiency_status
granularity_problem_status
branch_problem_status
recommended_next_action
inspection_reason
source_r2_selection_frame_id
generated_by
info_class
semantic_judgement_status
```

중요 구분:

```text
농도 문제
-> 같은 가지는 맞지만 더 낮은 농도 정보가 필요하다.

가지 문제
-> 애초에 선택한 가지가 맞지 않는다.
```

## 7. Controller 상태 후보

```text
stop_sufficient
continue_deeper
continue_switch_branch
stop_budget_exhausted
stop_no_actionable_path
stop_failed_final
```

controller는 의미 판단을 새로 하지 않는다.

controller는 R3의 구조화 status와 예산 숫자만 본다.

## 8. 금지

- R route를 node_1에 연결하지 않는다.
- 실제 graph DB traversal을 자동 실행하지 않는다.
- R1/R2/R3 LLM prompt를 구현하지 않는다.
- 의미축 CoreEgo를 만들지 않는다.
- node_3 최종 답변에 R 결과를 주입하지 않는다.
- code가 graph node 선택 이유를 의미적으로 작성하지 않는다.

## 9. 테스트 후보

구현으로 승격될 경우 테스트:

1. R2 selection은 허용된 graph node id만 통과한다.
2. 허용 목록 밖 graph node id는 validator가 거부한다.
3. R3는 raw leaf, bundle, summary node kind를 구조적으로 구분한다.
4. `continue_deeper`와 `continue_switch_branch`가 서로 다른 status로 남는다.
5. budget exhausted 시 controller가 loop를 닫는다.
6. 모든 LLM 의미 판단 필드는 LLM이 없으면 `not_run` 또는 `failed`로 남는다.

## 10. 완료 조건 후보

아직 구현 금지.

승격 시 완료 조건:

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
git diff --check
```
