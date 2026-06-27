# ORDER 110: Node4 Recent Memory Utterance Guard v0

## 상태

발주서 초안.

이 발주서는 ORDER_109 완료 이후에 구현한다.

## 배경

ORDER_109가 완료되면 node_3는 선택된 최근 원문 기억을 보고 사용자에게 이전 대화 내용을 말할 수 있다.

그 순간 새로운 위험이 생긴다.

위험:

```text
node_3가 선택된 원문에 없는 말을 "아까 네가 말했다"고 주장
selector의 mixed 판단을 code fact처럼 말함
truncated 원문을 전체 대화처럼 단정
raw internal id를 사용자 답변에 노출
이전 턴 원문을 과잉 해석해 감정/의도/장기 목표를 단정
```

따라서 node_4가 최근 기억 발화에 특화된 검수 규칙을 가져야 한다.

## 목표

node_4가 최종 report 안의 최근 기억 관련 발화가 `SelectedRecentMemoryContextFrame`과 `Node3InputBriefFrame` 범위를 벗어나지 않는지 검사한다.

핵심 문장:

```text
node_3가 "아까 네가 말했다"고 말하려면, 그 말은 selected recent memory context 안에 있어야 한다.
```

## 구현 범위

### 1. node_4 input에 selected memory context 명시

node_4 gatekeeper 입력 payload에 다음을 포함한다.

```text
selected_recent_memory_contexts
selected_recent_memory_context_frame_id
memory_selection_status
memory_selection_info_class
```

node_4 prompt 또는 code guard가 이 필드를 볼 수 있어야 한다.

### 2. 기억 발화 검수 규칙 추가

node_4가 다음을 반려할 수 있게 한다.

반려 후보 reason code:

```text
CODE_STATUS:recent_memory_claim_without_selected_context
CODE_STATUS:recent_memory_claim_not_supported_by_context
CODE_STATUS:recent_memory_truncated_context_overclaim
CODE_STATUS:recent_memory_selector_judgement_overstated_as_fact
CODE_STATUS:recent_memory_internal_id_leak
```

의미:

1. selected context가 없는데 "아까 네가 말했다"류 발화를 함.
2. selected context 안에 없는 구체 내용을 이전 대화라고 주장함.
3. truncated context만 보고 전체 이전 대화를 단정함.
4. selector의 관련성 판단을 코드 사실처럼 표현함.
5. raw frame id, trace id, data id를 사용자 답변에 노출함.

### 3. code guard와 LLM review의 역할 분리

code가 할 수 있는 검사:

- selected context count가 0인지
- report에 raw internal id 패턴이 노출됐는지
- report가 selected raw text에 포함된 짧은 literal을 그대로 말하는지 여부
- truncation flag가 있는데 "전체 대화" 같은 표현이 있는지 간단히 감지

code가 하면 안 되는 검사:

- 문장 의미가 충분히 같은지 판정
- 과거 발화의 의도 해석 진위 판정
- 기억 사용이 자연스러운지 평가

LLM node_4가 할 수 있는 검사:

- 최종 답변의 기억 관련 주장과 selected context가 의미적으로 어긋나는지 검토
- 과잉 해석인지 판단
- 반려 이유를 mixed 정보로 작성

### 4. node_4 gatekeeper frame 필드 보강

후보 필드:

```text
recent_memory_guard_status
recent_memory_guard_reason_codes
recent_memory_claim_count
unsupported_recent_memory_claim_count
recent_memory_internal_id_leak_count
recent_memory_revision_targets
```

기존 `gate_status`, `revision_targets`, `contradictions`는 유지한다.

### 5. safe blocking answer 유지

node_4가 최근 기억 발화 문제로 `needs_revision` 또는 `failed`를 내면, 기존 safe blocking answer를 유지한다.

중요:

- 잘못된 기억 발화를 사용자에게 그대로 내보내지 않는다.
- node_4 반려 이유는 debug/runtime에는 보이되, 사용자 답변은 안전하게 막는다.

### 6. terminal/runtime 표시

runtime view에 다음을 표시한다.

예시:

```text
node_4 recent memory guard: pass
node_4 recent memory guard: needs_revision / unsupported=1 / internal_id_leak=0
```

