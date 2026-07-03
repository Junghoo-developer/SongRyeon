# ORDER 153: Graph Memory Export Integrity Audit And R Experimental Source Recording v0

## 1. Goal

외부 graph DB/Neo4j/Vessel 연결 전에 graph-memory DataStore 기록의 참조 무결성을 잠근다.

이번 발주는 외부 DB 연결이 아니라, 외부 DB로 내보내기 전에 다음 두 가지를 보장하는 좁은 MVP다.

1. R experimental route가 참조하는 graph snapshot/guide/node/edge 좌표가 DataStore에 실제 record로 남는다.
2. graph/rloop source reference가 DataStore 안에서 dangling 상태인지 검사하는 read-only audit helper가 생긴다.

## 2. Background

ORDER_152 감사에서 다음 문제가 확인됐다.

```text
run_dry_turn(..., enable_r_route_experimental=True)
r_route_experimental_graph_data_ids=[]
missing_graph_or_rloop_count=14
```

즉 R experimental branch는 `build_graph_memory_snapshot_from_capsules(...)`로 graph frame을 메모리에서 만들지만, 그 snapshot/guide/node/edge를 DataStore record로 보존하지 않은 채 R handoff와 R ledger source로 인용한다.

이는 외부 DB export 전에 위험하다.

## 3. Scope

### 3.1 R experimental source recording

- `decision.route == "R"` experimental branch에서 R handoff 전에 graph source records를 DataStore에 기록한다.
- 고정 ID인 `graph:core_ego:root`, `graph:axis:time`, root->axis shared edge는 final turn graph recording과 payload 충돌 가능성이 있으므로 직접 재기록하지 않는다.
- batch-specific snapshot/guide/time_bundle/raw/edge records는 기록한다.
- 기록된 graph data ids를 `r_route_experimental_graph_data_ids`와 node movement output에 반영한다.

### 3.2 Integrity audit helper

- DataStore를 읽어서 graph/rloop source reference가 missing인지 검사한다.
- code는 누락을 자동 보정하지 않는다.
- helper는 read-only다.
- 검사 대상은 최소한 다음이다.
  - graph/rloop prefix를 가진 `source_data_ids`
  - `graph_memory:edge:*`의 `from_node_id`, `to_node_id`

### 3.3 Tests

- ORDER_152 감사에서 재현된 R experimental dangling graph refs가 사라졌는지 확인한다.
- 일부러 missing graph/rloop ref를 가진 DataStore를 만들면 audit helper가 보고하는지 확인한다.
- default dry-run graph integrity가 pass인지 확인한다.

## 4. Non-goals

이번 발주는 다음을 열지 않는다.

- Neo4j/Vessel 실제 연결
- graph DB export 실행
- semantic axis
- R LLM selector
- R live route 확대
- R traversal이 `HAS_ACTIVITY_LEDGER`를 따라가는 기능
- L/R summary generation
- node_3 답변 주입 변경

## 5. Test Plan

Required commands:

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_153_graph_memory_integrity.py
python -m pytest
python main.py smoke-test
git diff --check
```

## 6. Completion Report Must Include

- R experimental dangling source ref가 어떻게 사라졌는지
- integrity audit helper가 무엇을 검사하는지
- 외부 DB/Neo4j를 아직 열지 않았는지
- compileall / pytest / smoke-test 결과
