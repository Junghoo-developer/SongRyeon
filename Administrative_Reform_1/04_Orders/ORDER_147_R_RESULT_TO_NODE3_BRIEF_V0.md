# ORDER_147_R_RESULT_TO_NODE3_BRIEF_V0

## Status

구현 완료.

실행 기록:

- `Administrative_Reform_1/05_Execution_Records/order_147_r_result_to_node3_brief_2026_07_01_001.md`

## 1. 목표

ORDER_146의 experimental R route skeleton 결과를 node_3 input brief에 구조화해서 전달한다.

핵심:

```text
R route skeleton이 실행됐다는 절대 장부는 node_3가 볼 수 있게 한다.
하지만 node_3가 이를 완전한 graph memory 탐색 성공으로 말하지 못하게 한다.
```

## 2. 구현 범위

- `Node3RLoopResultMaterial`을 추가한다.
- `Node3InputBriefFrame.r_loop_result_material`에 최신 `R:experimental:return_summary_frame` 요약을 복사한다.
- node_3 LLM payload에 safe R result summary를 넣는다.
- node_3 grounding block에 R 탐색 실험 상태를 표시한다.
- runtime terminal view가 node_3 brief 안의 R result material을 표시한다.
- node_3 prompt에 R skeleton/partial 결과의 사용자-facing 경계를 추가한다.

## 3. 메타정보 경계

- R return summary material은 code가 DataStore record에서 복사한 절대 상태 장부다.
- `generated_by=CODE:R_ROUTE_EXPERIMENTAL_GATE`
- `info_class=absolute`
- `semantic_judgement_status=not_run`
- `attitude_hint`는 skeleton/partial 결과를 성공처럼 말하지 않게 하는 표시다.

## 4. 금지

- R1/R2/R3 LLM node를 열지 않는다.
- R loop 자동 반복을 열지 않는다.
- external DB/Neo4j 연결을 열지 않는다.
- 의미축 graph node를 만들지 않는다.
- node_3가 R skeleton을 완전한 장기기억 탐색 성공으로 표현하게 하지 않는다.
- code가 R 결과의 의미 판단을 대신 만들지 않는다.

## 5. 테스트 기준

1. experimental R route가 실행되면 node_3 input brief에 `r_loop_result_material`이 들어간다.
2. 해당 material의 source data id는 `R:experimental:return_summary_frame`이다.
3. material은 `generated_by=CODE:R_ROUTE_EXPERIMENTAL_GATE`, `info_class=absolute`, `semantic_judgement_status=not_run`을 유지한다.
4. node_3 grounding block은 R 탐색 실험 상태와 한계를 표시한다.
5. node_3 LLM payload는 raw internal ID 대신 safe boundary만 제공한다.
6. terminal은 node_3 brief 안의 R result material을 표시한다.

## 6. 완료 조건

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
git diff --check
```

## 7. 다음 후보

ORDER_148에서는 다음 중 하나를 결재한다.

- R live test pack 작성
- R1/R2/R3 frame-only state machine 실제 구현
- R result를 node_0 memory packet으로 회수하는 handoff
