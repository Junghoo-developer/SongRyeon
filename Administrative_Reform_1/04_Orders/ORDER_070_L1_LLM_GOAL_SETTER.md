# ORDER 070: L1 LLM Goal Setter

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: L1의 거시/미시 목표와 이유를 코드가 고정 생성하는 문제  
**목표**: L1이 Node1 라우팅과 Node0 보고를 바탕으로 L루프의 거시/미시 목표를 LLM으로 설정하게 한다.

## 배경

현재 L1은 항상 `route_L_internal_document_lookup`와 `prepare_query_for_search_docs`를 만든다.  
이것은 운영상 편하지만, 목표 설정 이유는 사용자 입력과 현재 상황을 해석해야 하는 상대정보다.

## 범위

1. `L1GoalFrame`을 LLM 생성 목표와 코드 fallback 목표를 구분하도록 정리한다.
2. L1 prompt를 작성한다.
3. 입력에는 다음을 포함한다.
   - Node1 route decision
   - Node1 route reason
   - Node0 targeted memory packet
   - tool catalog
   - 현재 L루프에서 허용된 도구와 예산
4. LLM 출력에는 다음을 둔다.
   - `macro_goal`
   - `macro_goal_reason`
   - `micro_goal`
   - `micro_goal_reason`
   - `goal_limits`
   - `source_data_ids`
5. 코드는 목표 문장을 새로 쓰지 않고 schema 검증만 한다.
6. fallback 목표는 `CODE:FALLBACK_OPERATION_GOAL`로 표시한다.

## 원칙

1. 목표는 절대정보가 아니다.
2. 목표 ID와 schema status는 절대정보다.
3. 목표 이유는 LLM이 쓴 혼합정보로 보존한다.
4. L1은 L2가 검색어를 만들 수 있을 만큼 목표를 좁히되, 문서 내용의 진실성을 판단하지 않는다.

## 완료 기준

1. L1 LLM call이 저장된다.
2. L1 목표와 이유가 LLM 출력으로 표시된다.
3. L1 fallback이 발생하면 fallback으로 표시된다.
4. L2가 L1 목표를 입력으로 받아 기존 검색 흐름을 유지한다.
5. smoke test가 L1 LLM 성공/실패 경로를 검증한다.

