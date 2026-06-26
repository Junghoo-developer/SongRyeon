# ORDER 005-012A: L Nodes Folder Split

**상태**: 정식 발주서  
**승격일**: 2026-06-21  
**출처**: 사용자 요청 "노드 폴더에 L1,2,3도 추가"  
**목표**: L루프 내부의 L1, L2, L3를 `nodes/` 폴더의 독립 노드 파일로 분리한다.

## 범위

1. `songryeon_core/nodes/l1_goal_setter.py`를 만든다.
2. `songryeon_core/nodes/l2_query_setter.py`를 만든다.
3. `songryeon_core/nodes/l3_result_keeper.py`를 만든다.
4. `songryeon_core/loops/l_loop.py`는 세 노드를 호출하는 조립 루프로 바꾼다.

## 원칙

1. LLM 호출은 아직 붙이지 않는다.
2. 기존 dry run 결과가 유지되어야 한다.
3. L1/L2/L3도 trace를 남기는 노드로 취급한다.
