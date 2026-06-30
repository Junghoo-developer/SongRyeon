# ORDER_139_GRAPH_MEMORY_FOUNDATION_AND_RLOOP_GUIDE_PACKET_V0

## 1. 목표

심야정부/R루프 구현의 첫 삽을 뜬다.

이번 발주는 완성된 외부 그래프 DB나 완성된 R루프가 아니다.

목표는 더 작다.

```text
TurnStateCapsule/TraceStore/DataStore 기반 raw graph node 문법을 만들고,
CoreEgo 시간축 entry를 구성하고,
R루프가 나중에 읽을 RLoopGraphGuidePacket을 생성한다.
```

즉 이번 작업의 성공은 "송련이 장기기억을 완성했다"가 아니라 다음이다.

```text
기존 capsule/trace/data 좌표를 잃지 않고 graph memory foundation으로 올릴 수 있다.
CoreEgo 직속 연결은 시간축만 쓴다.
R루프용 graph guide packet이 생성되고 provenance가 남는다.
```

## 2. 반드시 먼저 읽을 문서

구현 전 아래 문서를 읽고 시작한다.

1. `AGENTS.md`
2. `Administrative_Reform_1/01_Maintenance_System/SCHEMA_METAINFO_POLICY_v0.md`
3. `Administrative_Reform_1/00_Philosophy/Night_Government_Graph_Memory_Philosophy_2026_06_30.md`
4. `Administrative_Reform_1/00_Philosophy/R_Loop_Graph_Guide_Philosophy_2026_06_30.md`
5. `Administrative_Reform_1/05_Execution_Records/night_government_mvp_removed_2026_06_30_001.md`
6. `Administrative_Reform_1/04_Orders/ORDER_138_INTEGRATION_BASELINE_AND_DIRTY_WORKTREE_RECONCILIATION_V0.md`

특히 `night_government` 제거 기록을 반드시 읽는다.

이전 실패를 반복하지 않는다.

## 3. 배경 판단

외부 채팅방산 심야정부 MVP는 제거되었다.

이유:

- 기존 TurnStateCapsule/TraceStore/DataStore를 우선 사용하지 않았다.
- 별도 `MemoryRecord` 저장소를 만들었다.
- relative/mixed 정보의 source provenance가 송련 기준으로 부족했다.
- 0 기억공급관과 연결되지 않은 독립 active packet을 만들었다.

따라서 이번 ORDER_139는 "새 기억장"을 만들지 않는다.

기존 송련 runtime이 이미 만든 절대정보 좌표를 graph memory 문법으로 정리한다.

## 4. 구현 범위

### 4.1 Graph Memory Schema

최소 schema/frame을 추가한다.

후보 이름:

```text
GraphMemoryNodeFrame
GraphMemoryEdgeFrame
GraphMemorySnapshotFrame
CoreEgoTimeAxisFrame
RLoopGraphGuidePacketFrame
```

정확한 이름은 코드베이스 패턴에 맞춰 조정해도 된다.

단, 아래 개념은 반드시 표현한다.

#### Graph node kind

```text
raw_capsule
raw_bundle
summary
core_ego
time_axis
time_bundle
```

이번 발주에서 `summary`는 schema/계산 필드만 열어도 된다.

LLM 요약 생성은 하지 않는다.

#### Graph edge kind

```text
CONTAINS
CHILD_OF_TIME_AXIS
SOURCE_OF
SUMMARY_OF
```

이번 MVP에서 실제로 필요한 최소 edge만 만들어도 된다.

### 4.2 Raw Capsule Graph Node 생성

최근 `TurnStateCapsule` 또는 테스트용 capsule 입력을 받아 raw graph node를 만든다.

원칙:

- 새 memory text를 발명하지 않는다.
- 기존 capsule의 `turn_id`, trace count, movement count, user/final trace anchor 등 절대정보 좌표만 담는다.
- node id는 deterministic/idempotent 해야 한다.
- 같은 capsule을 두 번 ingest해도 중복 raw node를 만들지 않는다.

예상 node id 후보:

```text
graph:raw_capsule:{turn_id}
```

### 4.3 CoreEgo 시간축 연결

초기 CoreEgo 직속 연결은 시간축만 쓴다.

의미축은 만들지 않는다.

최소 구조:

```text
graph:core_ego:root
  -> graph:axis:time
      -> graph:time_bundle:{session_or_batch_id}
          -> graph:raw_capsule:{turn_id}
```

시간축 bundle은 코드가 확정 가능한 절대정보로 만든다.

사용자 의도/주제/의미 유사도 기준으로 묶지 않는다.

### 4.4 원문 절단 금지와 토큰 예산

이번 MVP는 원문 전문을 반드시 graph node에 넣을 필요는 없다.

다만 bundle 구성 정책은 아래 원칙을 반영한다.

```text
원문을 중간에서 자르지 않는다.
토큰/문자 예산을 넘으면 leaf 단위로 bundle을 나눈다.
예산에 걸치는 마지막 leaf는 다음 bundle로 넘기거나 제외한다.
```

초기 테스트에서는 문자 수 기반 예산을 써도 된다.

단, 이것을 "의미 판단"처럼 표시하지 않는다.

### 4.5 Summary Depth 계산 인프라

이번 발주에서 LLM summary를 만들지는 않는다.

하지만 summary depth 계산에 필요한 필드는 schema에 둔다.

후보 필드:

```text
summary_depth
source_depth_min
source_depth_max
source_leaf_count
source_summary_count
source_bundle_kind
```

raw leaf node는 다음과 같이 본다.

```text
summary_depth = 0
source_leaf_count = 1
source_summary_count = 0
```

raw bundle node는 summary가 아니므로 의미 요약으로 취급하지 않는다.

