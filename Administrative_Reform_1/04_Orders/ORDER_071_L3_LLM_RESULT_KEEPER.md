# ORDER 071: L3 LLM Result Keeper

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: L3가 코드로 목표 달성 여부와 이유를 쓰는 최대 월권 지점  
**목표**: L3의 의미적 달성 판단과 보존 이유를 LLM에게 맡기고, 코드는 운영 상태와 후보 추출만 담당하게 한다.

## 배경

현재 L3는 search_docs 후보 수와 controller decision을 보고 `achieved`, `partial`, `failed`와 이유문을 만든다.  
라벨은 `CODE:OPERATION_CHECK`지만, 사용자는 이것을 실제 목표 달성 판단으로 읽기 쉽다.

이 발주서는 L3를 두 층으로 나눈다.

1. 코드 층: 후보 추출, 개수, ID, controller 상태 기록
2. LLM 층: 목표 대비 달성 여부와 그 이유 판단

## 범위

1. `L3PreservedInfoFrame`은 코드가 유지한다.
2. `L3OperationFrame` 또는 동등한 구조를 만들어 코드 운영 상태를 분리한다.
3. `L3AchievementFrame`은 LLM 판단 결과로 재정의한다.
4. L3 prompt를 작성한다.
5. LLM 입력에는 다음을 포함한다.
   - L1 goal frame
   - L2 query plan/frame
   - search_docs distillation
   - read_doc distillation
   - LLoopControlFrame 목록
   - tool budget frame 목록
6. LLM 출력에는 다음을 둔다.
   - `achievement_status`
   - `achievement_reason`
   - `macro_achievement_status`
   - `macro_achievement_reason`
   - `micro_achievement_status`
   - `micro_achievement_reason`
   - `preserved_info_ids`
   - `source_mode`
   - `claim_alignment`
   - `source_data_ids`
7. 코드는 LLM 판단문을 수정하지 않고 schema 검증만 한다.

## 원칙

1. 코드가 `candidate_count > 0`을 확인하는 것은 절대정보다.
2. "목표가 달성됐다"는 의미판단은 LLM 또는 인간 문서의 상대정보다.
3. L3가 만든 판단은 source bundle을 가진 혼합정보로 Node2에 넘긴다.
4. L3는 문서 내용의 최종 진실성을 판단하지 않는다.

## 완료 기준

1. L3 LLM call이 기록된다.
2. 코드 운영 상태와 LLM 달성 판단이 별도 frame으로 분리된다.
3. 기존 `CODE:OPERATION_CHECK` 이유문은 제거되거나 operation label로 격하된다.
4. Node2가 L3 LLM 판단을 혼합정보로 받을 수 있다.
5. smoke test가 L3 LLM 판단, fallback, source bundle을 검증한다.

