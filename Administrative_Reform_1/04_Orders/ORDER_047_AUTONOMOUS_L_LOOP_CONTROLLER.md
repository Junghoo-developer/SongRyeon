# ORDER 047: Autonomous L Loop Controller

**상태**: 정식 발주서  
**승격일**: 2026-06-21  
**출처**: 사용자 요청 "알아서 척척 검색"  
**목표**: L루프가 단일 `search_docs` 호출로 끝나지 않고, 제한된 횟수 안에서 검색, 문서 읽기, query 수정, 중단 판단을 스스로 반복하게 한다.

## 배경

현재 L루프는 다음 흐름으로 고정되어 있다.

```text
L1 -> L2 -> search_docs 1회 -> L3
```

자율 검색을 하려면 L루프 내부에 "다음 도구를 쓸지, 검색어를 바꿀지, 충분하니 멈출지"를 결정하는 controller가 필요하다.

## 범위

1. `LLoopControlFrame` 스키마를 만든다.
2. controller는 `continue_search`, `read_document`, `stop_success`, `stop_failed` 중 하나를 선택한다.
3. 각 선택에는 이유와 근거 trace/data ID를 붙인다.
4. 최대 반복 횟수와 최대 도구 호출 횟수를 둔다.
5. L3AchievementFrame은 최종 controller 상태를 반영한다.

## 원칙

1. 자율성은 무제한 반복이 아니다. 항상 budget 안에서만 움직인다.
2. 도구 실행은 코드가 맡고, LLM은 다음 행동 후보를 제안한다.
3. 같은 query 반복이나 같은 문서 반복 읽기는 효율 정책에서 막는다.

## 완료 기준

1. L루프가 최대 N회까지 도구 호출을 반복할 수 있다.
2. 각 반복마다 `LLoopControlFrame`이 저장된다.
3. stop 조건이 없으면 budget 초과 실패 신호를 남긴다.
4. dry run과 smoke test가 통과한다.
