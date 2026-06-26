# TMP ORDER 019: Node 1 Routing Decision Payload Store

## 목표

1 상황판단 라우터의 route 결정도 DataStore payload로 저장한다.

## 배경

현재 `route:L`, `route:2`는 trace output_ref로 남지만, 라우팅 결정의 본체는 DataStore에 없다.

## 범위

1. `RoutingDecisionFrame` 스키마를 만든다.
2. `frame_id`, `turn_id`, `route`, `expected_next_0_mode`, `required_schema`, `source_trace_ids`, `source_data_ids`를 둔다.
3. `record_routing()`이 DataStore에 payload를 저장하게 한다.
4. 0이 라우팅 이후 호출될 때 해당 route frame을 source data로 받을 수 있게 한다.

## 완료 기준

- `route:L`, `route:2`가 DataStore record로 저장된다.
- 0의 다음 memory packet source data에 직전 route frame이 연결된다.
- 기존 trace_count는 필요 이상으로 늘리지 않는다.

## 제외

- 라우팅 이유 자연어 생성.
- LLM 라우터 연결.
