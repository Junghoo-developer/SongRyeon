# Current Architecture Pre-Extension Audit 2026-06-25 001

## 0. Audit Scope

감사 발주:

```text
<local-practice-notes>/SONGRYEON_CORE_CURRENT_ARCHITECTURE_AND_PRE_EXTENSION_AUDIT_2026_06_25.md
```

감사 대상:

```text
<local-workspace>/SongRyeon_Core
```

이번 감사에서는 새 기능을 구현하지 않았다.

코드 변경 없음.
새로 남긴 것은 이 실행 기록뿐이다.

주의:

```text
git status --short
```

위 명령은 현재 폴더가 git repository가 아니라서 실패했다.
따라서 변경 추적은 git diff가 아니라 파일 감사와 실행 결과 기준으로 기록한다.

## 1. 현재 실행 경로 요약

실제 실행은 fake adapter와 dry-run runtime으로 세 경로를 재현했다.

### A. route=2 직행 경로

입력 fixture:

```text
안녕
```

핵심 결과:

```text
l_loop_run_count=0
route_path=["1:route=2", "0:final_trace_for_2"]
route2_handoff.status=ready
node3_input_brief.read_documents=0
node3_input_brief.runtime_tasks=7
node4_gatekeeper.gate_status=pass
```

| step | node_or_loop | mode | input record | output record | generated_by | info_class | semantic_judgement_status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | node_0 | pre_route_report | user input trace | memory_packet:node_1:pre_route_report | CODE:RULE_STUB | absolute task ledger | not_run for task ledger |
| 2 | node_1 | routing | memory_packet:node_1:pre_route_report | route:2 | LLM:songryeon-all-nodes-fake-llm-adapter | absolute task ledger | not_run for task ledger |
| 3 | node_0 | final_trace_for_2 | route:2 | memory_packet:node_2:final_trace_for_2 | CODE:RULE_STUB | absolute task ledger | not_run for task ledger |
| 4 | node_0 | turn_outcome | memory_packet:node_2:final_trace_for_2 | turn_outcome:turn_dry_001 | CODE:RULE_STUB | absolute task ledger | not_run for task ledger |
| 5 | node_0 | node2_input_frame | final_trace_for_2, turn_outcome | node2_input:turn_dry_001 | CODE:RULE_STUB | absolute task ledger | not_run for task ledger |
| 6 | node_0 | route2_handoff | node2_input:turn_dry_001 | node_2:handoff_frame | CODE:RULE_STUB | absolute condition check | not_run |
| 7 | node_2 | metainfo_boundary_and_node3_brief | node_2:handoff_frame, node2_input | boundary_dry_001, node_2:boundary_review, node_3:input_brief_frame | LLM fake + CODE brief builder | mixed brief from absolute sources | node_2 LLM ran, brief builder not_run |
| 8 | node_3 | report | node_3:input_brief_frame | report_dry_001 | LLM:songryeon-all-nodes-fake-llm-adapter | mixed | ran |
| 9 | node_4 | gatekeeper | report_dry_001, node_3 brief | node_4:gatekeeper_frame | LLM:songryeon-all-nodes-fake-llm-adapter | mixed gate review | ran |

### B. route=L 1회 + L internal continuation + route=2 경로

입력 fixture:

```text
내부 문서에서 특정 근거를 찾고 부족하면 다시 검색해줘
```

핵심 결과:

```text
l_loop_run_count=1
l_loop_continuation_count=2
l_loop_revision_query_count=1
l_loop_final_continuation_status=stop_budget_exhausted
route_path=[
  "1:route=L",
  "0:targeted_memory_supply",
  "L:L1_L2_tools_L3(run=1)",
  "0:loop_return_summary",
  "1:route=2",
  "0:final_trace_for_2"
]
route2_handoff.actual_l_run_count=1
route2_handoff.l_internal_revision_count=2
route2_handoff.blocked_same_turn_l_reroute_request_count=0
node3_input_brief.read_documents=1
node3_input_brief.search_candidate_count=6
node3_input_brief.runtime_tasks=12
```

