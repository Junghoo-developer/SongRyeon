# ORDER_210_NODE1_RECENT_DEVELOPMENT_STATUS_R_ROUTE_NORMALIZATION_V0

## 상태

즉시 구현 승인.

## 배경

live 테스트에서 사용자가 "최근 발주서를 기준으로 지금 송련 Core가 어디까지 개발됐는지 브리핑해줘"라고 물었을 때, `--enable-vessel-r-route`가 켜져 있었고 R handoff도 준비되어 있었지만 node_1은 `L`을 선택했다.

runtime 감사판 기준으로 확인된 사실은 다음과 같다.

1. `R_handoff_status=available`
2. `R_vessel_ledgers=0`
3. route sequence가 `['L', 'L', '2']`
4. L loop는 문서를 읽었지만 최종 답변은 사용자의 "개발 상태 브리핑" 목표에 충분히 맞지 않았다.

이는 R route 자체가 없는 문제가 아니라, node_1이 "최근/현재 개발 상태를 이미 적재된 Vessel graph memory에서 되짚는 일"을 R route의 담당으로 충분히 보지 못한 문제로 본다.

## 목표

node_1이 L/R/2를 고를 때 보는 `route_capability_cards`와 prompt 경계를 보강한다.

특히 R route가 활성화되어 있을 때, 다음 요청은 R의 주요 후보임을 명시한다.

1. 이미 Vessel/Neo4j graph memory에 적재된 프로젝트 개발 흐름을 되짚는 요청.
2. 최근 발주서, 최근 구현 흐름, 현재 개발 상태를 시간축/요약 계층에서 브리핑하는 요청.
3. graph memory가 가진 CoreEgo/time-axis/source-bundle/summary-layer 자료를 따라가야 하는 요청.

## 원칙

1. code가 사용자 문장을 보고 의미적으로 R을 강제하지 않는다.
2. keyword heuristic을 추가하지 않는다.
3. `allowed_routes`는 계속 hard guard다.
4. R card는 `allow_r_route_experimental=True`일 때만 payload에 들어간다.
5. L route는 여전히 새 문서/코드/아티팩트 원문 검색이 필요한 경우 담당한다.
6. `--force-vessel-r-route` 명시 정책은 기존처럼 유지한다.

## 구현 범위

1. `node_1_router.py`
   - R route capability card의 `best_for`에 이미 적재된 프로젝트 개발 흐름/최근 발주서/현재 개발 상태 브리핑을 추가한다.
   - L route capability card의 `not_for`에 이미 적재된 개발 상태 브리핑은 R이 더 적합하다는 경계를 추가한다.
   - route selection policy에 code semantic routing이 `not_run`임을 유지한다.

2. `node_1_router_v0.md`
   - R route와 L route의 차이를 더 자연스럽게 설명한다.
   - "최근/현재 개발 상태"가 무조건 R이라는 규칙이 아니라, 이미 Vessel graph memory에 적재된 흐름을 보려는 요청일 때 R이 적합하다고 적는다.

3. 테스트
   - R card가 recent/current development status briefing을 R evidence surface로 설명하는지 확인한다.
   - L card가 새 원문 검색과 이미 적재된 graph memory briefing을 구분하는지 확인한다.
   - prompt가 keyword rule이 아니라 evidence surface 비교를 요구하는지 유지한다.

## 금지

1. hidden keyword routing 추가 금지.
2. code 의미 판단 fallback 추가 금지.
3. node_1 validator 약화 금지.
4. R1/R2/R3 traversal 변경 금지.
5. L loop read/search 정책 변경 금지.
6. node_3/node_4 guard 변경 금지.

## 완료 조건

1. `python -m compileall songryeon_core/nodes/node_1_router.py`
2. `python -m pytest tests/test_order_204_node1_route_capability_cards.py tests/test_order_210_node1_recent_development_status_r_route.py -q`

## 후속 확인

구현 후 live qwen 테스트에서 다음 질문을 다시 확인한다.

```powershell
python main.py qwen-turn "최근 발주서를 기준으로 지금 송련 Core가 어디까지 개발됐는지 브리핑해줘" --timeout 180 --pretty --enable-vessel-r-route --database neo4j
```

기대는 node_1이 code 강제 없이 `R`을 더 자연스럽게 선택하는 것이다.
