# ORDER 119: Structure Failed Honesty And Answer Basis Failure Diagnostics v0

## 상태

발주서 초안.

사용자 승인 후 구현한다.

## 목표

`structure_failed`가 발생했을 때, 송련이 문서 검색을 한 척하거나 엉뚱한 fallback 답변을 만들지 않게 한다.

또한 ORDER_118 이후 추가된 `node_2 answer_basis_mode selector`가 live에서 실패하는 원인을 runtime, terminal, fallback 출력에 명확히 드러내게 한다.

이번 발주의 핵심은 질문을 휴리스틱으로 분류해서 fallback 답변을 예쁘게 만드는 것이 아니다.

핵심은 다음이다.

```text
실패했으면 실패했다고 말한다.
어느 단계에서 실패했는지 기록한다.
없는 검색 결과를 있는 것처럼 말하지 않는다.
node_2 answer_basis selector 실패 원인을 숨기지 않는다.
```

## 배경

최근 live 테스트에서 다음 문제가 확인됐다.

### 사례 1

사용자 입력:

```text
지금 smoke 결과 기준으로 뭐가 통과했어?
```

결과:

- 최종 답변은 pass
- 그러나 `node_2 answer basis`는 실패했다.

```text
node_2 answer basis:
mode=mixed_or_uncertain
generated_by=CODE:FALLBACK
semantic=failed
reason_codes=['llm_mode_selection_failed']
```

즉 ORDER_118의 핵심인 node_2 answer-basis selector가 live에서 성공한 증거가 없다.

### 사례 2

사용자 입력:

```text
방금 smoke-test를 실제로 다시 돌린 거야? 아니면 과거 실행기록을 읽은 거야? 둘을 구분해서 답해줘.
```

결과:

- route=2
- L loop 없음
- read_documents=0
- search_candidates=0
- selected recent memory context=1
- 최종 답변은 대체로 적절했다.
- 하지만 node_2 answer basis는 여전히 `CODE:FALLBACK`이었다.

```text
mode=mixed_or_uncertain
generated_by=CODE:FALLBACK
semantic=failed
reason_codes=['llm_mode_selection_failed']
```

또한 답변에서 "이전 실행 기록(선택된 최근 기억)"처럼 표현되어, 실제 source가 "실행기록 문서"인지 "직전 대화 원문"인지 살짝 흐려졌다.

### 사례 3

사용자 입력:

```text
지금 송련의 말하기 모드 설계가 너무 빡빡한지, 아니면 적절한지 의견을 말해줘. 단, 이건 네 해석이라는 점을 밝혀줘.
```

결과:

```text
상태: structure_failed
trace/data: 0 / 0
LLM_REPORTER=not_run
```

fallback answer:

```text
[CODE/FALLBACK -> CODE/RENDER] ...에 맞춰 내부 문서를 찾았어.
검색 결과 payload를 찾지 못해서 근거 문서 요약은 만들지 못했어.
```

문제:

- 사용자는 의견/해석을 요청했다.
- 그런데 fallback renderer는 문서 검색 실패처럼 말했다.
- trace/data가 0인데도 "내부 문서를 찾았어"라고 말하는 것은 정직하지 않다.
- 이건 질문 유형을 휴리스틱으로 맞히는 문제가 아니라, 실패 상태를 정직하게 렌더링하지 못한 문제다.

## 구현 범위

### 1. structure_failed fallback 정직성 수정

`structure_failed`일 때 fallback answer는 다음 원칙을 따른다.

```text
1. LLM reporter가 실행되지 않았음을 말한다.
2. trace/data가 없거나 불완전하면 그 사실을 말한다.
3. 검색 payload가 없으면 "내부 문서를 찾았다"고 말하지 않는다.
4. 실제로 search/result/read_doc payload가 존재할 때만 검색/문서 읽기를 언급한다.
5. 사용자 질문에 대한 의미 답변을 code가 대신 만들지 않는다.
```

권장 fallback 문구:

```text
이번 턴은 structure_failed 상태라서 송련의 정상 노드 흐름이 끝까지 기록되지 않았어.
node_3 최종 보고도 실행되지 않았고, 확인 가능한 trace/data 기록이 없거나 불완전해.
따라서 사용자 질문에 대한 의미 답변은 만들지 않고, 실패 상태만 보고할게.
```

검색 payload가 실제로 있을 때만:

```text
다만 DataStore에 검색 결과 payload가 남아 있어 그 범위만 재렌더링할 수 있어.
```

라고 말한다.

금지 문구:

```text
내부 문서를 찾았어.
검색 결과 payload를 찾지 못해서...
```

검색 결과 payload가 없는데 위 문장을 쓰면 안 된다.

### 2. structure_failed diagnostics 추가

`qwen-turn`, `qwen-chat`, pretty runtime 또는 fallback response에 structure failure 원인을 더 드러낸다.

가능한 필드 후보:

```text
structure_failure_stage
structure_failure_reason
structure_failure_exception_type
structure_failure_llm_call_data_id
structure_failure_trace_event_id
structure_failure_node
structure_failure_prompt_ref
```

주의:

- exception 전문이나 stack trace를 user-facing 답변에 길게 노출하지 않는다.
- terminal/runtime diagnostic에는 짧은 reason code와 data id를 남긴다.
- 내부 raw ID를 최종 자연어 답변에 무심코 노출하지 않는다.

### 3. node_2 answer-basis selector failure diagnostics

ORDER_118의 answer-basis selector가 live에서 계속 실패하고 있다.

현재는 최종적으로:

```text
CODE:FALLBACK
llm_mode_selection_failed
```

만 보인다.

