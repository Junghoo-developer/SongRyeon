# Structure Map v0

## 목적

이 문서는 SongRyeon Core 에이전트의 현재 설계를 학습용으로 정리한 기능 지도다. 아직 발주서가 아니며, 이 문서만으로 코딩을 시작하지 않는다.

## 핵심 흐름

```text
사용자 입력
-> 0 기억공급관
-> 1 상황판단 라우터
-> 0 조건부 기억공급
-> 2 또는 L
-> 0 루프/턴 trace 정리
-> 1 복귀 또는 2 전달
-> 3 보고
```

## 0 기억공급관

0은 LLM 호출 단위의 노드다. 단, 일반 노드처럼 한 번만 지나가는 것이 아니라 여러 지점에서 반복 호출된다.

### 입력

- 최근 대화 원본. 예: 최근 8턴.
- 오래된 대화 요약본.
- 최근 대화 원본에 대응하는 이전 턴의 0.state 또는 턴 상태 캡슐.
- 이번 턴의 실시간 trace.
- 1의 라우팅 결정.
- 1의 라우팅 이유.
- 라우팅 대상 노드/루프의 특성.

### 역할

1. 사용자 입력 직후 1에게 사전 보고한다.
2. 1의 라우팅 후 대상에 맞는 기억 패킷을 공급한다.
3. 루프가 끝나고 1로 돌아가기 전에 루프 trace를 1이 보기 좋게 압축한다.
4. 1이 2로 라우팅하기 직전에 이번 턴 trace를 최종 정리하고 성패를 판정한다.
5. 접근할 수 없는 기억은 만들어내지 않고 기억 부족 신호를 낸다.

## 1 상황판단 라우터

1은 최근 대화, 사용자 직전 입력, 0의 보고를 듣고 상황을 판단한다. 판단력은 라우팅과 라우팅 이유 작성에 집중한다.

### MVP 라우팅 대상

- `2`: 메타정보 경계관.
- `L`: 장기기억/내부문서 검색 루프.

### 출력

- 라우팅 대상.
- 라우팅 이유.
- 스키마 강제 여부와 스키마 이름.

## 2 메타정보 경계관

2는 0의 최종 trace 정리를 보고 3이 말할 수 있는 경계를 만든다.

현재 MVP에서 2는 전체 trace/data 저장소를 직접 훑지 않는다. 0이 먼저 `Node2InputFrame`을 만들고, 2는 그 프레임에 적힌 `source_trace_ids`, `source_data_ids`만 읽어서 `MetainfoBoundary`를 만든다.

### Node2InputFrame

0이 2에게 넘기는 입력 프레임 스키마다.

- `frame_id`: 입력 프레임 data_id. 예: `node2_input:turn_dry_001`.
- `turn_id`: 프레임이 만들어진 턴.
- `final_memory_packet_id`: 0이 2에게 마지막으로 넘긴 memory packet data_id.
- `turn_outcome_id`: 0이 판정한 이번 턴 종료 상태 data_id.
- `route_ids`: 이번 턴에서 1이 만든 라우팅 결정 data_id 목록.
- `l_loop_output_ids`: L루프가 만든 주요 output data_id 목록.
- `source_trace_ids`: 2가 읽어도 되는 trace ID 목록.
- `source_data_ids`: 2가 읽어도 되는 DataStore record ID 목록.
- `boundary_policy`: 2가 어떤 정책으로 경계를 만들지 나타내는 이름.
- `schema_name`, `schema_version`: 적용된 스키마 이름과 버전.

이 프레임은 LLM 판단 결과가 아니다. 코드가 이미 존재하는 trace/data ID를 선별해서 묶은 절대정보 입력 계약이다.

### 메타정보 분류

#### 절대 정보

코드나 trace가 자동으로 채울 수 있는 기준점이다. 예를 들어 데이터 id, 개발자가 강제한 정보, 데이터 날짜, 데이터 종류, 데이터 존재 여부가 있다.

#### 상대 정보

가변적이고 해석이 필요한 정보다. 사용자 의도 추정, 상황 판단, 요약, 해석 등이 여기에 들어간다.

#### 혼합 정보

절대 정보를 출처로 삼아 만든 판단이다. 상대 정보와 혼합 정보는 반드시 출처가 되는 절대 정보 id를 가져야 한다.

## 3 보고관

3은 2가 허용한 정보만 보고 사용자에게 말한다. 표현은 어느 정도 풀어도 되지만, 출처 없는 단정은 하면 안 된다.

## L루프

L루프는 장기기억과 내부 문서를 검색하는 루프다.

