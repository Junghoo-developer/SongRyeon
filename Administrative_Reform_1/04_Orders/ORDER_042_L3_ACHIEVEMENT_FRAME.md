# ORDER 042: L3 Achievement Frame

**상태**: 정식 발주서  
**승격일**: 2026-06-21  
**출처**: 사용자 요청 "다음은 L3AchievementFrame"  
**목표**: L3가 L루프의 운영 목표 달성 여부와 이유를 스키마로 강제해 DataStore에 남긴다.

## 배경

현재 L3는 `L3PreservedInfoFrame`으로 검색 결과 후보를 보존하지만, 달성 여부는 `judgement_status=not_judged`에 머물러 있다.  
따라서 1이나 2가 L루프 결과를 해석하려면 "검색 결과가 있었는가", "운영 목표를 달성했는가"를 직접 추정해야 한다.

## 범위

1. `L3AchievementFrame` 스키마를 만든다.
2. L3는 `L3:preserved_info_frame`과 함께 `L3:achievement_frame`을 생성한다.
3. 달성 여부, 이유, 후보 수, 근거 trace/data ID를 payload에 남긴다.
4. 이 판단은 문서 내용의 진실성 판단이 아니라 검색/보존 산출물 존재 여부에 대한 운영 판단으로 제한한다.
5. L루프 결과와 2 입력 프레임이 `L3:achievement_frame`을 포함하게 한다.

## 완료 기준

1. `python dry_run.py`가 통과한다.
2. DataStore에 `L3:achievement_frame`이 저장된다.
3. `L3:achievement_frame.reason`이 비어 있지 않다.
4. `python main.py smoke-test`가 통과한다.
