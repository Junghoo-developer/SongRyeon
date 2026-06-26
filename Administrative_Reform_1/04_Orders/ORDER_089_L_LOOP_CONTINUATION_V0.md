# ORDER 089: L Loop Continuation v0

## 구현 갱신: 2026-06-24

추가 완료:

- revision tool attempt 이후 L3가 결과를 다시 보존/판정하는 `run_l3_revision_result_keeper`를 추가했다.
- 재판정 결과는 기존 고정 ID가 아니라 `L3:revision_preserved_info:0001`, `L3:revision_achievement:0001`처럼 attempt별 ID에 기록한다.
- continuation controller가 기본 `L3:achievement_frame`만 보지 않고, 지정된 attempt별 L3 판정과 L2 revision query frame을 읽을 수 있게 확장했다.
- smoke-test에서 `revision tools -> L3 revision recheck -> continuation decision`까지 독립적으로 검증했다.

아직 남은 것:

- 실제 live L루프 그래프에서 `continue -> 0 -> L2 -> tools -> L3 -> continuation`을 자동 반복하도록 배선하는 일.
- runtime pretty view에 revision recheck와 second continuation을 보기 좋게 표시하는 일.
- controller 성공/실패 프레임을 revision attempt 이후 어떻게 다시 확정할지 결정하는 일.

## 상태

정식 발주서.

부분 구현.

2026-06-24 현재 1단계 스키마, 2단계 controller 판단 함수, 3단계 0 summary helper, L2 revision input builder, L2 revision query planner, L2 revision query frame 확정, revision tool attempt 구현 완료.

실제 `continue -> 0 -> L2 -> tools -> L3` 그래프 배선, L3 재판정, runtime view 연결은 아직 구현 대기.

이 문서는 `ORDER_086`의 설계 메모를 바탕으로, 실제 코드에 넣을 첫 그래프 배선 목표를 좁혀 쓴다.

## 한 줄 목표

L3가 목표 미달을 판단했을 때 곧바로 route=2로 흘려보내지 말고, L루프 내부에서 제한적으로 `L3 -> 0 -> L2` 재검색 경로를 연다.

## 배경

현재 L루프는 대체로 다음 순서로 돈다.

```text
1 -> 0 -> L1 -> L2 -> tools -> L3 -> 0 -> 1 -> 0 -> 2 -> 3 -> 4
```

이 구조는 문서를 한 번 찾아 답하는 데는 충분하다.

하지만 최근 테스트에서 다음 문제가 반복해서 드러났다.

```text
L3가 partial/failed/missing을 감지해도,
그래프는 결국 route=2로 넘어가고,
node_3는 주어진 재료 안에서만 정직하게 답하며,
node_4는 grounding만 맞으면 pass할 수 있다.
```

즉, 현재 구조는 다음 둘을 아직 충분히 분리하지 못한다.

```text
grounding success: 근거 밖 헛소리를 하지 않았는가?
task success: 사용자의 실제 요청을 해결했는가?
```

이번 발주서는 `task success`가 부족할 때 L루프 안에서 한 번 더 해볼 길을 만드는 것이 목표다.

## 핵심 원칙

### 1. 휴리스틱 금지

금지한다.

```text
사용자 문장에 "방금", "찾아", "문서", "task"가 있으면 재검색한다.
L3 reason 문자열에 특정 단어가 있으면 재검색한다.
검색 결과 제목 문자열을 코드가 의미 해석해서 재검색한다.
```

재검색 여부는 구조화된 상태와 예산으로만 결정한다.

허용한다.

```text
L3AchievementFrame의 구조화 필드
L3 goal match 관련 구조화 필드
tool budget의 절대 카운트
이미 읽은 문서 수
이미 실행한 continuation attempt 수
```

### 2. L3는 라우터가 아니다

L3는 비판자와 판정자다.

L3가 직접 다음 노드를 호출하지 않는다.

대신 L3는 다음 정보를 남긴다.

```text
거시 목표 달성 여부
미시 목표 달성 여부
문서 목표 매칭 여부
의미적 목표 매칭 여부
실패/부분성공 사유
다음 시도에 필요한 수정 방향
```

실제 재시도 실행은 L루프 controller/code가 담당한다.

### 3. 0을 끼운다

L3에서 L2로 바로 돌아가지 않는다.

가벼운 경로이지만 0의 기억 공급 역할은 보존한다.

MVP 경로는 다음이다.

```text
L3
-> controller continuation check
-> 0(l3_continuation_summary_for_L2)
-> L2(revision)
-> tools
-> L3
```

여기서 0은 L3의 실패/부분성공 사유, 이전 검색어, 읽은 문서, 아직 읽지 않은 후보, 예산 상태를 L2가 다시 보기 좋게 압축한다.

