# ORDER 016: L2 Query Frame Schema

**상태**: 정식 발주서  
**승격일**: 2026-06-21  
**출처**: ORDER 015 이후 다음 수 결정  
**목표**: L2가 실제 검색 질의 프레임을 DataStore에 저장하고, `search_docs`가 그 프레임의 `query_text`를 사용하게 한다.

## 배경

ORDER 015까지 진행하면서 L3는 `search_docs` 결과를 스키마 기반 보존 프레임으로 저장하게 됐다.  
하지만 L2는 아직 `L2:query_frame`이라는 trace 출력만 만들고 실제 query payload를 저장하지 않는다.  
그 결과 L루프는 사용자 입력을 임시 query로 직접 `search_docs`에 넘기고 있다.

## 범위

1. `schemas.py`에 `L2QueryFrame` dataclass를 추가한다.
2. `L2QueryFrame` 검증 함수를 추가한다.
3. L2는 `L2:query_frame` payload를 DataStore에 저장한다.
4. L루프는 DataStore에서 `L2:query_frame.query_text`를 읽어 `search_docs`에 넘긴다.
5. L루프의 output data 목록에 `L2:query_frame`을 포함한다.

## 메타정보 분리

### 절대 정보

- `frame_id`
- `turn_id`
- `schema_name`
- `schema_version`
- `source_trace_ids`
- `source_data_ids`
- `query_text`
- `query_source`
- `query_mode`
- `target_tool_name`

`query_text`는 "가장 좋은 검색어"라는 판단이 아니다.  
현재 MVP에서는 사용자 입력에서 임시로 만든 검색 질의 문자열이라는 절대정보로 둔다.

### 상대 정보

이번 단계에서는 검색어 후보 비교, 검색 의도 해석, 질의 품질 평가는 하지 않는다.

### 혼합 정보

이번 단계에서는 생성하지 않는다.

## 완료 기준

1. `python dry_run.py`가 통과한다.
2. `data_record_count`가 3이 된다.
3. DataStore에 `L2:query_frame` payload가 저장된다.
4. `search_docs`는 `L2:query_frame.query_text`를 사용한다.
5. Qwen, LangGraph, DB는 아직 사용하지 않는다.