추가로 다음을 확인 가능하게 한다.

```text
answer_basis_failure_type
answer_basis_llm_call_data_id
answer_basis_trace_event_id
answer_basis_validation_error
answer_basis_raw_text_present
answer_basis_prompt_ref
answer_basis_payload_parse_status
```

terminal/runtime 표시 예:

```text
node_2 answer basis:
  mode=mixed_or_uncertain / generated_by=CODE:FALLBACK / semantic=failed
  reason_codes=['llm_mode_selection_failed']
  failure_type=parse_failed
  llm_call=llm_call:node_2:trace_...
  prompt=node_2_answer_basis_selector_v0.md
```

주의:

- 실패했다고 code가 의미 모드를 대신 고르지 않는다.
- fallback은 계속 `mixed_or_uncertain` + `llm_mode_selection_failed`로 유지한다.
- 이번 발주는 진단 강화이지 휴리스틱 fallback이 아니다.

### 4. selected recent memory source 표현 정직성

최근 기억 context를 근거로 답할 때, node_3가 이것을 실행기록 문서와 혼동하지 않게 한다.

구분해야 할 source 종류:

```text
selected_recent_memory_context:
  - 직전/최근 대화 원문을 code가 복사한 context
  - 문서 원문이 아님
  - 실행기록 문서가 아님

read_documents:
  - L loop 또는 document context pack으로 공급된 문서 원문

runtime_tasks:
  - 현재 턴 실행 순서 장부

trace/data:
  - 현재 턴 내부 기록
```

node_3 prompt 또는 brief reporting rules에 다음 경계를 추가한다.

```text
선택된 최근 기억 context는 과거 대화 원문이지, 실행기록 문서나 새로 읽은 문서가 아니다.
과거 대화 안에서 문서/실행기록이 언급되었더라도, 그것을 직접 읽은 문서처럼 말하지 않는다.
```

### 5. node_3 중복 grounding block 방지

최근 답변에서 code가 만든 첫 `근거 기준:` 블록 뒤에 node_3 본문이 다시 `**근거 기준:**` 블록을 만들었다.

원칙:

```text
근거 기준 블록은 code가 한 번만 만든다.
node_3 LLM은 본문에서 별도 grounding block을 만들지 않는다.
```

보강 방향:

- `node_3_reporter_v0.md`에 "본문 안에 `근거 기준:` 또는 `**근거 기준:**` 제목을 다시 만들지 말라" 추가
- `_strip_accidental_grounding_block()`이 bold 형태의 `**근거 기준:**`도 제거할 수 있는지 검토
- count block은 계속 code가 생성한다.

### 6. 테스트 추가

pytest 또는 smoke case를 추가한다.

#### A. structure_failed fallback no fake search

입력 또는 fixture:

```text
status=structure_failed
trace_count=0
data_record_count=0
search payload 없음
```

기대:

- fallback answer가 "내부 문서를 찾았어"라고 말하지 않음
- "node_3 final reporter not_run" 또는 동등한 상태를 말함
- code가 의미 답변을 대신 만들지 않음

#### B. structure_failed with actual search payload

입력 또는 fixture:

```text
status=structure_failed
search payload 있음
read_doc payload 있음/없음
```

기대:

- 실제 payload가 있을 때만 검색/문서 근거를 언급
- payload가 없는 항목은 없다고 말함

#### C. answer-basis failure diagnostics

fixture:

```text
node_2 answer basis selector parse_failed 또는 validation_failed
```

기대:

- fallback mode는 그대로 `mixed_or_uncertain`
- reason_codes는 `["llm_mode_selection_failed"]`
- terminal/runtime에 failure_type 또는 validation error 요약 표시
- llm_call_data_id 또는 trace id가 diagnostic으로 남음

#### D. selected recent memory is not document

fixture:

```text
selected_recent_memory_context 있음
read_documents=0
```

기대:

- node_3 payload/reporting rules가 selected recent memory를 문서로 부르지 않음
- 최종 답변 또는 테스트용 renderer가 "실행기록 문서"라고 오표현하지 않음

#### E. duplicate grounding block stripping

fixture:

```text
body_markdown starts with "**근거 기준:**"
```

기대:

- final rendered markdown에 code-generated grounding block만 남음
- LLM이 만든 중복 grounding block은 제거됨

## 검증 명령

반드시 다음 순서를 따른다.

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

## 금지

- 휴리스틱으로 사용자 질문을 문서/의견/기억 질문으로 분류해서 fallback 의미 답변을 만들지 마라.
- code가 answer_basis_mode를 의미적으로 대신 고르지 마라.
- `mixed_or_uncertain` fallback을 의미 판단처럼 보이게 하지 마라.
- 검색 payload가 없는데 "내부 문서를 찾았다"고 말하지 마라.
- selected recent memory context를 실행기록 문서나 read_document처럼 부르지 마라.
- node_4 guard를 약화하지 마라.
- W/R loop 열지 마라.
- scheduler/외부 DB/vector DB/장기기억 DB 건드리지 마라.
- same-turn L reroute 횟수 늘리지 마라.
- node_4 자동 재작성 루프 열지 마라.

## 완료 보고에 반드시 포함할 것

- structure_failed fallback 문구를 어디서 고쳤는지
- structure_failed diagnostics에 어떤 필드를 추가했는지
- answer-basis selector failure diagnostics에 어떤 필드를 추가했는지
- selected recent memory source 표현 경계를 어디에 추가했는지
- 중복 grounding block 방지를 어떻게 했는지
- 추가한 pytest/smoke 이름
- compileall / pytest / smoke-test 결과
- 이번 발주에서 일부러 하지 않은 것