### 4. 1까지 돌아가지 않는다

이번 MVP에서는 다음 경로를 열지 않는다.

```text
L3 -> 0 -> 1 -> 0 -> L
```

이 경로는 원칙적으로 가능하지만 너무 무겁다.

L1 목표 자체가 틀린 경우는 나중에 별도 발주서에서 다룬다.

### 5. 최대 3회

재검색은 최대 3회까지만 허용한다.

이 숫자는 똑똑한 판단이 아니라 안전장치다.

```text
max_l_continuation_attempts = 3
```

3회 안에 해결하지 못하면 route=2로 넘어가되, node_3에게 partial/failed 상태와 부족한 점을 정직하게 전달한다.

## 목표 그래프

기본 성공 경로:

```text
L1
-> L2
-> tools
-> L3(achieved)
-> 0(loop_return_summary)
-> 1
-> 0(final_trace_for_2)
-> 2
```

재시도 경로:

```text
L1
-> L2 attempt 1
-> tools
-> L3(partial/failed/missing)
-> controller continuation check
-> 0(l3_continuation_summary_for_L2)
-> L2 attempt 2
-> tools
-> L3
```

최대 반복:

```text
attempt 1
attempt 2
attempt 3
```

소진 후:

```text
L3(partial/failed)
-> 0(loop_return_summary)
-> 1
-> 0(final_trace_for_2)
-> 2
-> 3: 부족한 점을 정직하게 보고
-> 4: 근거 밖 주장 검사
```

## 새로 필요한 데이터

### LLoopContinuationFrame

L루프 controller가 재시도 여부를 기록하기 위한 frame.

후보 필드:

```text
frame_id
turn_id
attempt_index
max_attempts
continuation_status
continuation_reason_code
source_l3_achievement_id
source_l2_query_frame_id
previous_query_text
read_doc_ids
unread_candidate_doc_ids
tool_budget_status
next_target_node
source_trace_ids
source_data_ids
schema_name
schema_version
```

`continuation_status` 후보:

```text
continue
stop_achieved
stop_budget_exhausted
stop_no_actionable_gap
stop_failed_final
```

중요:

`continuation_reason_code`는 코드가 쓰는 절대/조건 라벨이다.

예:

```text
CODE_STATUS:l3_not_achieved_and_attempts_remaining
CODE_STATUS:l3_achieved
CODE_STATUS:max_continuation_attempts_reached
CODE_STATUS:no_unread_candidate_or_revision_plan
```

LLM의 의미 판단문을 코드 reason으로 둔갑시키지 않는다.

### L2RevisionInputFrame

L2가 재검색을 할 때 받는 입력 frame.

후보 필드:

```text
frame_id
turn_id
attempt_index
macro_goal
micro_goal
previous_query_text
previous_tool_name
read_document_names
unread_candidate_summaries
l3_goal_status
l3_goal_match_status
l3_semantic_goal_match_status
l3_feedback_text
remaining_budget
source_data_ids
source_trace_ids
schema_name
schema_version
```

주의:

`l3_feedback_text`는 LLM 판단에서 온 혼합 정보다.

코드는 이 텍스트의 의미를 해석해 재시도 여부를 결정하지 않는다.

L2가 다음 검색 계획을 세울 때 참고하는 재료로만 사용한다.

## L2 변경

L2는 두 모드를 가진다.

```text
initial_query_plan
revision_query_plan
```

`initial_query_plan`은 지금처럼 L1 목표와 0의 기억 공급을 바탕으로 첫 검색 계획을 만든다.

`revision_query_plan`은 다음을 함께 본다.

- 기존 검색어
- 기존 검색 결과
- 이미 읽은 문서
- 아직 읽지 않은 후보
- L3의 목표 미달 판단
- 남은 예산

L2는 재검색 계획을 만들 수 있다.

하지만 실제 도구 실행은 여전히 controller/code가 예산 안에서 수행한다.

## L3 변경

L3는 다음을 더 명확히 해야 한다.

```text
achieved: 현재 재료로 사용자 요청에 충분히 답할 수 있음
partial: 관련 재료는 있으나 요청을 완전히 만족하지 못함
failed: 현재 재료가 요청 해결에 부적합함
missing: 특정 요구 문서/근거가 발견되지 않음
```

L3는 실패 사유를 남기되, 다음 라우팅을 직접 실행하지 않는다.

필요하면 다음 시도에 유용한 제안을 남길 수 있다.

예:

```text
다른 검색어가 필요함
읽지 않은 상위 후보를 확인할 필요가 있음
명시 문서명이 있으므로 read_artifact가 적합함
현재 문서는 질문과 부분적으로만 관련됨
```

이 제안은 혼합 정보로 기록한다.

## 0 변경

