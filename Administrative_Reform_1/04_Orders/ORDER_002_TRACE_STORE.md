# ORDER 002: Trace Store

**상태**: 정식 발주서  
**승격일**: 2026-06-21  
**출처**: `TMP_Auto_Hunt_2026_06_21/TMP_ORDER_002_TRACE_EVENT_FORMAT.md`  
**목표**: `TraceEvent`를 실제로 추가, 조회, 저장, 복원할 수 있는 최소 trace 저장소를 만든다.

## 범위

1. `trace_store.py`를 만든다.
2. `TraceEvent`를 메모리에 추가할 수 있게 한다.
3. 전체 trace 목록을 조회할 수 있게 한다.
4. `turn_id` 기준으로 trace를 조회할 수 있게 한다.
5. JSON 파일로 저장하고 다시 불러올 수 있게 한다.

## 원칙

1. Qwen 14B는 연결하지 않는다.
2. LangGraph는 연결하지 않는다.
3. DB는 만들지 않는다.
4. 상대 정보 필드는 추가하지 않는다.
5. trace 저장소는 `schemas.py`의 절대정보 구조를 사용한다.

## 완료 기준

1. `trace_store.py`가 존재한다.
2. `python -m py_compile schemas.py trace_store.py`가 통과한다.
3. 샘플 trace를 추가, 저장, 복원, 턴별 조회할 수 있다.
