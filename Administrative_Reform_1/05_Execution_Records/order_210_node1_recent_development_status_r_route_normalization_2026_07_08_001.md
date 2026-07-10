# order_210_node1_recent_development_status_r_route_normalization_2026_07_08_001

## 작업 범위

ORDER_210 Node1 Recent Development Status R Route Normalization을 구현했다.

목표는 node_1이 "최근 발주서 기준 현재 개발 상태 브리핑" 요청을 무조건 L 문서 검색으로 보내지 않고, R route가 활성화되어 있고 사용자가 이미 적재된 Vessel graph memory의 프로젝트 흐름을 보려는 경우 R을 선택할 수 있게 하는 것이다.

## 구현 내용

- `songryeon_core/nodes/node_1_router.py`
  - R route capability card의 `best_for`에 다음 근거 표면을 추가했다.
    - 이미 적재된 Vessel graph memory 기반 현재/최근 개발 상태 브리핑
    - 최근 발주서 또는 구현 타임라인 브리핑
  - L route capability card의 `not_for`에 이미 적재된 graph memory 기반 개발 상태 브리핑을 추가했다.
  - R route의 `not_for`에 아직 graph memory에 적재됐다고 볼 수 없는 최신 파일/발주서 원문 읽기 요청을 추가했다.

- `songryeon_core/prompts/node_1_router_v0.md`
  - R이 적합한 경우를 "이미 Vessel graph memory에 적재된 개발 흐름을 보려는 요청"으로 보강했다.
  - L이 적합한 경우를 "새 원문/정확한 파일/아직 적재되지 않았을 수 있는 자료를 읽어야 하는 요청"으로 보강했다.

- `tests/test_order_210_node1_recent_development_status_r_route.py`
  - R card가 최근/현재 개발 상태 브리핑을 graph memory 근거 표면으로 설명하는지 검증했다.
  - L card가 새 원문 검색과 이미 적재된 graph memory briefing을 구분하는지 검증했다.
  - prompt가 keyword rule이 아니라 evidence surface 비교를 유지하는지 검증했다.

- `Administrative_Reform_1/04_Orders/ORDER_210_NODE1_RECENT_DEVELOPMENT_STATUS_R_ROUTE_NORMALIZATION_V0.md`
  - 발주서를 추가했다.

- `Administrative_Reform_1/04_Orders/README.md`
  - ORDER_210 등록 및 현재 정식 발주서 범위를 갱신했다.

## 일부러 하지 않은 것

- code keyword heuristic 추가 없음.
- code가 사용자 질문을 보고 R을 강제하는 의미 판단 없음.
- node_1 validator 약화 없음.
- R1/R2/R3 traversal 변경 없음.
- L loop 검색/읽기 정책 변경 없음.
- node_3/node_4 guard 변경 없음.

## 검증

```powershell
python -m compileall songryeon_core\nodes\node_1_router.py
python -m pytest tests\test_order_204_node1_route_capability_cards.py tests\test_order_210_node1_recent_development_status_r_route.py -q
```

결과:

- compileall 통과
- pytest 6 passed

## live qwen 확인

다음 명령으로 live 확인을 수행했다.

```powershell
python main.py qwen-turn "최근 발주서를 기준으로 지금 송련 Core가 어디까지 개발됐는지 브리핑해줘" --timeout 180 --pretty --enable-vessel-r-route --database neo4j
```

확인된 절대정보:

- `route sequence=['R', '2']`
- `policy_flags=['enable_r_route_experimental']`
- `L_runs=0`
- `R_handoff_status=available`
- `R_vessel_ledgers=1`

따라서 ORDER_210의 직접 목표인 "node_1이 R route를 선택할 수 있게 하는 정상화"는 live에서 확인됐다.

## 새로 드러난 병목

같은 live 실행에서 node_3 brief의 Vessel R material은 다음처럼 기록됐다.

- `node3_vessel_status=failed`
- `node3_vessel_items=0`
- `node3_vessel_task=failed`

즉, 이제 1번의 R 선택 문제는 개선됐지만, R traversal 결과가 node_3에게 유효한 graph material로 전달되는 단계에는 별도 감사가 필요하다.
