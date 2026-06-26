# ORDER 041: Node2 Input Frame

**상태**: 정식 발주서  
**승격일**: 2026-06-21  
**출처**: 사용자 요청 "2의 입력 데이터 정리"  
**목표**: 2 메타정보 경계관이 전체 trace/data를 직접 훑지 않고, 0이 정리한 `Node2InputFrame`을 입력으로 받게 한다.

## 배경

현재 2는 `trace_store.events_for_turn(turn_id)` 전체를 순회하며 절대정보 후보를 만든다.  
이 방식은 시스템적으로는 안전하지만, 입력 범위가 너무 넓어 보고가 시끄럽고 LLM을 붙였을 때 입력 통제가 어렵다.

## 범위

1. `Node2InputFrame` 스키마를 만든다.
2. 0은 2번 직전에 `node2_input:<turn_id>` payload를 DataStore에 저장한다.
3. `Node2InputFrame`에는 2가 볼 trace/data ID와 핵심 역할별 ID를 명시한다.
4. 2는 `Node2InputFrame`이 있으면 그 프레임에 적힌 source만 읽는다.
5. 기존 전체 trace fallback은 유지한다.

## 원칙

1. 2는 "모든 것을 보는 노드"가 아니라 "0이 정리한 경계 입력을 검증하는 노드"가 된다.
2. 0은 정보를 창조하지 않고 trace/data ID를 선별해 묶는다.
3. LLM이 들어와도 prompt에는 `Node2InputFrame` 중심 입력을 넘긴다.

## 완료 기준

1. `python dry_run.py`가 통과한다.
2. DataStore에 `node2_input:turn_dry_001`이 저장된다.
3. boundary source가 `Node2InputFrame`을 기준으로 만들어진다.
4. `python main.py smoke-test`가 통과한다.