```text
1이 L로 라우팅
-> 0이 L루프에 필요한 기억 공급
-> L1 목표 설정
-> L2 검색어 설정
-> search_docs 임베딩 문서 검색
-> L3 달성 여부 판단과 보존 정보 작성
-> 0이 L루프 trace를 1에게 요약
```

### L1

0의 보고를 받고 처음 시동을 건다. 거시 목표와 미시 목표를 설정하고 그 이유를 적는다.

현재 MVP에서 L1은 LLM으로 사용자 의도를 해석하지 않는다. 대신 L루프가 실행될 때 필요한 규칙 기반 운영 목표를 `L1GoalFrame` 스키마 payload로 DataStore에 저장한다.

### L1GoalFrame

L1이 L루프의 운영 목표를 저장하는 프레임 스키마다.

- `frame_id`: goal frame data_id.
- `turn_id`: 프레임이 만들어진 턴.
- `macro_goal`: L루프에 부여된 큰 운영 목표.
- `micro_goal`: macro_goal을 실행하기 위한 작은 운영 목표.
- `goal_source`: 목표 출처. 현재는 `rule_based_l_route`.
- `target_loop`: 목표가 적용되는 루프. 현재는 `L`.
- `schema_name`, `schema_version`: 적용된 스키마 이름과 버전.
- `source_trace_ids`: L1이 입력으로 받은 trace 목록.
- `source_data_ids`: L1이 입력으로 읽은 DataStore record 목록.

현재 `macro_goal`, `micro_goal`은 사용자 의도 해석이 아니라 코드가 부여한 운영 목표다.

### L2

0의 보고와 L1의 출력을 보고 검색어를 설정한다. L2의 source data에는 `L1:goal_frame`이 들어간다.

현재 MVP에서 L2는 LLM으로 검색어를 새로 생성하지 않는다. 대신 사용자 입력을 `user_input_fallback` 출처의 `query_text`로 삼아 `L2QueryFrame` 스키마를 통과한 payload를 DataStore에 저장한다.
ORDER 045부터는 선택적으로 LLM query planner를 붙일 수 있다. 이 경우 L2는 먼저 `L2QueryPlanFrame`을 만들고, 선택된 후보 하나를 `L2QueryFrame`으로 이어 보낸다. LLM planner가 실패하면 기존 `user_input_fallback` 검색으로 돌아간다.

### L2QueryPlanFrame

L2가 내부 문서 검색어 후보들을 저장하는 계획 프레임 스키마다.

- `frame_id`: query plan frame data_id. 현재는 `L2:query_plan_frame`.
- `turn_id`: 프레임이 만들어진 턴.
- `planner_mode`: query plan 생성 방식. 현재는 `llm` 또는 `fallback`.
- `selected_candidate_id`: 실제 검색에 사용할 후보 ID.
- `candidates`: 검색어 후보 목록.
- `source_trace_ids`: L2 planner가 입력으로 받은 trace ID 목록. LLM call trace도 포함될 수 있다.
- `source_data_ids`: L2 planner가 입력으로 읽은 DataStore record ID 목록. LLM call record도 포함될 수 있다.
- `schema_name`, `schema_version`: 적용된 스키마 이름과 버전.

각 후보는 `query_text`, `purpose`, `expected_signal`, `priority`, `target_tool_name`, `source_data_ids`를 가진다. `purpose`와 `expected_signal`은 혼합 정보이므로 근거 data ID를 함께 가진다.

### L2QueryFrame

L2가 검색 도구에 넘길 질의를 저장하는 프레임 스키마다.

- `frame_id`: query frame data_id.
- `turn_id`: 프레임이 만들어진 턴.
- `query_text`: 검색 도구에 넘길 질의 문자열.
- `query_source`: 질의 문자열의 출처. 현재는 `user_input_fallback`.
- `query_mode`: 검색 방식. 현재는 `embedding_search`.
- `target_tool_name`: 대상 도구 이름. 현재는 `search_docs`.
- `schema_name`, `schema_version`: 적용된 스키마 이름과 버전.
- `source_trace_ids`: L2가 입력으로 받은 trace 목록.
- `source_data_ids`: L2가 입력으로 읽은 DataStore record 목록.

`query_source`는 현재 `user_input_fallback` 또는 `llm_query_plan`이 될 수 있다.

### search_docs

L2 이후 호출되는 읽기 전용 문서 검색 도구다. MVP에서는 외부 임베딩 모델 대신 로컬 해시 임베딩으로 내부 Markdown 문서 chunk를 검색한다. 검색 query는 DataStore의 `L2:query_frame.query_text`에서 읽는다.