0은 L3와 L2 사이에서 다음 mode를 가진다.

```text
l3_continuation_summary_for_L2
```

0이 L2에게 공급할 내용:

- L1 거시 목표
- L1 미시 목표
- L3 판정 상태
- L3 실패/부분성공 사유
- 이전 L2 검색어
- 이전 도구 선택
- 이미 읽은 문서
- 아직 읽지 않은 후보
- 남은 예산
- 현재 attempt index

0은 의미 비판을 하지 않는다.

0은 L2가 다음 판단을 하기 좋게 재료를 정리한다.

## controller 변경

L루프 controller는 각 L3 이후 다음을 수행한다.

```text
1. L3 status를 읽는다.
2. attempt count를 읽는다.
3. tool budget을 읽는다.
4. 계속할 수 있으면 LLoopContinuationFrame(status=continue)를 기록한다.
5. 0의 l3_continuation_summary_for_L2를 호출한다.
6. L2 revision_query_plan을 호출한다.
7. 도구를 실행한다.
8. L3를 다시 호출한다.
```

계속하지 않는 경우:

```text
LLoopContinuationFrame(status=stop_...)
-> 기존 loop_return_summary 경로로 빠진다.
```

## task ledger 반영

Task Ledger v0는 이 새 동선을 그대로 기록해야 한다.

예상 동선:

```text
L:L_loop
```

MVP에서는 L루프 내부 세부 task를 최종 ledger에 낱개로 풀지 않아도 된다.

다만 L루프 내부 record에는 continuation attempt가 남아야 한다.

나중에 scheduler/task queue가 확장되면 다음처럼 쪼갤 수 있다.

```text
L2 attempt task
tool search task
tool read task
L3 judge task
0 continuation summary task
```

이번 발주서에서는 여기까지 쪼개지 않는다.

## node_3 / node_4 영향

node_3는 최종적으로 다음을 받아야 한다.

```text
성공한 경우: 최종 읽은 문서와 보존 정보
부분성공/실패한 경우: 무엇을 시도했고 무엇이 부족했는지
```

node_3가 "성공"처럼 꾸미면 안 된다.

node_4는 여전히 grounding을 검사한다.

다만 이번 발주서는 node_4가 task success까지 검사하게 만드는 발주서가 아니다.

그건 별도 후속 발주서로 둔다.

## 구현 순서

### 1단계: 스키마

- `LLoopContinuationFrame`
- `L2RevisionInputFrame`
- validator 추가
- smoke-test용 최소 fixture 추가

### 2단계: controller

- L3 이후 continuation decision 함수 추가
- 최대 3회 제한
- achieved면 기존 경로 유지
- partial/failed/missing이면 예산이 있을 때 재시도

### 3단계: 0 summary

- `l3_continuation_summary_for_L2` memory packet mode 추가
- L2 revision에 필요한 정보만 압축

### 4단계: L2 revision

- L2 query planner에 revision mode 추가
- 이전 실패/부분성공 정보를 payload로 공급
- 새 검색 계획을 schema로 강제

### 5단계: runtime view

runtime에 다음을 표시한다.

```text
- L continuation: attempt=2/3 / status=continue / reason=...
- L2 revision plan: ...
```

### 6단계: smoke-test

다음 사례를 테스트한다.

```text
1. 첫 시도 achieved면 재시도하지 않는다.
2. partial이고 budget이 남으면 재시도한다.
3. max attempts에 도달하면 멈춘다.
4. stop 후 node_3가 부족한 점을 정직하게 받는다.
5. raw 내부 ID가 node_3 답변으로 새지 않는다.
```

## 구현 금지

- 사용자 문장 키워드 기반 재시도 분기 금지.
- L3 reason 문자열을 코드가 의미 해석해서 재시도 여부를 정하는 것 금지.
- 무한 루프 금지.
- L3가 직접 라우팅하는 구조 금지.
- 이번 MVP에서 W/R/C/M 루프와 섞기 금지.
- node_4를 task success 판정자로 확장하는 것 금지.

## 성공 기준

다음이 가능해야 한다.

```text
사용자 요청에 맞는 문서를 첫 검색에서 못 찾음
-> L3가 partial/failed/missing을 기록
-> controller가 예산과 attempt를 확인
-> 0이 L2 revision용 요약을 공급
-> L2가 다른 검색 계획을 생성
-> tools가 재실행
-> L3가 다시 판정
```

그리고 runtime에 이 과정이 보여야 한다.

최종 목표는 이것이다.

```text
송련이 모르면 바로 답변으로 도망가지 않고,
자기가 무엇을 못 찾았는지 보고,
제한된 횟수 안에서 다시 찾아본 뒤,
그래도 부족하면 부족하다고 말한다.
```
