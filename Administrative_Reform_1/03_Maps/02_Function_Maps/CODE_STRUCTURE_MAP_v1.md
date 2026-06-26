# Code Structure Map v1

## 목적

이 문서는 2026-06-22 기준 SongRyeon Core의 실제 코드 위치를 학습용으로 정리한 기능 지도다.

이 문서는 발주서가 아니다.

코딩 전에 어느 파일을 읽어야 하는지 찾기 위한 지도다.

## 현재 안정 기준선

현재 프로젝트는 다음 기능까지 도달했다.

- 로컬 Qwen 호출
- fake adapter 기반 smoke
- L루프 내부 문서 검색
- document memory index
- search_docs/read_doc 도구
- trace/data/runtime artifact 저장
- 절대/상대/혼합 정보 라벨링
- node_2 boundary review
- node_3 LLM reporter
- node_4 gatekeeper
- pretty terminal runtime view

아직 구현하지 않은 것:

- W loop
- R loop/CoreEgo graph
- node_4 반려 후 자동 재작성 루프
- 장기 대화 기억 DB
- 실제 그래프 DB 기반 정체성 루프

## 루트 파일

```text
README.md
main.py
dry_run.py
Administrative_Reform_1/
songryeon_core/
```

### `README.md`

사람이 프로젝트를 처음 볼 때 읽는 입구다.

현재 원칙, 문서 입구, 실행 명령을 적는다.

### `main.py`

CLI 입구다.

역할:

- `dry-run`
- `search-docs`
- `show-orders`
- `replay`
- `qwen-ping`
- `qwen-l-loop-smoke`
- `fake-turn`
- `qwen-turn`
- `qwen-chat`
- `smoke-test`

새 명령을 추가할 때는 먼저 runtime 모듈에 기능을 만들고, `main.py`는 얇은 연결만 맡게 한다.

### `dry_run.py`

루트에서 바로 실행하는 호환용 wrapper다.

핵심 구현은 `songryeon_core/runtime/dry_run.py`에 있다.

## 코드 패키지

```text
songryeon_core/
  core/
  state/
  nodes/
  loops/
  tools/
  llm/
  prompts/
  runtime/
```

## `core/`

역할:

스키마, trace, data, registry, failure signal 같은 중심 계약을 둔다.

주요 파일:

- `schemas.py`: 대부분의 dataclass와 validator.
- `trace_store.py`: 턴 실행 흔적 저장.
- `data_store.py`: payload 본체 저장.
- `registry.py`: prompt/schema/tool registry 기초.
- `failure_signals.py`, `failure_signal_store.py`: 실패/부족 신호.

주의:

`schemas.py`는 커지고 있으므로, 다음 대규모 정리 때는 도메인별 스키마 파일 분리를 고려한다.

분리 후보:

```text
schemas/base.py
schemas/memory.py
schemas/routing.py
schemas/l_loop.py
schemas/metainfo.py
schemas/reporting.py
schemas/tools.py
```

하지만 지금은 import 안정성이 더 중요하므로 바로 쪼개지 않는다.

## `state/`

역할:

현재 턴 상태와 0이 보는 특수 기억 상태를 다룬다.

주요 파일:

- `unified_state.py`: 0 이외 노드들이 보는 상태 helper.
- `zero_state.py`: 0 기억공급관이 보는 상태와 턴 캡슐 helper.
- `capsule_persistence.py`: 턴 캡슐 저장/복원.

## `nodes/`

역할:

LLM 호출 또는 규칙 기반 노드 단위를 둔다.

현재 노드:

- `node_0_memory_supplier.py`
- `node_1_router.py`
- `node_2_metainfo_boundary.py`
- `node_2_handoff.py`
- `node_3_reporter.py`
- `node_4_gatekeeper.py`
- `l1_goal_setter.py`
- `l2_query_setter.py`
- `l3_result_keeper.py`

LLM wrapper 노드:

- `llm_node_0_memory_supplier.py`
- `llm_node_1_router.py`
- `llm_node_2_metainfo_boundary.py`
- `llm_node_3_reporter.py`

주의:

미래 W1은 `nodes/w1_problem_triage.py`로 들어가는 것이 자연스럽다.

R loop는 아직 live node로 만들지 않는다.

## `loops/`

역할:

여러 노드와 도구 호출을 묶는 루프를 둔다.

현재:

- `l_loop.py`

미래:

- `w_loop.py` 가능.
- `r_loop.py`는 CoreEgo/graph 설계가 선행될 때까지 보류.

## `tools/`

역할:

LLM이 직접 실행하지 않는 읽기/검색 도구를 둔다.

주요 파일:

- `document_loader.py`
- `document_snapshot.py`
- `document_memory_index.py`
- `document_tools.py`
- `embedding_backend.py`
- `embedding_model.py`
- `embedding_store.py`
- `vector_index_cache.py`
- `tool_runner.py`
- `tool_result_distiller.py`
- `tool_efficiency_policy.py`

현재 도구:

- `list_docs`
- `search_docs`
- `read_doc`

주의:

도구 결과는 도구가 만든 절대정보 또는 절대정보에 가까운 추출물이다.

도구 결과 안의 문장 내용이 참이라는 뜻은 아니다.

## `llm/`

역할:

LLM 호출, JSON 검증, adapter, fake model을 둔다.

주요 파일:

- `base.py`
- `fake.py`
- `runtime.py`
- `qwen_adapter.py`
- `json_validation.py`
- `node_executor.py`

원칙:

LLM raw output은 trace/data에 남길 수 있다.

하지만 raw output이 곧 최종 답변이나 사실은 아니다.

## `prompts/`

역할:

노드별 prompt 파일을 둔다.

미래 W1 prompt는 이 폴더에 `w1_problem_triage_v0.md`로 추가한다.

## `runtime/`

역할:

실제 한 턴 실행, CLI용 응답 payload, terminal view, smoke, replay를 둔다.

주요 파일:

- `dry_run.py`: 현재 한 턴 실행의 중심.
- `user_turn.py`: fake/qwen 사용자 턴 wrapper.
- `terminal_view.py`: 사람이 볼 pretty runtime과 answer 렌더링.
- `smoke_test.py`: 회귀 확인.
- `l_loop_smoke.py`: L loop smoke.
- `artifact_export.py`: trace/data/report export.
- `replay.py`: export 재생.

주의:

`runtime/dry_run.py`는 현재 가장 큰 결합점이다.

다음 대규모 리팩터링 후보는 다음과 같다.

```text
runtime/turn_context.py
runtime/route_flow.py
runtime/route2_flow.py
runtime/report_flow.py
```

하지만 지금은 기능이 살아있는 기준선 보존이 더 중요하므로, 작은 정리만 한다.

## 다음 학습 순서

처음부터 코드를 읽을 때 권장 순서:

```text
1. README.md
2. Administrative_Reform_1/01_Maintenance_System/SCHEMA_METAINFO_POLICY_v0.md
3. Administrative_Reform_1/01_Maintenance_System/DEVELOPMENT_CYCLE_POLICY_v0.md
4. Administrative_Reform_1/03_Maps/02_Function_Maps/CODE_STRUCTURE_MAP_v1.md
5. songryeon_core/runtime/user_turn.py
6. songryeon_core/runtime/dry_run.py
7. songryeon_core/runtime/terminal_view.py
8. songryeon_core/core/schemas.py
```

한 번에 다 이해하려 하지 않는다.

먼저 “사용자 입력이 어디서 들어와서 어떤 자료 구조로 바뀌는가”만 따라가면 된다.
