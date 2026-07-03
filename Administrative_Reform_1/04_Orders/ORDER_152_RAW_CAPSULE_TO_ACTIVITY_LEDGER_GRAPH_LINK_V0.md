# ORDER 152: Raw Capsule To Activity Ledger Graph Link v0

## 1. Goal

`graph:raw_capsule:{turn_id}`가 같은 턴의 L/R 활동 장부를 graph-memory 표면에서 찾을 수 있게 만든다.

ORDER_151까지는 L/R 활동 장부가 DataStore record로 존재하지만, raw capsule graph node와 graph node/edge로 직접 연결되지는 않았다.
이번 MVP는 활동 장부를 의미 요약하지 않고, code-generated graph node/edge와 link frame으로만 연결한다.

## 2. Scope

추가한다.

- `activity_ledger` graph node kind
- `HAS_ACTIVITY_LEDGER` graph edge kind
- `TurnActivityGraphLinkFrame`
- `record_turn_activity_graph_links()`
- dry-run 배선
- runtime/smoke/pytest 검증

열지 않는다.

- 외부 DB/Neo4j 연결
- summary layer
- L/R 의미 판단
- R live route 확장
- raw capsule payload 재작성
- node_3 답변 주입

## 3. Graph Shape

```text
graph:raw_capsule:{turn_id}
  -[HAS_ACTIVITY_LEDGER]->
graph:activity_ledger:{ledger_data_id}
```

`activity_ledger` node는 원본 활동 장부 DataStore record를 graph-memory에서 찾기 위한 좌표 노드다.
LLM 요약이나 중요도 판단을 담지 않는다.

## 4. Link Frame

`TurnActivityGraphLinkFrame`

- `frame_id`
- `turn_id`
- `turn_capsule_graph_node_id`
- `l_loop_activity_ledger_data_ids`
- `r_graph_access_ledger_data_ids`
- `activity_ledger_graph_node_ids`
- `activity_ledger_graph_edge_ids`
- `link_records`
- `source_trace_ids`
- `source_data_ids`
- `generated_by=CODE:TURN_ACTIVITY_GRAPH_LINK_BUILDER`
- `info_class=absolute`
- `semantic_judgement_status=not_run`

`link_records`는 다음 값만 담는다.

- `activity_kind`
- `ledger_data_id`
- `graph_node_id`
- `edge_id`
- `source_field`

## 5. Rules

- code는 기존 L/R ledger record의 존재와 ID만 복사한다.
- code는 어떤 ledger가 더 중요한지 판단하지 않는다.
- raw capsule node와 ledger node 사이 edge는 결정론적 ID를 가진다.
- 같은 payload를 재기록하면 중복 생성하지 않는다.
- link frame count는 list 길이와 일치해야 한다.

## 6. Test Plan

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_152_raw_capsule_activity_graph_link.py
python -m pytest
python main.py smoke-test
git diff --check
```

## 7. Done Criteria

- dry turn에서 `graph:turn_activity_graph_link:{turn_id}`가 기록된다.
- L ledger용 `activity_ledger` graph node가 기록된다.
- R dry-run이 켜진 경우 R access ledger용 `activity_ledger` graph node도 기록된다.
- `HAS_ACTIVITY_LEDGER` edge가 raw capsule node에서 activity ledger node로 이어진다.
- 모든 새 frame/node/edge는 `info_class=absolute`, `semantic_judgement_status=not_run`을 지킨다.