| step | node_or_loop | mode | input record | output record | generated_by | info_class | semantic_judgement_status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | node_0 | pre_route_report | user input trace | memory_packet:node_1:pre_route_report | CODE:RULE_STUB | absolute task ledger | not_run for task ledger |
| 2 | node_1 | routing | memory packet | route:L | LLM fake | absolute task ledger | not_run for task ledger |
| 3 | node_0 | targeted_memory_supply | route:L | memory_packet:L:targeted_memory_supply | CODE:RULE_STUB | absolute task ledger | not_run |
| 4 | L | L_loop_run_0001 | memory_packet:L:targeted_memory_supply | L:run_frame:0001, L1, L2, search/read_doc, L3, L:continuation:0001/0002, L2:revision_query_frame:0001, L3:revision_achievement:0001 | mixed L1/L2/L3 fake adapters + CODE controller/tools | mixed loop bundle | LLM semantic where adapter ran; code checks not_run |
| 5 | node_0 | loop_return_summary | L output bundle | memory_packet:node_1:loop_return_summary, L:return_summary_frame | CODE:RULE_STUB | absolute/mixed copied summary | not_run |
| 6 | node_1 | routing_after_l_return | loop_return_summary | route:2 | LLM fake | routing decision | ran |
| 7 | L_reroute_controller | same_turn_l_reroute_policy | route:2, L return summary | L:reroute_controller:0001 | CODE:SAME_TURN_L_REROUTE_CONTROLLER | absolute_policy_decision | not_run |
| 8 | node_0 | final_trace_for_2 | route:2 | memory_packet:node_2:final_trace_for_2 | CODE:RULE_STUB | absolute task ledger | not_run |
| 9 | node_0 | turn_outcome | final_trace_for_2 | turn_outcome:turn_dry_001 | CODE:RULE_STUB | absolute task ledger | not_run |
| 10 | node_0 | node2_input_frame | final_trace_for_2, turn_outcome | node2_input:turn_dry_001 | CODE:RULE_STUB | absolute input frame | not_run |
| 11 | node_0 | route2_handoff | node2_input | node_2:handoff_frame | CODE:ROUTE2_HANDOFF_CHECK | absolute_condition_check | not_run |
| 12 | node_2 | metainfo_boundary_and_node3_brief | handoff, node2_input | boundary_dry_001, node_2:boundary_review, node_3:input_brief_frame | CODE + LLM fake review | mixed brief from sources | review ran, brief builder not_run |
| 13 | node_3 | report | node_3 input brief | report_dry_001 | LLM fake | mixed | ran |
| 14 | node_4 | gatekeeper | report, brief | node_4:gatekeeper_frame | LLM fake | mixed gate review | ran |

### C. same-turn L reroute enabled + L run 2 + route=2 경로

입력 fixture:

```text
내부 문서를 검색하고 부족하면 같은 턴에서 한 번 더 L을 실행해줘
```

핵심 결과:

```text
same_turn_l_reroute_enabled=true
max_l_runs_per_turn=2
l_loop_run_count=2
final_reroute_controller_decision=close_route_2
final_reroute_controller_reason=CODE_STATUS:same_turn_L_reroute_max_runs_reached
route2_handoff.actual_l_run_count=2
route2_handoff.blocked_same_turn_l_reroute_request_count=1
route2_handoff.l_internal_revision_count=0
final downstream id scope=L:run:0002:*
```

