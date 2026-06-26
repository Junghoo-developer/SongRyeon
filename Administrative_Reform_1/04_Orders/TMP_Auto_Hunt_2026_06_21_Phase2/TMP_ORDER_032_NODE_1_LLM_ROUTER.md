# TMP ORDER 032: Node 1 LLM Router

## 목표

1 상황판단 라우터를 LLM 기반으로 바꾸되, 출력은 엄격한 라우팅 스키마로 제한한다.

## 배경

현재 1은 키워드 기반으로 `L` 또는 `2`를 고른다.  
실제 에이전트에서는 맥락 판단이 필요하지만, 라우팅 출력은 흔들리면 안 된다.

## 범위

1. `RoutingDecisionFrame`에 `routing_reason` 후보 필드를 추가한다.
2. 허용 route는 MVP 기준 `L`, `2`로 제한한다.
3. LLM 출력 검증 실패 시 규칙 기반 router로 fallback한다.
4. route reason은 source_trace_ids/source_data_ids를 가진 혼합 정보로 취급한다.

## 완료 기준

- LLM이 허용되지 않은 route를 내면 실패 처리된다.
- fallback router가 기존 동작을 유지한다.

## 제외

- R/W/C/M 라우트 활성화.
- 멀티 라우트 동시 실행.
