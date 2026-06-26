# ORDER 001A: Schema Absolute Refinement

**상태**: 정식 발주서  
**승격일**: 2026-06-21  
**출처**: `ORDER_001_SCHEMA_FOUNDATION.md` 실행 후 사용자 검토  
**목표**: `schemas.py`를 절대정보 중심으로 더 신중하게 다듬는다.

## 배경

`TurnStateCapsule`의 노드 동선은 단순한 "주요 경로"가 아니라, 한 턴에서 지나간 모든 노드/루프 동선을 trace와 입출력에 연결해야 한다.

또한 상대 정보와 혼합 정보는 아직 노드 설계와 병행해야 하므로, 이번 단계에서는 확정 가능한 절대정보 필드만 강화한다.

## 작업 범위

1. 노드 동선을 `dict`가 아니라 명시 스키마로 표현한다.
2. 스키마 적용 정보를 명시 스키마로 표현한다.
3. 데이터 id, 종류, 존재 여부 같은 절대정보 참조 구조를 추가한다.
4. 상대 정보, 혼합 정보 필드는 추가하지 않는다.

## 완료 기준

1. `TurnStateCapsule`이 전체 노드 동선을 `NodeMovement`로 보존한다.
2. 노드 입출력은 trace id와 data id에 연결될 수 있다.
3. `python -m py_compile schemas.py`가 통과한다.
