# ORDER 001: Schema Foundation

**상태**: 정식 발주서  
**승격일**: 2026-06-21  
**출처**: `TMP_Auto_Hunt_2026_06_21/TMP_ORDER_001_SCHEMA_FOUNDATION.md`  
**목표**: 연습장 MVP의 기본 데이터 그릇을 Python 타입 초안으로 정의한다.

## 작업 범위

다음 스키마를 `schemas.py`에 정의한다.

- `TraceEvent`
- `UnifiedState`
- `ZeroState`
- `TurnStateCapsule`
- `MemoryPacketFrom0`
- `RoutingDecision`
- `MetainfoBoundary`
- `FailureSignal`

## 원칙

1. 각 스키마는 `dataclass`로 만든다.
2. 각 필드에는 한글 주석으로 의미를 짧게 설명한다.
3. Qwen 14B, LangGraph, 실제 노드 실행은 붙이지 않는다.
4. 이번 발주서는 구조 그릇만 만든다.

## 완료 기준

1. `schemas.py`가 존재한다.
2. 위 8개 스키마가 모두 정의되어 있다.
3. `python -m py_compile schemas.py`가 통과한다.