### ToolCatalogFrame

ORDER 046부터 L루프는 도구 실행 전에 `ToolRegistry` 내용을 `ToolCatalogFrame`으로 저장한다.

- `catalog_id`: tool catalog data_id. 예: `tool_catalog:turn_dry_001`.
- `turn_id`: catalog가 만들어진 턴.
- `tools`: 사용 가능한 도구 목록.
- `source_trace_ids`: catalog 생성의 근거 trace ID 목록.
- `source_data_ids`: catalog 생성의 근거 data ID 목록.
- `schema_name`, `schema_version`: 적용된 스키마 이름과 버전.

각 도구 항목은 `tool_name`, `description`, `read_only`, `input_fields`, `output_data_type`을 가진다. 현재 문서 도구 catalog에는 `list_docs`, `read_doc`, `search_docs`가 들어간다.

### ToolChoiceFrame

L2가 실제로 어떤 도구를 쓰기로 했는지 저장하는 선택 프레임이다.

- `choice_id`: tool choice data_id. 예: `tool_choice:L2:search_docs`.
- `turn_id`: 선택이 만들어진 턴.
- `chooser_node_id`: 도구를 선택한 노드. 현재는 `L2`.
- `tool_name`: 선택된 도구 이름.
- `reason`: 도구 선택 이유.
- `expected_use`: 이 도구로 기대하는 사용 효과.
- `catalog_id`: 참조한 tool catalog data_id.
- `source_trace_ids`: 선택 근거 trace ID 목록.
- `source_data_ids`: 선택 근거 data ID 목록. 반드시 `catalog_id`를 포함한다.
- `schema_name`, `schema_version`: 적용된 스키마 이름과 버전.

LLM은 도구 실행권을 직접 갖지 않는다. LLM이나 노드는 `ToolChoiceFrame`을 만들고, 코드는 선택된 `tool_name`이 registry에 존재하는지 검증한 뒤 도구를 실행한다.

### LLM 기반 L루프 후속 방향

ORDER 043-050은 LLM을 실제 런타임에 올리고, L루프가 검색어 계획과 도구 선택을 더 자율적으로 하도록 확장하는 발주서 묶음이다.

```text
LLM runtime 활성화
-> LLM call trace/retry 표준화
-> L2 LLM query plan
-> tool catalog 제공
-> L loop controller 반복 검색
-> tool result distillation
-> tool efficiency policy
-> LLM L loop smoke/replay
```

이 흐름에서도 LLM은 도구를 직접 실행하지 않는다. LLM은 query plan, tool choice, stop decision 같은 구조화된 프레임을 만들고, 코드는 registry, schema, budget을 검증한 뒤 도구를 실행한다.

### LLMCallFrame

ORDER 044부터 LLM 호출은 `LLMCallFrame`으로 trace/data에 남길 수 있다.

- `call_id`: LLM call data_id.
- `turn_id`: 호출이 속한 턴.
- `node_id`: 호출을 요청한 노드.
- `prompt_ref`: 사용한 prompt 파일이나 식별자.
- `input_data_ids`: 입력 payload가 근거로 삼은 data ID 목록.
- `model_id`: 호출된 모델 ID.
- `response_format`: 요청한 응답 형식.
- `raw_text`: LLM 원문 응답.
- `parse_status`: JSON 파싱 통과 여부.
- `validation_status`: 스키마 검증 통과 여부.
- `retry_count`: 재시도 횟수.
- `failure_type`: `none`, `parse_failed`, `schema_failed`, `adapter_failed` 중 하나.
- `source_trace_ids`, `source_data_ids`: 호출의 근거 ID 목록.

LLM raw output은 저장되지만 자동으로 사용자에게 보고되는 정보는 아니다. 2와 3의 경계를 통과한 정보만 최종 보고에 쓰인다.

### L3

L1, L2의 출력과 그 이유에 대응하여 달성 여부를 판단한다. 동시에 다음 흐름에 전달해야 할 정보를 적절한 양으로 보존한다.

현재 MVP에서 L3는 의미 판단을 하지 않는다. 대신 `L3PreservedInfoFrame` 스키마를 통과한 보존 프레임을 DataStore에 저장한다.
L3의 source data에는 `L1:goal_frame`, `L2:query_frame`, `tool_result:search_docs:*`가 함께 들어간다.
또한 `L3AchievementFrame`으로 검색/보존 운영 목표의 달성 여부와 이유를 남긴다. 이 판단은 문서 내용의 사실성이나 충분성 판단이 아니라, 검색 결과 후보가 보존되었는지를 기준으로 한 제한적 운영 판단이다.