| step | node_or_loop | mode | input record | output record | generated_by | info_class | semantic_judgement_status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | node_0 | pre_route_report | user input trace | memory_packet:node_1:pre_route_report | CODE:RULE_STUB | absolute task ledger | not_run |
| 2 | node_1 | routing | memory packet | route:L | LLM:same-turn-l-reroute-fake-adapter | routing decision | ran |
| 3 | node_0 | targeted_memory_supply | route:L | memory_packet:L:targeted_memory_supply | CODE:RULE_STUB | absolute memory packet | not_run |
| 4 | L | L_loop_run_0001 | memory_packet:L:targeted_memory_supply | L:run_frame:0001, L1/L2/tool/L3 bundle | LLM fake + CODE tools | mixed loop bundle | mixed |
| 5 | node_0 | loop_return_summary | L run 1 output | memory_packet:node_1:loop_return_summary, L:return_summary_frame | CODE:RULE_STUB | copied structured summary | not_run |
| 6 | node_1 | routing_after_l_return | run 1 return summary | L:reroute:route:L | LLM fake | routing decision | ran |
| 7 | L_reroute_controller | same_turn_l_reroute_policy | L:reroute:route:L | L:reroute_controller:0001 | CODE:SAME_TURN_L_REROUTE_CONTROLLER | absolute_policy_decision | not_run |
| 8 | node_0 | targeted_memory_supply | L:reroute_controller:0001 | L:run:0002:memory_packet:L:targeted_memory_supply | CODE:RULE_STUB | absolute memory packet | not_run |
| 9 | L | L_loop_run_0002 | scoped L memory packet | L:run_frame:0002, L:run:0002:L1/L2/tool/L3 bundle | LLM fake + CODE tools | mixed loop bundle | mixed |
| 10 | node_0 | loop_return_summary | L run 2 output | L:run:0002:memory_packet:node_1:loop_return_summary, L:run:0002:L:return_summary_frame | CODE:RULE_STUB | copied structured summary | not_run |
| 11 | node_1 | routing_after_l_return | run 2 return summary | L:run:0002:route:L | LLM fake | routing decision | ran |
| 12 | L_reroute_controller | same_turn_l_reroute_policy | L:run:0002:route:L | L:run:0002:L:reroute_controller:0001 | CODE:SAME_TURN_L_REROUTE_CONTROLLER | absolute_policy_decision | not_run |
| 13 | node_1 | routing_policy_close_to_2 | controller close | L:run:0002:route:2 | CODE/RULE close decision recorded by node_1 path | policy close routing | not_run |
| 14 | node_0 | final_trace_for_2 | L:run:0002:route:2 | L:run:0002:memory_packet:node_2:final_trace_for_2 | CODE:RULE_STUB | absolute memory packet | not_run |
| 15 | node_0 | turn_outcome | scoped final_trace_for_2 | L:run:0002:turn_outcome:turn_dry_001 | CODE:RULE_STUB | absolute outcome | not_run |
| 16 | node_0 | node2_input_frame | scoped final/outcome | L:run:0002:node2_input:turn_dry_001 | CODE:RULE_STUB | absolute input frame | not_run |
| 17 | node_0 | route2_handoff | scoped node2_input | L:run:0002:node_2:handoff_frame | CODE:ROUTE2_HANDOFF_CHECK | absolute_condition_check | not_run |
| 18 | node_2 | metainfo_boundary_and_node3_brief | scoped handoff/input | L:run:0002:boundary_dry_001, L:run:0002:node_3:input_brief_frame | CODE + LLM fake review | mixed brief from sources | review ran, brief builder not_run |
| 19 | node_3 | report | scoped brief | L:run:0002:report_dry_001 | LLM fake | mixed | ran |
| 20 | node_4 | gatekeeper | scoped report/brief | L:run:0002:node_4:gatekeeper_frame | LLM fake | mixed gate review | ran |

## 2. 문서 계약과 코드의 일치 여부

대체로 일치한다.

주요 일치 근거:

- `Node2InputFrame`과 `Node2HandoffFrame`이 route=2 진입 범위를 제한한다.
- `Node3InputBriefFrame`이 read_documents, search_candidate_documents, allowed_claims, runtime_tasks를 분리한다.
- node_3 LLM payload는 document/source raw ID를 본문 입력에서 제거한다.
- node_4는 Node3InputBrief와 rendered report를 함께 받아 검사한다.
- same-turn L reroute는 기본 off이고, flag on에서도 v0 ceiling 2로 제한된다.
- Task Ledger v0는 scheduler가 아니라 `NodeMovement`를 `TaskFrame`/`TaskResultFrame`으로 복사한다.

문서와 코드의 작은 불일치:

- `ORDER_098_RUN_AWARE_TERMINAL_FINAL_RENDERER_V0.md`는 상태가 "구현 전 발주서"로 남아 있지만, 실제 코드와 smoke-test에는 run-aware renderer, count 분리, route path 표시 정직성, node_3 identity boundary가 상당 부분 구현되어 있다.
- 다음 개발 전에 ORDER_098 상태 또는 후속 실행 기록을 기준선으로 정리하는 편이 좋다.

## 3. L internal continuation / same-turn reroute 구분 상태

구분 상태는 양호하다.

L internal continuation:

```text
L:continuation:0001
memory_packet:L2:l3_continuation_summary_for_L2:0001
L2:revision_input:0001
L2:revision_query_frame:0001
L3:revision_achievement:0001
```

top-level same-turn reroute:

```text
L:reroute_controller:0001
L:run:0002:L:reroute_controller:0001
```

terminal/runtime 표시:

```text
actual_l_runs=N
top_level_l_reroute_request_blocked=N
l_internal_revision=present|none
```

route path도 실제 실행과 차단 요청을 분리한다.

정책 disabled fixture에서 확인된 표시:

```text
L:L1_L2_tools_L3(run=1)
L:top_level_reroute_blocked_by_controller
```

policy enabled fixture에서 확인된 표시:

```text
actual_l_run_count=2
blocked_same_turn_l_reroute_request_count=1
final reason=CODE_STATUS:same_turn_L_reroute_max_runs_reached
```

주의:

- L internal continuation live 배선은 `l2_query_planner_adapter`가 있을 때 실행된다.
- adapter 없는 코드 fallback 경로에서는 continuation controller가 live graph로 돌지 않는다.

## 4. count consistency 감사 결과

현재 count 명명은 정직하게 분리되어 있다.

보고 가능한 문서 수의 기준:

```text
data_type startswith tool_result:read_doc 또는 tool_result:read_artifact
and payload.text is non-empty string
```

원시 문서 추출 record 수의 기준:

```text
data_type startswith tool_result:read_doc 또는 tool_result:read_artifact
payload.text 존재/공백 여부와 무관하게 record 전체를 셈
```

빈 추출 record 수의 기준:

```text
document extract record 중 payload.text가 없거나 공백인 record
```

검색 후보 문서 수의 기준:

```text
L3 preserved_info_frame.candidates 안의 doc_id를 사람이 읽는 문서명으로 정리한 unique list
```

runtime task 수의 기준:

```text
node_3 input brief 생성 직전까지의 NodeMovement 목록
preview movement를 포함해 node_3가 받은 현재 턴 실행 순서 자료 수를 셈
```

grounding block counts 기준:

```text
읽은 문서 = len(Node3InputBriefFrame.read_documents)
검색 후보 문서 = Node3InputBriefFrame.search_candidate_count
현재 턴 실행 순서 자료 = len(Node3InputBriefFrame.runtime_tasks)
```

node4 count guard expected counts:

```text
node_4가 보고문 첫머리의 '근거 기준:' 블록을 파싱해서 위 expected counts와 비교한다.
불일치하면 LLM gate pass라도 needs_revision으로 강제한다.
```

검증 fixture:

```text
reportable_document_count=2
raw_document_extract_record_count=3
empty_document_extract_record_count=1
```

위 fixture에서 `read_doc_count`는 호환 필드로 `reportable_document_count`와 같아야 한다.
스키마 validator가 이 관계를 강제한다.

## 5. node_3 identity boundary 감사 결과

현재 방어는 세 겹이다.

1. `Node3InputBriefFrame.reporting_rules`
2. `node3_brief_llm_payload.reporter_identity_boundary`
3. `node_3_reporter_v0.md` prompt

핵심 규칙:

```text
너는 특정 내부 노드 그 자체가 아니라, 사용자에게 보고하는 송련의 최종 응답자 관점으로 말한다.
node_0/node_1/node_2/node_3 같은 내부 역할명은 자기정체성으로 쓰지 않는다.
```

현재 smoke-test는 brief 안에 이 규칙이 존재하는지 검사한다.

남은 위험:

- node_4 prompt는 raw internal ID, unsupported claim, grounding mismatch는 검사하지만, "자기 자신을 node_2/node_3로 정의함"을 별도 구조 규칙이나 code guard로 강제하지는 않는다.
- 다음에 실제 Qwen 출력에서 같은 문제가 반복되면 node_4 unsupported/contradiction rule 또는 code-level identity phrase guard를 추가할 수 있다.

## 6. node_4 remand 이후 확장 준비성

현재형 safe blocking은 구현되어 있고 smoke-test로 확인된다.

확인 결과:

```text
gate_status=needs_revision -> final answer is FINAL_BLOCKED_BY_GATEKEEPER
gate_status=failed -> content remand처럼 말하지 않고 "검사 자체 실패"라고 말함
```

