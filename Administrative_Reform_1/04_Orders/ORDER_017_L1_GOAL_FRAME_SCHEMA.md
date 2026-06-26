# ORDER 017: L1 Goal Frame Schema

**상태**: 정식 발주서  
**승격일**: 2026-06-21  
**출처**: ORDER 016 이후 다음 수 결정  
**목표**: L1이 L루프의 목표 프레임을 DataStore에 저장하고, L2/L3가 그 목표 프레임을 출처로 이어받게 한다.

## 배경

ORDER 016까지 진행하면서 L2 query frame, `search_docs` tool result, L3 preserved frame은 모두 DataStore payload를 갖게 됐다.  
하지만 L1은 아직 `L1:goal_frame` trace 출력만 만들고 실제 payload를 저장하지 않는다.

## 범위

1. `schemas.py`에 `L1GoalFrame` dataclass를 추가한다.
2. `L1GoalFrame` 검증 함수를 추가한다.
3. L1은 `L1:goal_frame` payload를 DataStore에 저장한다.
4. L2는 `L1:goal_frame`을 source data로 받는다.
5. L3는 `L1:goal_frame`, `L2:query_frame`, `tool_result:search_docs:*`를 모두 source data로 받는다.

## 메타정보 분리

### 절대 정보

- `frame_id`
- `turn_id`
- `schema_name`
- `schema_version`
- `source_trace_ids`
- `source_data_ids`
- `macro_goal`
- `micro_goal`
- `goal_source`
- `target_loop`

이번 단계의 `macro_goal`, `micro_goal`은 LLM이 사용자 의도를 해석한 결과가 아니다.  
MVP L루프가 실행될 때 코드가 부여한 규칙 기반 운영 목표다.

### 상대 정보

이번 단계에서는 사용자 의도 해석, 목표 품질 판단, 목표 재작성은 하지 않는다.

### 혼합 정보

이번 단계에서는 생성하지 않는다.

## 완료 기준

1. `python dry_run.py`가 통과한다.
2. `data_record_count`가 4가 된다.
3. DataStore에 `L1:goal_frame` payload가 저장된다.
4. L2 source data에 `L1:goal_frame`이 들어간다.
5. L3 source data에 `L1:goal_frame`, `L2:query_frame`, `tool_result:search_docs:*`가 모두 들어간다.
6. Qwen, LangGraph, DB는 아직 사용하지 않는다.
