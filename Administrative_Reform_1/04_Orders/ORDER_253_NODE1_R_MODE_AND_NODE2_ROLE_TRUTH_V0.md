# ORDER 253: Node1 R Mode And Node2 Role Truth v0

## 상태

승인 및 구현 진행.

## 배경

현재 node_1의 route capability card는 route `R`이 열렸다는 사실만 보고,
실제 실행이 다음 중 어느 것인지 구분하지 않는다.

```text
vessel_live: Neo4j read packet과 R1/R2/R3를 실행하는 현장 R
capsule_skeleton: 최근 TurnStateCapsule로 만든 결정론적 실험 R
```

그 결과 capsule skeleton만 열린 경우에도 node_1은 Vessel/Neo4j와 RawSource 원문을
탐색할 수 있다고 설명받을 수 있다. 또한 route `2` capability card는 node_2가
부족한 근거를 복구하거나 보고를 차단하지 않는다는 실제 한계를 충분히 밝히지 않는다.

## 목표

1. node_1 입력에 현재 R 실행 모드를 절대정보로 명시한다.
2. R capability card의 설명과 첫 node_0 mode를 실제 실행 모드에 맞춘다.
3. node_2를 근거 복구/차단 노드로 과장하지 않고 종착 정리 단계로 설명한다.

## 구현 범위

### R 실행 모드

```text
vessel_live
capsule_skeleton
```

- `vessel_live`의 첫 node_0 mode는 `vessel_r_read_packet`이다.
- `capsule_skeleton`의 첫 node_0 mode는 `r_loop_graph_guide_handoff`다.
- RoutingDecision과 RoutingDecisionFrame에 선택 당시 실행 모드를 보존한다.
- route `L`과 `2`에는 R 실행 모드를 기록하지 않는다.

### node_2 역할 설명

node_1의 route `2` card에 다음 사실을 명시한다.

- node_2는 이미 공급된 근거를 절대/상대/혼합 정보로 정리한다.
- node_2는 답변 근거 자세를 선택하고 node_3용 brief를 만든다.
- node_2는 새 문서/코드/그래프를 조회하지 않는다.
- node_2는 부족한 근거를 L/R로 복구하지 않는다.
- node_2의 status만으로 node_3 실행을 차단하지 않는다.
- 따라서 route `2`는 필요한 근거가 이미 공급됐을 때만 선택해야 한다.

## 금지

- R 복귀 후 node_1 재판정 루프를 열지 않는다.
- node_2에 새 차단 권한이나 재라우팅 권한을 부여하지 않는다.
- L 성공 판정과 검색 정책을 바꾸지 않는다.
- R1/R2/R3 탐색 의미나 예산을 바꾸지 않는다.
- 휴리스틱을 추가하지 않는다.

## 검증

1. vessel live card와 capsule skeleton card가 서로 다른 능력과 첫 mode를 표시한다.
2. RoutingDecisionFrame이 R 실행 모드와 first node_0 mode의 불일치를 거부한다.
3. route `2` card가 node_2의 비차단/비복구 성질을 명시한다.
4. 기존 experimental skeleton과 Vessel live 회귀시험이 유지된다.
5. `python -m compileall songryeon_core main.py`
6. `python -m pytest`
7. `python main.py smoke-test`

