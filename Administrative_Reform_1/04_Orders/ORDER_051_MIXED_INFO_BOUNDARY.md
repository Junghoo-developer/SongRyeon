# ORDER 051: Mixed Info Boundary

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: ORDER 042-046 이후 보고 경계 확장 필요  
**목표**: 2 메타정보 경계관이 절대정보뿐 아니라 근거가 붙은 혼합 정보도 조건부로 허가하게 한다.

## 배경

현재 2는 `Node2InputFrame`이 지정한 source를 바탕으로 절대정보 목록을 만든다.  
하지만 `L3AchievementFrame.reason`, `ToolChoiceFrame.reason`, `L2QueryPlanCandidate.purpose` 같은 정보는 이미 근거 ID를 가진 혼합 정보인데도, 3 보고관은 아직 그 본문을 안전하게 말하지 않는다.

## 범위

1. `MixedInfoRef` 또는 동등한 boundary payload 구조를 만든다.
2. 혼합 정보는 반드시 원본 data_id와 field path를 가진다.
3. 혼합 정보는 반드시 근거 `source_trace_ids`, `source_data_ids`를 가진다.
4. 2는 허가 가능한 혼합 정보와 아직 보고하면 안 되는 혼합 정보를 구분한다.
5. `L3AchievementFrame.reason`, `ToolChoiceFrame.reason`을 1차 허가 후보로 삼는다.

## 원칙

1. 혼합 정보는 절대정보가 아니다.
2. 혼합 정보는 출처 없는 자연어 주장으로 보고되면 안 된다.
3. 2는 "말해도 되는 문장"이 아니라 "말해도 되는 근거 달린 정보 조각"을 허가한다.

## 완료 기준

1. `MetainfoBoundary.mixed_info`에 허가된 혼합 정보가 들어간다.
2. 각 mixed info는 source data/trace ID를 가진다.
3. 근거 없는 혼합 정보는 boundary에 들어가지 않는다.
4. `python main.py smoke-test`가 통과한다.
