# ORDER 148: Graph NEXT And Turn Access Ledger v0

## 1. Goal

`TurnStateCapsule` 기반 graph memory에서 시간순 raw capsule 탐색과 R 루프 graph 열람 이력 추적을 작게 잠근다.

이번 발주는 두 가지를 한다.

1. 시간순으로 인접한 `raw_capsule` graph node 사이에 `NEXT` edge를 만든다.
2. R skeleton이 어떤 graph node를 후보로 보고, 선택하고, 검사했는지를 `TurnGraphAccessLedgerFrame`으로 남긴다.

## 2. Background

ORDER_139 이후 Core에는 다음 구조가 있다.

```text
graph:core_ego:root
  -> graph:axis:time
      -> graph:time_bundle:{batch_id}
          -> graph:raw_capsule:{turn_id}
```

하지만 raw capsule끼리 시간순으로 바로 이어지지 않아, 인접 턴을 볼 때 상위 time bundle을 거쳐 다시 내려가야 한다.

또한 ORDER_140~147 이후 R skeleton에는 graph node 선택/검사 결과가 생겼지만, 해당 턴이 어떤 graph node를 보았는지 본점의 `used_sources`/`REFERENCES_MEMO` 같은 장부로 승격되지는 않았다.

## 3. Scope

### 3.1 NEXT edge

- `GraphMemoryEdgeFrame.edge_kind`에 `NEXT`를 추가한다.
- `build_graph_memory_snapshot_from_capsules()`는 dedupe된 capsule 입력 순서 기준으로 인접 raw capsule node를 `NEXT` edge로 연결한다.
- `NEXT`는 의미 판단이 아니라 입력 순서와 `turn_id` 좌표에 근거한 절대정보다.
- raw 원본이나 capsule payload는 변경하지 않는다.

### 3.2 Turn graph access ledger

새 schema를 추가한다.

```text
TurnGraphAccessLedgerFrame
```

최소 필드:

- `frame_id`
- `turn_id`
- `turn_capsule_graph_node_id`
- `candidate_graph_node_ids`
- `selected_graph_node_ids`
- `inspected_graph_node_ids`
- `read_graph_node_ids`
- `used_as_answer_source_graph_node_ids`
- `access_records`
- `source_trace_ids`
- `source_data_ids`
- `generated_by=CODE:GRAPH_ACCESS_LEDGER`
- `info_class=absolute`
- `semantic_judgement_status=not_run`

이번 MVP에서 `read_graph_node_ids`와 `used_as_answer_source_graph_node_ids`는 빈 배열일 수 있다. 아직 R route 결과가 최종 답변 근거로 쓰이는 단계가 아니기 때문이다.

### 3.3 R skeleton connection

- `run_r_loop_dry_run_skeleton()`이 R2/R3/return summary 결과에서 ledger를 생성한다.
- ledger는 DataStore에 `graph_memory:turn_access_ledger_frame`로 기록한다.
- ledger는 code가 이미 가진 graph node id를 복사할 뿐, 관련성/중요도/정답성을 판단하지 않는다.

## 4. Non-goals

- 외부 DB/Neo4j 연결을 열지 않는다.
- 의미축 graph node를 만들지 않는다.
- R1/R2/R3 LLM 판단을 새로 열지 않는다.
- live R route 정책을 확장하지 않는다.
- node_3 최종 답변에 R 결과를 새로 주입하지 않는다.
- graph node 원문 요약이나 기억 요약을 만들지 않는다.

## 5. Test Plan

필수 검증:

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

추가 pytest:

- raw capsule 3개를 graph memory로 만들면 `NEXT` edge 2개가 생긴다.
- `NEXT` edge는 dedupe된 capsule 순서를 따른다.
- `TurnGraphAccessLedgerFrame`은 `generated_by=CODE:GRAPH_ACCESS_LEDGER`, `info_class=absolute`, `semantic_judgement_status=not_run`을 지킨다.
- R dry-run skeleton은 selected/inspected/source graph node id를 ledger에 보존한다.
- ledger는 의미 판단 텍스트를 만들지 않는다.

## 6. Completion Report Must Include

- `NEXT` edge가 어디서 생성되는지
- `TurnGraphAccessLedgerFrame`이 어디서 생성/기록되는지
- 어떤 값이 후보/선택/검사 graph node로 들어가는지
- 아직 하지 않은 것
- compileall / pytest / smoke-test 결과
