# ORDER 253 실행 기록: node_1 R 모드와 node_2 역할 정직성

## 결과

구현 및 검증 완료.

## 구현 내용

### 1. R 실행 모드 분리

node_1 route capability input과 RoutingDecision/Frame에 다음 절대 모드를 추가했다.

```text
vessel_live
capsule_skeleton
```

모드별 실제 첫 node_0 동선:

```text
vessel_live -> vessel_r_read_packet
capsule_skeleton -> r_loop_graph_guide_handoff
```

RoutingDecisionFrame validator는 R 실행 모드와 첫 node_0 mode가 어긋나면 실패한다.
route L/2가 R 실행 모드를 기록하는 것도 실패한다.

기존 `allow_r_route_experimental=True`만 사용하는 호출은 호환을 위해
`capsule_skeleton`으로 해석한다. 현장 Vessel R 배선은 `dry_run`이
`vessel_live`를 명시적으로 전달한다. 강제 Vessel R도 `vessel_live`로 기록한다.

### 2. node_2 역할 설명 정정

node_1의 route 2 capability card와 prompt에 다음 경계를 추가했다.

- node_2는 공급된 절대/상대/혼합 정보를 분류한다.
- node_2는 답변 근거 자세를 선택하고 node_3 brief를 조립한다.
- node_2는 새 문서/코드/Vessel 근거를 가져오지 않는다.
- node_2는 부족한 근거를 L/R로 되돌려 복구하지 않는다.
- 현재 runtime에서 node_2 status만으로 node_3 실행을 차단하지 않는다.
- 따라서 route 2는 필요한 근거가 이미 공급됐을 때만 선택해야 한다.

## 변경 파일

- `Administrative_Reform_1/04_Orders/ORDER_253_NODE1_R_MODE_AND_NODE2_ROLE_TRUTH_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`
- `songryeon_core/core/schema_parts/trace_data.py`
- `songryeon_core/core/schemas.py`
- `songryeon_core/nodes/node_1_router.py`
- `songryeon_core/prompts/node_1_router_v0.md`
- `songryeon_core/runtime/dry_run.py`
- `tests/test_order_146_r_route_experimental_gate.py`
- `tests/test_order_200_vessel_r_live_gated_integration.py`
- `tests/test_order_204_node1_route_capability_cards.py`
- `tests/test_order_210_node1_recent_development_status_r_route.py`
- `tests/test_order_243_autonomous_r_route_reality_and_downstream_honesty.py`
- `tests/test_order_253_node1_r_mode_and_node2_role_truth.py`

## 검증

```text
python -m compileall songryeon_core main.py
passed

집중 회귀시험
25 passed in 16.30s

python -m pytest
429 passed, 5 deselected in 77.18s

python main.py smoke-test
SMOKE_TEST_OK

git diff --check
passed
```

## 일부러 하지 않은 것

- R 종료 뒤 node_1 LLM 재판정 없음
- R 실패/partial 뒤 L 자동 전환 없음
- node_2 차단 권한 또는 재라우팅 권한 추가 없음
- L 후보/원문 성공 판정 변경 없음
- R1/R2/R3 탐색 예산과 의미 변경 없음
- 휴리스틱 추가 없음

## 남은 경계

node_1은 이제 선택 전에 실제 R 구현 종류와 node_2의 비복구 성질을 볼 수 있다.
그러나 R 결과가 실패/partial일 때 어느 경로로 복구할지는 여전히 별도 설계 대상이다.

