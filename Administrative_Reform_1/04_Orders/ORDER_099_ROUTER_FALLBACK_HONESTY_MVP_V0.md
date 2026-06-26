# ORDER 099: Router Fallback Honesty MVP v0

## 상태

구현 완료.

ORDER_098 이후 확장 전에 node_1 router fallback의 메타정보 정직성을 잠그기 위한 좁은 MVP 설계서다.

기준 실행 기록:

- `Administrative_Reform_1/05_Execution_Records/order_099_router_fallback_honesty_mvp_2026_06_25_001.md`

## 배경

현재 node_1 router는 LLM router를 사용할 수 있다.
하지만 LLM router가 실패하면 runtime 쪽에서 기존 code rule router로 fallback할 수 있다.

문제는 fallback 자체가 아니라, 그 전환 사건이 routing frame 안에서 충분히 선명하지 않을 수 있다는 점이다.

현재 감사에서 확인한 코드 흐름:

```text
songryeon_core/nodes/node_1_router.py
- route_next_with_llm(...)
- LLM routing 실패 시 예외 발생
- route_next(...) 규칙 라우터는 CODE:RULE_STUB 또는 CODE:POLICY_STUB 결정을 만든다.

songryeon_core/runtime/dry_run.py
- route_next_with_llm(...) 호출
- except Exception 뒤 route_next(...)로 fallback
- record_routing(...)은 최종 fallback RoutingDecision을 저장한다.
```

이 구조에서는 최종 route가 `CODE:RULE_STUB`으로 보이더라도, 사람이 다음 사실을 한 번에 알기 어렵다.

```text
LLM router를 시도했다.
LLM router가 실패했다.
runtime policy가 code fallback을 허용했다.
그래서 code rule router가 최종 route를 만들었다.
```

## 핵심 질문

```text
node_1이 처음부터 code rule router만 쓴 것인가?
아니면 LLM router가 실패해서 code fallback으로 내려온 것인가?
```

이 둘은 같은 결과 route를 만들 수 있지만, 메타정보 의미가 다르다.

## 원칙

- code fallback을 금지하는 것이 목표가 아니다.
- code fallback을 LLM 판단처럼 보이게 하지 않는 것이 목표다.
- LLM 실패 사실, fallback 허용 정책, fallback으로 생성된 route를 서로 다른 절대정보로 남긴다.
- dev/smoke fallback 정책과 Qwen 실사용 strict 정책을 구분한다.
- 휴리스틱을 숨기지 않는다.

## 구현 범위

### 1. RoutingDecision / RoutingDecisionFrame 확장 검토

다음 필드를 추가할지 검토한다.

```text
fallback_after_llm_failure: bool
router_llm_failure_data_id: str | None
router_llm_failure_trace_event_id: str | None
router_llm_failure_type: str | None
fallback_policy: str | None
fallback_allowed_by_runtime_policy: bool
fallback_source_route_rule_id: str | None
```

필드 의미:

- `fallback_after_llm_failure`: 이 route가 LLM 실패 뒤 code fallback으로 생성됐는지.
- `router_llm_failure_data_id`: 실패한 LLM call record의 data id.
- `router_llm_failure_trace_event_id`: 실패한 LLM call trace event id.
- `router_llm_failure_type`: validation failure, adapter failure, timeout 등 실패 종류.
- `fallback_policy`: fallback을 허용한 runtime 정책명.
- `fallback_allowed_by_runtime_policy`: 현재 실행 모드에서 fallback이 명시적으로 허용됐는지.
- `fallback_source_route_rule_id`: fallback으로 실제 route를 만든 code rule id.

### 2. runtime fallback helper 검토

`dry_run.py` 안의 try/except에 직접 필드를 덧칠하기보다, 작은 helper를 둘지 검토한다.

후보:

```text
route_next_with_llm_or_policy_fallback(...)
```

단, helper가 의미 판단을 대신하면 안 된다.
helper는 다음 절대 사실만 묶는다.

```text
LLM router attempt status
LLM failure id/type
fallback policy id
fallback route decision
```

### 3. 정책 구분

dev/smoke에서는 fallback을 허용할 수 있다.
이 경우 routing frame은 반드시 다음을 드러낸다.

```text
llm_routing_status=failed
fallback_after_llm_failure=true
fallback_policy=dev_smoke_router_fallback_allowed
route_source=CODE:RULE_STUB 또는 CODE:POLICY_STUB
```

Qwen 실사용 strict policy는 별도로 정한다.
후보는 다음 중 하나다.

```text
strict_router_fallback=blocked
strict_router_fallback=safe_route_2_with_visible_failure
strict_router_fallback=allow_but_visible
```

이번 MVP에서는 strict policy를 조용히 열지 않는다.
정책 필드와 smoke/dev 경계부터 만든다.

### 4. terminal/runtime 표시

terminal view는 다음 차이를 사람이 읽을 수 있게 보여야 한다.

```text
node_1 router: CODE:RULE_STUB
node_1 router: LLM failed -> CODE:RULE_STUB fallback
node_1 router: LLM ran
```

즉, 최종 `route_source`만 보여주고 끝내지 않는다.

## 감사/수정 후보 파일

```text
songryeon_core/nodes/node_1_router.py
songryeon_core/runtime/dry_run.py
songryeon_core/runtime/user_turn.py
songryeon_core/runtime/terminal_view.py
songryeon_core/runtime/smoke_test.py
songryeon_core/core/schemas.py
```

필요하면 다음 파일도 확인한다.

```text
songryeon_core/prompts/node_1_router_v0.md
```

## Smoke-test 요구

가능하면 다음 검사를 추가한다.

```text
1. node_1 LLM router가 성공하면 fallback_after_llm_failure=false 이고 llm_routing_status=ran 이다.

2. node_1 LLM router가 실패하고 dev/smoke fallback이 허용되면 fallback_after_llm_failure=true 이다.

3. fallback route frame은 실패한 LLM call data id 또는 trace event id를 source로 가진다.

4. fallback route frame은 fallback_policy와 fallback_source_route_rule_id를 가진다.

5. 처음부터 code rule router만 쓴 경우와 LLM 실패 뒤 fallback한 경우가 terminal 출력에서 구분된다.
```

## 금지

- W loop를 열지 않는다.
- R loop를 열지 않는다.
- scheduler 실행 정책을 열지 않는다.
- 외부 DB 또는 장기기억 DB를 만들지 않는다.
- node_4 자동 재작성 루프를 열지 않는다.
- same-turn L reroute 3회차 이상을 열지 않는다.
- fallback을 LLM 판단처럼 보이게 하지 않는다.
- Qwen strict policy에서 silent fallback을 몰래 허용하지 않는다.

## 완료 조건

구현 후 다음 명령이 통과해야 한다.

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
```

완료 보고에는 다음을 적는다.

- LLM router 실패가 어디에 기록되는지.
- code fallback이 어디에서 생성되는지.
- routing frame에서 fallback 전환을 어떤 필드로 확인하는지.
- dev/smoke fallback과 Qwen strict policy가 어떻게 구분되는지.
- terminal view에서 처음부터 code route인 경우와 LLM 실패 뒤 fallback인 경우가 어떻게 구분되는지.
- compileall / smoke-test 결과.
