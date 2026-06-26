# ORDER 045: L2 LLM Query Planner

**상태**: 정식 발주서  
**승격일**: 2026-06-21  
**출처**: 사용자 요청 "L루프에게 미리 일일이 다 데이터 설명 안 해도 알아서 척척 검색"  
**목표**: L2가 사용자 입력 fallback 하나만 검색하지 않고, LLM을 사용해 내부 문서 검색용 query 후보를 계획하게 한다.

## 배경

현재 L2는 `query_source=user_input_fallback`으로 사용자 입력을 거의 그대로 `search_docs`에 넘긴다.  
이 방식은 단순하지만 사용자가 내부 문서 구조와 데이터 이름을 일일이 설명해야 검색 품질이 오른다.

## 범위

1. `L2QueryPlanFrame` 스키마를 만든다.
2. L2 LLM 입력에는 사용자 입력, L1 목표, 0의 기억 패킷, 사용 가능한 도구 목록 요약을 넣는다.
3. L2는 검색 query 후보 여러 개와 우선순위를 만든다.
4. 각 query 후보에는 `query_text`, `purpose`, `expected_signal`, `source_data_ids`를 둔다.
5. 기존 `L2QueryFrame`은 첫 번째 실행 query 또는 선택된 query를 저장하는 실행 프레임으로 유지한다.

## 원칙

1. L2는 문서 내용을 상상하지 않는다. 검색어를 계획할 뿐이다.
2. query 생성 이유는 혼합 정보이며 근거 source ID를 가져야 한다.
3. LLM 실패 시 기존 user_input fallback으로 검색한다.

## 완료 기준

1. DataStore에 `L2:query_plan_frame`이 저장된다.
2. L2가 최소 1개 이상의 query 후보를 생성한다.
3. 선택된 query가 `L2:query_frame.query_text`로 이어진다.
4. FakeLLM 실패 시에도 기존 `search_docs` 흐름이 유지된다.
