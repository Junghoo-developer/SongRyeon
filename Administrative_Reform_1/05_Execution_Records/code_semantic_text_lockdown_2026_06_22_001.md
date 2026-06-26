# Code Semantic Text Lockdown 2026-06-22 001

**상태**: 완료 기록  
**관련 발주서**: `ORDER_067_CODE_SEMANTIC_TEXT_LOCKDOWN`  
**실행일**: 2026-06-22

## 수행 내용

코드가 직접 쓰던 자연어 의미문을 `CODE_STATUS:*` 라벨과 절대정보 필드로 낮췄다.

주요 변경:

1. Node0 memory packet
   - `compression_summary`를 자연어 요약 대신 `CODE_STATUS:trace_evidence_ids_supplied`로 변경.
   - `evidence_trace_count`, `operation_label` 추가.
2. Node1 router
   - 자연어 라우팅 이유 대신 `route_rule_id`, `matched_keywords`, `policy_flag` 추가.
   - `route_reason`은 `CODE_STATUS:*` 라벨로 격하.
3. L1 goal setter
   - `macro_goal_reason`, `micro_goal_reason`을 자연어 문장에서 `CODE_STATUS:*` 라벨로 격하.
4. Tool choice and L loop control
   - tool choice에 `tool_choice_policy_id`, `expected_effect_label`, `choice_generation_source`, `llm_tool_choice_status` 추가.
   - budget/control reason을 `CODE_STATUS:*` 라벨과 `condition_flags`로 격하.
5. L3 result keeper
   - 달성 이유문을 자연어 판단문에서 `CODE_STATUS:*` 운영 라벨로 격하.
6. Node2 boundary
   - 코드 생성 L3 reason과 tool choice reason을 mixed info로 승격하지 않게 변경.
7. Runtime pretty output
   - `규칙 근거` 대신 `operation_label`, `route_rule_id`, `matched_keywords`, `policy_flag`를 표시.

## 검증

`python main.py smoke-test` 통과.

중요한 변화:

- 기본 dry run의 `mixed_info_count`: `0`
- `mixed_info_excludes_code_l3_reason`: `true`
- `mixed_info_excludes_code_tool_choice_reason`: `true`

`python main.py fake-turn "송련의 문서 메모리 인덱스가 무엇을 읽는지 알려줘" --pretty`로 런타임 표시를 확인했다.

## 남은 한계

최종 `[answer]`는 아직 `CODE/RENDERER | LLM_REPORTER=not_run` 상태다.

코드 렌더러의 자연어 안내는 남아 있지만, 최종 보고문을 LLM으로 승격하는 작업은 `ORDER_073_NODE3_LLM_REPORTER`에서 처리한다.

