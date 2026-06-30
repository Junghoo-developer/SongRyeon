# ORDER_145_R_LOOP_PRE_LIVE_ROUTE_AUDIT_BASELINE_V0

## Status

구현 완료.

실행 기록:

- `Administrative_Reform_1/05_Execution_Records/order_145_r_loop_pre_live_route_audit_baseline_2026_07_01_001.md`

## 1. 목표

ORDER_139~144로 만들어진 graph memory/R loop 골격이 아직 live route가 아니라는 사실을 감사하고 테스트 기준선으로 잠근다.

핵심:

```text
R은 지금 dry-run opt-in skeleton이다.
qwen-chat/live node_1 route=R은 아직 열지 않는다.
```

## 2. 현재 코드 사실

- `RoutingDecisionFrame` validator는 route를 `L` 또는 `2`로만 허용한다.
- node_1 LLM router payload도 route를 `L` 또는 `2`로만 허용한다.
- `run_dry_turn()` 기본값은 `enable_r_route_dry_run=False`다.
- `enable_r_route_dry_run=True`일 때만 deterministic R1/R2/R3/budget/continuation/return summary frame이 생성된다.
- R dry-run frame은 `generated_by=CODE:R_LOOP_DRY_RUN_ONLY`, `semantic_judgement_status=not_run`으로 닫혀 있다.
- R1/R2/R3 placeholder frame은 아직 LLM 판단을 실행하지 않은 `mixed/not_run`이다.
- R budget/continuation/return summary 같은 code control frame은 `absolute/not_run`이다.
- R output은 node_1 routing decision이나 node_3 final report source로 자동 주입되지 않는다.

## 3. 감사 질문

1. 현재 node_1이 live route=R을 선택할 수 있는가?
2. R dry-run skeleton이 기본 턴에서 몰래 실행되는가?
3. R dry-run output이 node_1/node_3 근거로 섞이는가?
4. R frame이 LLM 판단이나 graph DB 진실처럼 보이는가?
5. 다음 단계에서 live R route를 열기 전에 어떤 경계가 남아 있는가?

## 4. 이번 작업 범위

- ORDER_145 문서화.
- R pre-live boundary 전용 pytest 추가.
- 실행 기록 추가.
- `04_Orders/README.md`, `05_Execution_Records/README.md` 갱신.

## 5. 금지

- node_1 route set에 `R`을 추가하지 않는다.
- qwen-chat/live runtime에서 R route를 실행하지 않는다.
- R1/R2/R3 LLM prompt를 새로 만들지 않는다.
- node_3 final answer에 R 결과를 주입하지 않는다.
- external DB/Neo4j 연결을 열지 않는다.
- semantic axis graph를 만들지 않는다.
- code가 graph 의미 판단을 대신 생성하지 않는다.

## 6. 테스트 기준

1. `RoutingDecisionFrame(route="R")`는 validator에서 실패해야 한다.
2. node_1 LLM router payload가 `route="R"`을 내면 실패해야 한다.
3. 기본 `run_dry_turn()`은 R dry-run output을 만들지 않아야 한다.
4. `run_dry_turn(enable_r_route_dry_run=True)`에서만 R dry-run output이 생겨야 한다.
5. R dry-run output은 `CODE:R_LOOP_DRY_RUN_ONLY` / `not_run`이어야 한다.
6. R budget/continuation/return summary control frame은 `absolute/not_run`이어야 한다.
7. R dry-run output은 node_1 routing decision 또는 node_3 report의 `source_data_ids`에 섞이지 않아야 한다.

## 7. 완료 조건

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
git diff --check
```

## 8. 다음 후보

ORDER_145 이후 live R route를 열려면 먼저 별도 발주서에서 다음을 정해야 한다.

- node_1이 어떤 조건에서 route=R을 허용할지
- R route가 node_3 답변에 언제, 어떤 형태로 연결될지
- R1/R2/R3가 LLM 판단을 할 때 상대/혼합정보를 어떻게 기록할지
- R loop 실패/부분성공을 node_3 태도에 어떻게 전달할지