### 4.6 RLoopGraphGuidePacket 생성

그래프 snapshot을 기반으로 R루프용 guide packet을 만든다.

이번 MVP의 guide packet은 code-generated absolute/status 중심이어야 한다.

필수 후보 필드:

```text
graph_snapshot_id
target_consumer = R_LOOP
available_entry_nodes
node_kind_counts
data_kind_counts
summary_depth_range
source_leaf_count_range
risky_or_unreviewed_node_ids
generated_by
info_class
semantic_judgement_status
source_graph_node_ids
source_data_ids
source_trace_ids
```

이번 MVP에서는 `recommended_traversal_hints`를 LLM으로 만들지 않는다.

LLM hint는 다음 발주 후보로 남긴다.

따라서 guide packet은 다음처럼 표시한다.

```text
generated_by = CODE:GRAPH_MEMORY_GUIDE_BUILDER
info_class = absolute
semantic_judgement_status = not_run
recommended_traversal_hints_status = not_run
```

### 4.7 0 기억공급관 연결은 최소 또는 보류

이번 발주에서 0이 실제 qwen-turn/qwen-chat 흐름에 guide packet을 자동 주입하는 것은 필수 아님.

허용 범위:

- dry-run/smoke/test helper에서 guide packet 생성 확인
- DataStore record로 보존
- runtime summary에 count/status만 노출

금지:

- node_1 route 판단에 바로 사용
- node_3 최종 답변에 바로 사용
- R루프를 실제 route로 열기

## 5. 정보 분류 원칙

코드가 쓸 수 있는 것:

- node id
- edge id
- source id
- count
- existence
- graph kind
- created_at
- depth number
- token/char budget status
- schema pass/fail

코드가 쓰면 안 되는 것:

- 이 기억이 사용자에게 중요하다는 의미 판단
- 이 capsule이 어떤 주제라는 판단
- 이 graph node가 어떤 질문에 유용하다는 판단
- 요약/해석/의도/감정

이번 발주에서 LLM 의미 판단은 기본 `not_run`이다.

## 6. 금지

- `songryeon_core/night_government` 패키지를 되살리지 않는다.
- `MemoryRecord`, `NightGovernmentPacket`, `MemoryActivationItem` 구조를 재사용하지 않는다.
- 새 독립 기억장 JSONL DB를 만들지 않는다.
- 외부 Neo4j/SQLite/vector DB 연결을 이번 발주에서 열지 않는다.
- 의미축 CoreEgo 연결을 만들지 않는다.
- R1/R2/R3 LLM loop를 구현하지 않는다.
- R route를 node_1에 연결하지 않는다.
- W loop/scheduler/장기기억 자동 승격을 열지 않는다.
- summary를 raw node 속성에 덮어쓰지 않는다.
- 코드가 의미 요약을 쓰지 않는다.

## 7. 파일 후보

구현자는 실제 코드 구조를 읽고 조정한다.

후보:

```text
songryeon_core/core/schemas.py
songryeon_core/core/schema_parts/
songryeon_core/core/data_store.py
songryeon_core/nodes/node_0_memory_supplier.py
songryeon_core/runtime/dry_run.py
songryeon_core/runtime/terminal_view.py
songryeon_core/runtime/smoke_test.py
tests/test_order_139_graph_memory_foundation.py
```

schema가 비대해질 경우 `schema_parts`에 새 모듈로 분리하고 compatibility layer를 유지한다.

## 8. 체크포인트 루틴

작업 전:

```powershell
git status --short --branch
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

작업 후:

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
git diff --check
```

전체 pytest/smoke가 오래 걸리더라도 이번 작업은 기반 작업이므로 생략하지 않는다.

## 9. 추가 테스트 요구

pytest를 추가한다.

필수 테스트:

1. 같은 `TurnStateCapsule`을 두 번 graph ingest해도 raw capsule node가 중복 생성되지 않는다.
2. raw capsule graph node는 capsule의 절대정보 좌표만 담고 의미 요약을 담지 않는다.
3. CoreEgo root -> TimeAxis -> TimeBundle -> RawCapsule edge가 생성된다.
4. 의미축/semantic topic node가 생성되지 않는다.
5. raw node의 `summary_depth=0`, `source_leaf_count=1`, `source_summary_count=0`이 보존된다.
6. RLoopGraphGuidePacket이 entry node 목록/count/depth range/source id를 담는다.
7. RLoopGraphGuidePacket의 LLM hint는 `not_run`이다.
8. guide packet이 node_1 routing이나 node_3 answer에 자동 주입되지 않는다.
9. runtime/smoke summary에 graph memory guide 생성 상태가 노출된다.

## 10. 완료 보고에 반드시 포함할 것

완료 보고에는 다음을 적는다.

- Graph memory frame/schema를 어디에 만들었는지
- raw capsule node idempotency를 어떻게 보장했는지
- CoreEgo 시간축 edge 구조가 어떻게 생겼는지
- summary depth/source count 계산이 어디에 있는지
- RLoopGraphGuidePacket이 어디서 생성되는지
- LLM 의미 판단이 `not_run`으로 남아 있는지
- 금지 항목을 열지 않았는지
- compileall/pytest/smoke/diff-check 결과

## 11. 다음 발주 후보

ORDER_140 후보:

```text
R1/R2/R3 frame-only state machine audit
```

ORDER_141 후보:

```text
CoreEgoGuideWorker LLM traversal hint generation
```

ORDER_142 후보:

```text
External graph DB adapter boundary
```

외부 DB 연결은 ORDER_139에서 하지 않는다.

먼저 graph memory 문법과 guide packet이 송련 메타정보 원칙을 지키는지 잠근다.

