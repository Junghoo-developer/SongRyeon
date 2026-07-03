# ORDER 120: Tool Use Budget Query Count Consistency Diagnostic v0

## 상태

발주서 초안.

사용자 승인 후 구현한다.

## 목표

`ToolUseBudgetFrame.query_count must not exceed max_query_attempts`로 `structure_failed`가 발생하는 원인을 찾고, 같은 종류의 예산 불일치가 다시 발생할 때 어느 frame/source/route/L run에서 깨졌는지 즉시 추적 가능하게 한다.

이번 발주의 목적은 예산을 임의로 늘리거나 질문을 휴리스틱으로 분류해 우회하는 것이 아니다.

핵심은 다음이다.

```text
query_count가 왜 max_query_attempts를 넘었는지 찾는다.
schema validator를 약화하지 않는다.
예산 불일치가 생기면 실패 지점을 정직하게 드러낸다.
```

## 배경

ORDER_119 구현 후 live 테스트에서 `structure_failed` fallback은 정직하게 작동했다.

사용자 입력:

```text
지금 송련의 말하기 모드 설계가 너무 빡빡한지, 아니면 적절한지 의견을 말해줘. 단, 이건 네 해석이라는 점을 밝혀줘.
```

출력:

```text
상태: structure_failed
trace/data: 0 / 0
structure_failure_stage: run_dry_turn
structure_failure_node: unknown
structure_failure_exception: ValueError
structure_failure_reason: ToolUseBudgetFrame.query_count must not exceed max_query_attempts
```

의미:

- ORDER_119의 fallback 정직성은 작동했다.
- 이제 숨겨져 있던 진짜 실패 원인이 보인다.
- 실패 원인은 `ToolUseBudgetFrame`의 count consistency 문제다.

이 입력은 의견/해석 요청에 가깝다.
그런데 런타임은 `run_dry_turn` 중 `ToolUseBudgetFrame.query_count > max_query_attempts` 상태로 터졌다.

따라서 다음을 감사해야 한다.

```text
1. 의견 요청인데 왜 tool budget/query budget frame이 생성됐는가?
2. max_query_attempts가 0 또는 낮은 값인데 query_count가 증가했는가?
3. ToolUseBudgetFrame 생성 시 query_count 초기값 또는 누적값이 잘못 들어가는가?
4. ORDER_112 whole-document/search budget 변경과 충돌했는가?
5. schema validator가 맞고 생성 코드가 틀린 것인가?
6. 실패 전 budget frame/data id가 기록되지 않아 trace/data 0으로 끝나는 구조인가?
```

## 구현 범위

### 1. ToolUseBudgetFrame 생성 경로 감사

다음 파일을 우선 감사한다.

```text
songryeon_core/core/schemas.py
songryeon_core/loops/l_loop.py
songryeon_core/loops/l_loop_budget.py
songryeon_core/runtime/dry_run.py
songryeon_core/runtime/defaults.py
songryeon_core/tools/document_tools.py
songryeon_core/tools/document_context_pack.py
songryeon_core/runtime/smoke_test.py
tests/test_order_112_document_context_pack.py
```

확인할 것:

- `ToolUseBudgetFrame` 필드 정의
- `query_count`
- `max_query_attempts`
- `tool_calls`
- `max_tool_calls`
- `read_doc_count`
- `max_read_doc`
- L1 budget request
- code budget approval
- document context pack 또는 search/read_doc loop에서 count를 올리는 위치

### 2. query_count consistency diagnostic 추가

예산 frame 생성 또는 검증 실패 시 다음 정보를 남길 수 있게 한다.

후보 필드:

```text
budget_failure_type
budget_failure_reason
budget_failure_frame_id
budget_failure_source_data_ids
budget_failure_route
budget_failure_l_run_id
budget_failure_query_count
budget_failure_max_query_attempts
budget_failure_tool_calls
budget_failure_max_tool_calls
budget_failure_read_doc_count
budget_failure_max_read_doc
budget_failure_stage
```

주의:

- user-facing 최종 답변에 raw internal id를 과도하게 노출하지 않는다.
- pretty runtime 또는 JSON summary에는 진단용 id를 남길 수 있다.
- trace/data가 0으로 끝나는 경우에도 최소 실패 reason은 유지한다.

### 3. schema validator는 약화하지 않는다

다음 validation은 유지한다.

```text
query_count <= max_query_attempts
tool_calls <= max_tool_calls
read_doc_count <= max_read_doc
```

만약 현재 validator가 올바른 상태라면, validator를 완화하지 않는다.

이번 발주는 다음을 금지한다.

```text
if query_count > max_query_attempts:
    query_count = max_query_attempts
```

같은 조용한 덮어쓰기 금지.

