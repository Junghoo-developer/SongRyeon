# ORDER 099 실행 기록: router fallback honesty MVP v0

## 상태

구현 및 검증 완료.

## 구현 내용

node_1 LLM router 실패 뒤 code rule router fallback이 쓰이는 경우를 처음부터 code rule router만 쓴 경우와 구분하게 했다.

- `core/schemas.py`
  - `RoutingDecision` / `RoutingDecisionFrame`에 router fallback 정직성 필드를 추가했다.
  - 추가 필드:
    - `fallback_after_llm_failure`
    - `router_llm_failure_data_id`
    - `router_llm_failure_trace_event_id`
    - `router_llm_failure_type`
    - `fallback_policy`
    - `fallback_allowed_by_runtime_policy`
    - `fallback_source_route_rule_id`
    - `llm_call_data_id`
    - `llm_trace_event_id`
  - `RoutingDecisionFrame` fallback 검증 규칙을 추가했다.

- `nodes/node_1_router.py`
  - `Node1RouterLLMFailure` 예외를 추가해 실패한 LLM call의 data id, trace event id, failure type을 보존하게 했다.
  - `route_next_with_llm_or_policy_fallback(...)` helper를 추가했다.
  - helper는 LLM 실패 사실과 code fallback decision을 같은 의미판단으로 합치지 않고, 절대정보 필드로만 연결한다.

- `runtime/dry_run.py`
  - node_1 첫 라우팅과 L return 뒤 라우팅 모두 새 helper를 사용하게 했다.
  - dev/smoke 기본 정책은 `dev_smoke_router_fallback_allowed`다.
  - result summary에 `node1_llm_routing_failed_count`, `node1_router_fallback_count`, `node1_router_fallback_policy`를 추가했다.

- `runtime/user_turn.py`
  - Qwen 사용자 턴에서는 node_1 router fallback을 조용히 허용하지 않는다.
  - Qwen strict 정책명은 `qwen_strict_router_fallback_blocked`다.
  - node_1 LLM router가 실패하면 기존 `structure_failed` 경로로 드러난다.

- `runtime/terminal_view.py`
  - terminal routing block에 다음 구분을 추가했다.
    - `node_1 router: CODE:RULE_STUB`
    - `node_1 router: LLM failed -> CODE:RULE_STUB fallback`
    - `node_1 router: LLM ran`
  - fallback일 때 policy, failure type, failed LLM data/trace id, fallback rule id를 표시한다.

- `runtime/smoke_test.py`
  - node_1 LLM router 성공 case, broken JSON 실패 뒤 dev/smoke fallback case, strict blocked case, terminal 표시 구분을 검사하는 smoke를 추가했다.

## 완료 조건 답변

LLM router 실패는 `LLMNodeExecutor`가 만든 `llm_call` record와 `llm_call` trace event에 먼저 기록된다.
`node_1_router.py`의 `Node1RouterLLMFailure`가 이 `call_data_id`, `trace_event_id`, `failure_type`을 보존한다.

code fallback은 `route_next_with_llm_or_policy_fallback(...)` 안에서 `route_next(...)`를 호출해 생성된다.
fallback으로 실제 route를 만든 규칙은 `fallback_source_route_rule_id`에 남긴다.

routing frame에서는 다음 필드로 fallback 전환을 확인한다.

```text
llm_routing_status=failed
fallback_after_llm_failure=true
router_llm_failure_data_id=llm_call:node_1:...
router_llm_failure_trace_event_id=trace_...
router_llm_failure_type=parse_failed 등
fallback_policy=dev_smoke_router_fallback_allowed
fallback_allowed_by_runtime_policy=true
fallback_source_route_rule_id=default_route_to_node_2 등
```

dev/smoke fallback과 Qwen strict policy는 runtime 호출 인자로 구분한다.

- dev/smoke: `allow_node_1_router_fallback=True`, `fallback_policy=dev_smoke_router_fallback_allowed`
- Qwen strict: `allow_node_1_router_fallback=False`, `fallback_policy=qwen_strict_router_fallback_blocked`

terminal view에서는 처음부터 code route인 경우와 LLM 실패 뒤 fallback인 경우가 다음처럼 구분된다.

```text
node_1 router: CODE:RULE_STUB
node_1 router: LLM failed -> CODE:RULE_STUB fallback
node_1 router: LLM ran
```

## 검증

통과:

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
```

smoke-test 결과 중 ORDER_099 관련 확인값:

- `node1_router_fallback_policy`: `dev_smoke_router_fallback_allowed`
- `node1_router_fallback_failure_type`: `parse_failed`
- `node1_router_fallback_terminal_distinct`: true
- `node1_router_strict_blocked`: true