좋은 점:

- 반려된 node_3 원문이 사용자-facing answer로 그대로 나가지 않는다.
- count guard mismatch도 safe blocking으로 이어진다.
- failed gate는 근거 밖 주장/모순 감지처럼 과장하지 않는다.

남은 확장 준비성:

- `revision_targets`는 있다.
- 그러나 자동 재작성 루프용 `return_target_node`, `return_reason_code`, `rewrite_scope`, `reroute_scope` 같은 구조화 필드는 아직 없다.
- 따라서 현재 정보는 사람이 다음 조치를 판단하기에는 충분하지만, node_4 -> node_3 자동 재작성 또는 node_4 -> node_1 재라우팅을 안전하게 열기에는 아직 부족하다.

이번 감사에서는 자동 재작성 루프를 열지 않았다.

## 7. router fallback policy 감사 결과

현재 node_1 경계:

- LLM route 성공: `route_source=LLM:<model>`, `llm_routing_status=ran`
- 코드 route: `route_source=CODE:RULE_STUB` 또는 `CODE:POLICY_STUB`, `llm_routing_status=not_run`

좋은 점:

- keyword fallback이 Qwen 판단처럼 보이지는 않는다.
- `force_l_route`는 `CODE_STATUS:force_l_route_policy`와 `policy_flag=force_l_route`로 드러난다.

남은 문제:

- `run_dry_turn`은 node_1 LLM router 예외 발생 시 `route_next()`로 fallback한다.
- 이때 최종 route frame은 `CODE:RULE_STUB`로 남으므로 Qwen 판단으로 위장하지는 않지만, "LLM router failed -> code fallback used"라는 전환 사실이 routing frame 안에 명시적으로 연결되어 있지는 않다.

권장 보강:

```text
router_fallback_policy
router_llm_failure_data_id
fallback_after_llm_failure=true
fallback_policy=dev_keyword_stub_fallback | strict_route2_on_router_llm_fail
strict_router_failed_status
```

특히 Qwen 실사용 모드에서는 "LLM 라우터 실패 후 keyword fallback"을 dev/smoke fallback으로 드러내거나, strict mode에서는 route=2 safe close로 보내는 정책을 별도 선택지로 두는 편이 좋다.

## 8. 다음 개발 전에 반드시 고칠 것

1. router fallback 전환 사실을 routing frame 또는 별도 frame으로 남긴다.
2. ORDER_098의 문서 상태를 실제 구현/검증 상태와 맞춘다.
3. node_4 자동 재작성 루프를 열기 전에 `return_target_node` 계열 구조화 필드를 설계한다.
4. node_3 identity boundary 위반을 node_4가 별도 반려할 수 있게 prompt 또는 code guard smoke를 추가한다.

## 9. 지금은 건드리지 말아야 할 것

이번 기준선에서는 다음을 열지 않는다.

```text
W loop
R loop
scheduler 실행 정책
외부 DB
장기기억 DB
node_4 자동 재작성 루프
same-turn L reroute 3회차 이상
휴리스틱 덧칠
count mismatch 숨기기
```

## 10. compileall / smoke-test 결과

실행 명령:

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
```

결과:

```text
compileall: exit code 0
smoke-test: exit code 0
status: SMOKE_TEST_OK
```

주요 smoke 결과:

```text
same_turn_l_reroute_default_run_count=1
same_turn_l_reroute_policy_run_count=2
same_turn_l_reroute_third_run_blocked=true
runtime_count_reportable_documents=2
runtime_count_raw_extract_records=3
runtime_count_empty_extract_records=1
node4_remand_blocked=true
node4_grounding_count_guard=needs_revision
node4_gate_failed_honest=true
live_l_loop_continuation_count=2
live_l_loop_revision_query_count=1
live_l_loop_final_continuation=stop_budget_exhausted
```

## 11. 한 줄 결론

현재 SongRyeon Core는 다음 확장 전에 가장 위험했던 세 지점인 count 혼동, L internal continuation과 top-level reroute 혼동, node_4 반려 후 최종 answer 누출을 이미 상당 부분 막고 있다.

다음 문턱은 새 루프가 아니라 router fallback 정직성, node_4 remand target 구조화, ORDER_098 문서 상태 정리다.
