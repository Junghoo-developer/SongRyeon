# ORDER_146_R_ROUTE_EXPERIMENTAL_GATE_AND_ALLOWED_ROUTE_SET_V0

## Status

구현 완료.

실행 기록:

- `Administrative_Reform_1/05_Execution_Records/order_146_r_route_experimental_gate_2026_07_01_001.md`

## 1. 목표

ORDER_145 기준선 위에서 live R route를 바로 일반 개방하지 않고, 명시 실험 플래그 뒤에서만 node_1 LLM이 `route=R`을 고를 수 있게 한다.

핵심:

```text
기본 route set은 L/2 유지.
--enable-r-route-experimental이 있을 때만 allowed_routes에 R 추가.
code는 R을 의미적으로 고르지 않는다.
R 선택은 node_1 LLM decision으로만 기록한다.
```

## 2. 구현 범위

- node_1 LLM router input payload의 `allowed_routes`를 조건부로 확장한다.
- `RoutingDecisionFrame(route="R")`는 다음 조건을 모두 만족할 때만 통과한다.
  - `policy_flag=enable_r_route_experimental`
  - `route_source=LLM:*`
  - `llm_routing_status=ran`
  - `route_rule_id=llm_router`
  - `expected_next_0_mode=r_loop_graph_guide_handoff`
- `run_dry_turn(..., enable_r_route_experimental=True)`에서 node_1이 R을 고르면 experimental R skeleton을 실행한다.
- R experimental skeleton은 `R:experimental:*` ID와 `generated_by=CODE:R_ROUTE_EXPERIMENTAL_GATE`로 기록한다.
- R experimental skeleton 이후에는 code가 `route=2`로 닫아 node_2/node_3 경계로 보낸다.
- CLI에는 `--enable-r-route-experimental` 플래그를 추가한다.

## 3. 메타정보 경계

- R route 선택 자체는 node_1 LLM 판단이다.
- R route 허용 여부는 code 정책이다.
- R skeleton 실행 frame은 code-generated 구조 점검이다.
- R skeleton의 R1/R2/R3 placeholder는 아직 `semantic_judgement_status=not_run`이다.
- R budget/continuation/return summary는 code가 확인 가능한 제어 장부다.

## 4. 금지

- 기본 qwen-chat에서 route=R을 열지 않는다.
- 키워드/휴리스틱으로 code가 R을 고르지 않는다.
- R1/R2/R3 LLM prompt를 새로 만들지 않는다.
- external DB/Neo4j 연결을 열지 않는다.
- semantic graph axis를 만들지 않는다.
- node_3가 R 결과를 완전한 장기기억 탐색 성공으로 말하게 하지 않는다.

## 5. 테스트 기준

1. 실험 플래그가 없으면 node_1 LLM payload `route=R`은 실패하거나 fallback으로 닫힌다.
2. 실험 플래그가 있으면 `allowed_routes`에 R이 들어가고 `route=R` payload가 통과한다.
3. `RoutingDecisionFrame(route=R)`은 policy flag/LLM source/R handoff mode 없이는 실패한다.
4. experimental R이 실행되면 `route:R -> R:experimental:* -> route:2`로 닫힌다.
5. terminal은 dry-run R과 experimental R을 구분해서 표시한다.

## 6. 완료 조건

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
git diff --check
```

## 7. 다음 후보

ORDER_147에서는 다음 중 하나를 결재해야 한다.

- R1/R2/R3 LLM화를 시작할지
- R return summary를 node_3 brief에 구조화해 전달할지
- R route live test pack을 먼저 만들지