단, 생성 코드가 잘못된 값을 만들고 있다면 생성 코드를 고친다.

### 4. opinion/relative_allowed 질문의 L route 유입 여부는 진단만 한다

이번 실패 입력은 의견/해석 요청이다.

하지만 이번 발주의 목적은 router를 휴리스틱으로 고치는 것이 아니다.

따라서 다음은 금지한다.

```text
"의견"이라는 단어가 있으면 route=2로 고정
"해석"이라는 단어가 있으면 L 금지
```

대신 다음을 기록한다.

```text
route selected
route_source
answer_basis_mode if reached
whether L loop entered
whether ToolUseBudgetFrame was created before/after route decision
```

라우팅 품질 문제는 별도 발주로 미룬다.

### 5. structure_failed와 budget failure 연결

ORDER_119에서 추가한 structure failure diagnostics와 연결한다.

`structure_failed` reason이 budget consistency violation이면 fallback/runtime에 다음처럼 보이게 한다.

```text
structure_failure_stage: run_dry_turn
structure_failure_exception: ValueError
structure_failure_reason: ToolUseBudgetFrame.query_count must not exceed max_query_attempts
budget_failure_type: query_count_exceeded_max_query_attempts
budget_failure_query_count: N
budget_failure_max_query_attempts: M
```

가능하면 exception message를 parsing해서 type만 뽑는 것이 아니라, 생성/검증 지점에서 구조화된 진단을 남긴다.

### 6. 테스트 추가

pytest 또는 smoke case를 추가한다.

#### A. ToolUseBudgetFrame validator 유지 테스트

fixture:

```text
query_count=max_query_attempts + 1
```

기대:

- validation 실패
- validator를 약화하지 않았음을 확인

#### B. valid budget frame 생성 테스트

fixture:

```text
query_count <= max_query_attempts
tool_calls <= max_tool_calls
read_doc_count <= max_read_doc
```

기대:

- validation 통과

#### C. live failure reproduction fixture

가능하면 live 입력과 유사한 dry fixture:

```text
지금 송련의 말하기 모드 설계가 너무 빡빡한지, 아니면 적절한지 의견을 말해줘. 단, 이건 네 해석이라는 점을 밝혀줘.
```

기대:

- 더 이상 `ToolUseBudgetFrame.query_count must not exceed max_query_attempts`로 structure_failed가 발생하지 않음
- 만약 다른 이유로 실패한다면 structure diagnostics가 정확히 표시됨

#### D. budget failure diagnostics fixture

의도적으로 budget inconsistency를 발생시키는 작은 fixture를 만든다.

기대:

- `budget_failure_type`
- `budget_failure_query_count`
- `budget_failure_max_query_attempts`
- `budget_failure_stage`

가 확인된다.

#### E. 기존 ORDER_112 document context pack 테스트 유지

ORDER_112에서 추가한 whole-document packing과 search/read_doc budget 테스트가 깨지지 않는지 확인한다.

## 검증 명령

반드시 다음 순서를 따른다.

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

가능하면 live 재검증:

```powershell
python main.py qwen-turn "지금 송련의 말하기 모드 설계가 너무 빡빡한지, 아니면 적절한지 의견을 말해줘. 단, 이건 네 해석이라는 점을 밝혀줘." --timeout 240 --pretty
```

기대:

- `structure_failed`가 사라지는지 확인한다.
- 남아 있다면 `budget_failure_*` 진단이 보이는지 확인한다.
- answer-basis selector가 도달했는지 확인한다.

## 금지

- ToolUseBudgetFrame validator를 약화하지 마라.
- query_count를 조용히 max_query_attempts로 덮어쓰지 마라.
- 휴리스틱으로 "의견" 질문을 route=2로 강제하지 마라.
- code가 answer_basis_mode를 의미적으로 대신 고르지 마라.
- budget failure를 `mixed_or_uncertain` 의미 판단으로 위장하지 마라.
- ORDER_119 structure_failed 정직성 fallback을 되돌리지 마라.
- node_4 guard를 약화하지 마라.
- W/R loop 열지 마라.
- scheduler/외부 DB/vector DB/장기기억 DB 건드리지 마라.
- same-turn L reroute 횟수 늘리지 마라.
- node_4 자동 재작성 루프 열지 마라.

## 완료 보고에 반드시 포함할 것

- query_count가 max_query_attempts를 초과한 실제 원인
- 수정한 생성 경로 또는 진단 경로
- validator를 유지했는지 여부
- 추가한 budget failure diagnostics 필드
- structure_failed diagnostics와 어떻게 연결했는지
- router/answer_basis를 건드렸는지 여부
- 추가한 pytest/smoke 이름
- compileall / pytest / smoke-test 결과
- 가능하면 live 재검증 결과
- 이번 발주에서 일부러 하지 않은 것