### L3PreservedInfoFrame

L3가 2번에게 넘기기 위해 만드는 보존 프레임 스키마다.

- `frame_id`: 보존 프레임 data_id.
- `turn_id`: 프레임이 만들어진 턴.
- `schema_name`, `schema_version`: 적용된 스키마 이름과 버전.
- `source_trace_ids`: L3가 입력으로 받은 trace 목록.
- `source_data_ids`: L3가 읽은 DataStore record 목록.
- `judgement_status`: 현재는 `not_judged`만 사용한다.
- `candidates`: `search_docs` 결과에서 보존한 후보 목록.

후보의 `doc_id`, `chunk_id`, `score`, `text_preview`는 도구 payload에서 확인한 절대정보다. 문서 내용의 진실성이나 중요도를 판단한 것은 아니다.

### L3AchievementFrame

L3가 L루프의 운영 목표 달성 여부와 이유를 저장하는 프레임 스키마다.

- `frame_id`: 판단 프레임 data_id. 현재는 `L3:achievement_frame`.
- `turn_id`: 프레임이 만들어진 턴.
- `achievement_status`: 제한된 규칙으로 정한 운영 달성 상태. 현재는 `achieved`, `partial`, `failed` 후보를 둔다.
- `reason`: 달성 상태를 선택한 이유.
- `target_goal_data_id`: 기준이 된 L1 목표 프레임 data_id.
- `preserved_info_frame_id`: 참조한 L3 보존 프레임 data_id.
- `candidate_count`: 보존 프레임에 들어간 검색 후보 개수.
- `evidence_trace_ids`: 판단의 근거 trace ID 목록.
- `evidence_data_ids`: 판단의 근거 DataStore record ID 목록.
- `source_trace_ids`: L3가 입력으로 받은 trace ID 목록.
- `source_data_ids`: L3가 입력으로 읽었거나 만든 DataStore record ID 목록.
- `schema_name`, `schema_version`: 적용된 스키마 이름과 버전.

`achievement_status`와 `reason`은 절대정보 그 자체가 아니라 절대정보를 근거로 만든 혼합 정보다. 따라서 반드시 `evidence_trace_ids`, `evidence_data_ids`를 같이 가진다.

## State와 Trace

### UnifiedState

0 이외의 노드와 루프가 보는 공용 state다.

### 0.state

0이 관리하는 특수 state다. 최근 대화 원본, 대화 요약본, 이전 턴의 상태 캡슐, 이번 턴 trace를 포함한다.

### Trace

trace는 일이 어떤 순서와 이유로 진행됐는지 남긴 실행 흔적이다. 일거수일투족을 저장하되, 나중에 0이나 DB/그래프 지식화를 위해 최적화한다.

### DataStore

DataStore는 trace가 만든 실제 데이터 본체를 `data_id` 기준으로 저장한다. trace에는 긴 payload를 직접 넣지 않고, `output_ref`와 DataRef가 DataStore의 record를 가리킨다.

## 현재 코드 폴더

```text
songryeon_core/
  core/
    schemas.py
    trace_store.py
    data_store.py
    failure_signal_store.py
    registry.py
    failure_signals.py
  llm/
    base.py
    fake.py
    json_validation.py
    node_executor.py
    qwen_adapter.py
  state/
    unified_state.py
    zero_state.py
    capsule_persistence.py
  nodes/
    llm_node_0_memory_supplier.py
    llm_node_1_router.py
    llm_node_2_metainfo_boundary.py
    llm_node_3_reporter.py
    l1_goal_setter.py
    l2_query_setter.py
    l3_result_keeper.py
    node_0_memory_supplier.py
    node_1_router.py
    node_2_metainfo_boundary.py
    node_3_reporter.py
  loops/
    l_loop.py
  tools/
    document_snapshot.py
    document_loader.py
    embedding_backend.py
    embedding_model.py
    embedding_store.py
    vector_index_cache.py
    document_tools.py
    tool_runner.py
  prompts/
    node_0_memory_supplier_v0.md
    node_1_router_v0.md
    node_2_metainfo_boundary_v0.md
    node_3_reporter_v0.md
  runtime/
    artifact_export.py
    dry_run.py
    replay.py
    smoke_test.py
```

루트의 `dry_run.py`는 `songryeon_core/runtime/dry_run.py`를 호출하는 실행 래퍼다.
루트의 `main.py`는 dry-run, search-docs, replay, smoke-test를 제공하는 CLI다.