## 메타정보 분류

절대정보:

- selected context count
- raw text 존재 여부
- truncation flag
- internal id leak count
- node_4 gate status
- reason code

혼합정보:

- node_4 LLM이 "이 기억 주장은 selected context에 근거하지 않는다"고 판단한 설명
- 과잉 해석 여부 판단

code guard는 의미 판단을 흉내 내지 않는다.

## 비범위

이번 발주에서 하지 말 것:

```text
node_5 기억 압축기 구현
장기기억 DB
vector DB
memory graph
자동 재작성 루프
node_4 -> node_3 자동 remand 실행
raw 원문 삭제
기억 요약 승인
```

node_4는 반려할 수 있지만, 이번 발주에서 자동 재작성까지 열지 않는다.

## 감사/수정 후보 파일

```text
songryeon_core/core/schemas.py
songryeon_core/nodes/node_4_gatekeeper.py
songryeon_core/prompts/node_4_gatekeeper_v0.md
songryeon_core/runtime/dry_run.py
songryeon_core/runtime/terminal_view.py
songryeon_core/runtime/smoke_test.py
```

실제 파일명이 다르면 현재 node_4 구현 파일을 먼저 감사한다.

## Smoke-test 요구

### 1. memory answer supported pass smoke

fixture:

```text
selected context raw_user_text="내 테스트 암호는 파란노트야."
report="방금 테스트 암호는 파란노트라고 말했어."
```

검증:

```text
node4_gate_status=pass
recent_memory_guard_status=pass
unsupported_recent_memory_claim_count=0
```

### 2. no selected context but memory claim blocked smoke

fixture:

```text
selected context=[]
report="아까 너는 파란노트라고 말했어."
```

검증:

```text
node4_gate_status=needs_revision
reason includes CODE_STATUS:recent_memory_claim_without_selected_context
safe blocking answer 출력
```

### 3. unsupported memory claim blocked smoke

fixture:

```text
selected context raw_user_text="내 테스트 암호는 파란노트야."
report="아까 너는 빨간노트라고 말했어."
```

검증:

```text
node4_gate_status=needs_revision
reason includes CODE_STATUS:recent_memory_claim_not_supported_by_context
```

### 4. internal id leak blocked smoke

fixture:

```text
report includes "memory_packet:node_1:pre_route_report" 또는 "trace_000001"
```

검증:

```text
node4_gate_status=needs_revision
reason includes CODE_STATUS:recent_memory_internal_id_leak
```

### 5. truncated overclaim blocked or warned smoke

fixture:

```text
selected context truncated=true
report="이전 대화 전체를 보면 너는 항상..."
```

검증:

```text
node4_gate_status=needs_revision
reason includes CODE_STATUS:recent_memory_truncated_context_overclaim
```

## 수동 확인 시나리오

```powershell
python main.py qwen-chat --live-trace
```

1턴:

```text
내 테스트 암호는 파란노트야.
```

2턴:

```text
방금 내가 말한 테스트 암호가 뭐였지?
```

기대:

```text
node_3가 "파란노트"를 말한다.
node_4 recent memory guard가 pass한다.
```

오류 유도:

테스트 fixture 또는 fake adapter로 node_3가 "빨간노트"라고 말하게 만든다.

기대:

```text
node_4가 needs_revision으로 막는다.
```

## 완료 조건

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
```

완료 보고에는 다음을 적는다.

- node_4가 selected memory context를 어디서 받는지
- code guard와 LLM review의 역할 분리
- 추가된 reason code
- pass/blocked smoke 결과
- safe blocking answer가 유지되는지
- compileall / smoke-test 결과

## 다음 발주 후보

ORDER_110 이후에야 오래된 기억 압축 계열로 넘어간다.

후보:

```text
ORDER_TBD_NODE5_MEMORY_COMPRESSOR_V0
ORDER_TBD_NODE4_MEMORY_SUMMARY_GATE_V0
```

번호는 아직 확정하지 않는다. `ORDER_111`과 `ORDER_112`는 이후 다른 좁은 MVP 발주서에 사용됐다.

이후 발주는 최근 원문 기억이 아니라 오래된 4턴 compression candidate를 요약 기억으로 바꾸는 작업이다.
