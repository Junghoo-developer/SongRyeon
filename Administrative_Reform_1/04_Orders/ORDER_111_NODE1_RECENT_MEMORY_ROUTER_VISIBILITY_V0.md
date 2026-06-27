# ORDER_111_NODE1_RECENT_MEMORY_ROUTER_VISIBILITY_V0

## 상태

구현 대상.

## 배경

최근 대화 기억 공급은 다음 단계까지 왔다.

- 0은 최근 raw conversation과 TurnStateCapsule을 대응시킨다.
- memory relevance selector는 후보 raw text를 보고 관련 후보를 고를 수 있다.
- selected recent memory context는 selector가 고른 이전 raw 대화를 요약 없이 복사한다.
- node_2/node_3는 selected recent memory context를 받을 수 있다.

하지만 node_1 router는 라우팅 시점에 selected recent memory context를 충분히 보지 못한다.
그래서 최근 대화 기억으로 바로 답할 수 있는 질문도 route=L로 새어 내부 문서 검색을 시도할 수 있다.

## 목표

node_1 LLM router가 이미 생성된 최근 기억 선택 결과와 selected recent memory context를 볼 수 있게 한다.

이 발주는 장기기억 DB, 요약 기억, W/R loop, scheduler, 외부 DB를 만들지 않는다.

## 구현 범위

1. 첫 라우팅에서 node_1의 source_data_ids에 다음 record를 포함한다.
   - pre-route memory packet
   - memory relevance selection frame
   - selected recent memory context frame

2. node_1 LLM input payload에 최근 기억 라우팅 context를 추가한다.
   - memory_relevance_selection frame
   - selected_recent_memory_context frame
   - selected context count

3. node_1 prompt에 다음 경계를 명시한다.
   - selected recent memory context가 현재 질문을 직접 커버하면 route=2를 선택할 수 있다.
   - 단, node_1이 새로운 관련성 판단을 code처럼 숨기면 안 된다.
   - LLM router는 supplied context를 근거로 자신의 route_reason을 작성한다.
   - 내부 문서/프로젝트 문서 근거가 필요한 요청은 여전히 route=L이다.

4. smoke-test를 추가한다.
   - selector가 이전 raw 대화를 선택한다.
   - selected context가 node_1 router LLM input에 들어간다.
   - node_1 router가 selected recent memory context를 근거로 route=2를 낼 수 있다.
   - route frame source_data_ids에 selection/context record가 남는다.

## 금지

- 코드 keyword heuristic으로 최근 기억 질문을 route=2로 강제하지 않는다.
- selector 없이 node_1이 raw 8턴 전체를 독자 선택하게 만들지 않는다.
- node_4 guard를 약화하지 않는다.
- L reroute 횟수, W/R loop, scheduler, 외부 DB, 장기기억 요약을 건드리지 않는다.

## 완료 조건

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
```

추가 smoke 기대값:

- `node1_recent_memory_router_visibility_route=2`
- `node1_recent_memory_router_visibility_context_seen=True`
- `node1_recent_memory_router_visibility_source_ids=True`
