# ORDER 014: DataStore And Tool Result Payload Store

**상태**: 정식 발주서  
**승격일**: 2026-06-21  
**출처**: ORDER 013 이후 다음 수 결정  
**목표**: trace가 가리키는 실제 데이터 본체를 `DataStore`에 저장하고, L3가 도구 결과 payload를 다시 읽을 수 있게 한다.

## 배경

ORDER 013에서 `search_docs` 도구와 `tool_call` trace가 생겼다.  
하지만 trace에는 도구가 실행됐다는 사실과 `data_id`만 남고, 검색 결과 payload를 안정적으로 보관하는 공용 저장소가 없었다.

이 발주서는 다음 분리를 만든다.

```text
TraceStore = 무슨 일이 언제 어떤 순서로 일어났는지
DataStore = 그 일이 만든 실제 데이터 본체
DataRef = TraceStore와 DataStore를 이어주는 이름표
```

## 범위

1. `songryeon_core/core/data_store.py`를 만든다.
2. `DataRecord`와 `DataStore`를 구현한다.
3. `DataStore`는 `data_id` 중복을 막고 JSON 저장/복원을 지원한다.
4. `ToolRunner`는 도구 결과 payload를 `DataStore`에 저장한다.
5. L3는 `search_docs` 결과 payload를 읽어 보존 프레임 payload를 만든다.
6. 드라이런은 `TraceStore`와 `DataStore`를 함께 흘려보낸다.

## 원칙

1. trace에는 긴 payload를 직접 넣지 않는다.
2. trace의 `output_ref`는 DataStore의 `data_id`를 가리킨다.
3. DataStore에는 JSON 직렬화 가능한 payload만 넣는다.
4. L3의 보존 프레임은 아직 상대 판단을 하지 않는다.
5. 검색 결과의 의미 판단은 나중에 L3/2/LLM 설계와 함께 확장한다.

## 완료 기준

1. `python dry_run.py`가 통과한다.
2. 드라이런 결과에 `data_record_count`가 나온다.
3. `tool_result:search_docs:*` payload가 DataStore에 저장된다.
4. `L3:preserved_info_frame` payload가 DataStore에 저장된다.
5. Qwen, LangGraph, DB는 아직 사용하지 않는다.
