# ORDER 066: Metainfo Audit Inventory

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: 코드가 절대정보, 상대정보, 혼합정보를 섞어 쓰는 문제를 확인한 감사  
**목표**: 기존 코드와 스키마의 모든 주요 출력 필드를 절대정보, 상대정보, 혼합정보로 분류하는 감사 표를 만든다.

## 배경

현재 프로젝트는 trace, DataStore, 도구, LLM 호출 기록의 뼈대는 갖췄다.  
하지만 일부 필드는 코드가 쓴 자연어인지, LLM이 쓴 자연어인지, 도구나 문서에서 복사된 문장인지 사용자가 헷갈릴 수 있다.

이 발주서는 코드를 바로 바꾸기 전에 무엇이 위험한지 고정하는 작업이다.

## 범위

1. 주요 schema class의 필드를 전부 분류한다.
2. 각 필드에 다음 항목을 붙인다.
   - `info_class`: `absolute`, `relative`, `mixed`
   - `generated_by`: `CODE`, `LLM`, `TOOL`, `DOCUMENT`, `USER`, `UNKNOWN`
   - `code_write_allowed`: 코드가 새로 써도 되는지
   - `code_copy_allowed`: 코드가 복사만 해도 되는지
   - `semantic_judgement_status`: 의미판단 실행 여부
3. `reason`, `summary`, `purpose`, `expected_use`, `achievement_status` 계열을 우선 감사한다.
4. 감사 결과를 개발 지도 또는 실행 기록에 남긴다.
5. 감사 결과는 구현 변경의 기준 문서가 된다.

## 원칙

1. 절대정보는 코드가 쓸 수 있다.
2. 상대정보는 코드가 새로 쓰면 안 된다.
3. 혼합정보는 출처 연결이 있어도 진실이 되지 않는다.
4. 코드가 복사한 문장은 `copied_from`을 가져야 한다.
5. 코드가 만든 상태 라벨은 자연어 이유문과 분리한다.

## 완료 기준

1. 감사 표가 존재한다.
2. 최소한 `MemoryPacketPayload`, `RoutingDecisionFrame`, `L1GoalFrame`, `L2QueryPlanFrame`, `ToolChoiceFrame`, `ToolUseBudgetFrame`, `LLoopControlFrame`, `L3AchievementFrame`, `MetainfoBoundary`, `ReportFrame`이 포함된다.
3. 코드가 새로 쓰면 안 되는 필드 목록이 분명하다.
4. 다음 발주서들이 이 감사 표를 기준으로 구현될 수 있다.

