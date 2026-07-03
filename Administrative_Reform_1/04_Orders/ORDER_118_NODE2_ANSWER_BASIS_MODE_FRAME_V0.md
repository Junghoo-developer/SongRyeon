# ORDER 118: Node2 Answer Basis Mode Frame v0

## 상태

발주서 초안.

사용자 승인 후 구현한다.

## 목표

node_2가 node_3에게 최종 답변의 근거 말하기 모드를 명시적으로 전달하게 한다.

이번 발주의 핵심은 node_2가 단순히 주어진 값을 복사하는 것이 아니라, 제공된 절대정보, 상대정보, 혼합정보 source bundle을 보고 스스로 `answer_basis_mode`를 선택하고 그 이유를 상대정보 또는 혼합정보로 남기게 하는 것이다.

이 작업은 송련의 행동 방식을 메타정보 분류 원칙과 맞추기 위한 MVP다.

## 배경

최근 대화에서 다음 문제가 확인됐다.

1. L loop가 돌았다는 이유만으로 node_3가 문서 근거 중심으로 과하게 굳을 수 있다.
2. 최근 대화 기억이 주근거인 질문에서도 "문서 근거 없음" 식으로 답할 위험이 있다.
3. 반대로 문서, trace, count 검증이 필요한 작업에서는 너무 유연하게 말하면 안 된다.
4. 따라서 node_3가 말하기 전에 node_2가 이번 답변의 근거 자세를 명시해야 한다.

사용자 결재 기준:

`answer_basis_mode`는 7개처럼 세분화하지 않는다.
3개로 제한한다.

```text
absolute_first
relative_allowed
mixed_or_uncertain
```

## 핵심 개념

### answer_basis_mode

node_2가 node_3에게 넘기는 최종 답변 자세다.

```text
absolute_first
relative_allowed
mixed_or_uncertain
```

#### absolute_first

절대정보 위주로 말해야 하는 모드.

사용 예:

```text
몇 개 읽었어?
route가 뭐야?
smoke 통과했어?
ORDER_112 문서에 뭐라고 적혀 있어?
trace/data 기준으로 뭐가 사실이야?
```

특징:

```text
정밀도 우선
추측 금지
모르면 모른다고 말함
코드/파일/trace/data/tool result/schema 값 중심
```

#### relative_allowed

상대정보를 섞어도 괜찮은 모드.

사용 예:

```text
이 구조 어때?
다음 목표 뭐가 좋을까?
초딩용으로 설명해줘.
README 첫인상 개선 아이디어 줘.
```

특징:

```text
유연성 허용
해석/조언/비판/브레인스토밍 가능
다만 절대사실인 척하면 안 됨
```

#### mixed_or_uncertain

혼합정보이거나, 근거가 부족하거나, 절대정보와 상대정보 매칭이 애매한 경우.

사용 예:

```text
오늘 전체 흐름 정리해줘.
최근 대화와 실행기록을 합쳐서 판단해줘.
문서 일부만 읽었는데 현재 가능한 결론을 말해줘.
근거가 부족하지만 어디까지 말할 수 있는지 알려줘.
```

특징:

```text
출처 묶음 기준
불확실성 표시
부분 근거 표시
단정 금지
```

## basis_reason_codes

모드는 3개로 제한하되, node_2가 왜 그 모드를 골랐는지는 reason code로 남긴다.

초기 후보:

```text
code_verified_fact_required
user_asked_for_interpretation
multi_source_bundle
source_mapping_unclear
insufficient_grounding
partial_evidence_only
recent_conversation_basis_present
document_basis_present
runtime_state_basis_present
llm_mode_selection_failed
```

주의:

- reason code는 모드 폭증을 막기 위한 보조 필드다.
- reason code가 answer_basis_mode처럼 행동하면 안 된다.
- code는 reason code enum 검증만 하고 의미 판단을 대신하지 않는다.

## mode_selection_reason

node_2가 자연어로 작성하는 모드 선택 이유다.

이 값은 절대정보가 아니다.

- 특정 하나의 절대정보 record/field에 대응하면 `relative`
- 여러 source bundle을 보고 판단했다면 `mixed`

대부분의 mode selection reason은 `mixed`가 될 가능성이 높다.

예:

```text
answer_basis_mode = mixed_or_uncertain
basis_reason_codes = ["multi_source_bundle", "partial_evidence_only"]
mode_selection_reason =
"사용자 요청은 최근 대화 흐름과 실행기록 문서를 함께 돌아보는 작업이므로,
단일 절대 record만으로 답하기 어렵고 부분 근거를 명시해야 한다."
generated_by = LLM:NODE_2
info_class = mixed
```

## 구현 방향

### 1. schema 추가

후보 schema:

```text
Node2AnswerBasisFrame
```

필드 후보:

```text
frame_id
turn_id
answer_basis_mode
basis_reason_codes
mode_selection_reason
mode_selection_reason_info_class
evidence_roles
generated_by
info_class
semantic_judgement_status
source_trace_ids
source_data_ids
```

### 2. answer_basis_mode enum

허용값은 아래 3개뿐이다.

```text
absolute_first
relative_allowed
mixed_or_uncertain
```

다른 값은 schema validation 또는 code validation에서 실패해야 한다.

### 3. evidence_roles

각 근거 자료가 답변에서 어떤 역할인지 node_2가 지정할 수 있게 한다.

초기 후보:

```text
primary_answer_basis
supporting_context
available_but_not_used
candidate_not_read
excluded_by_budget
failed_or_empty
not_supplied
```

주의:

- evidence role도 node_2 판단이다.
- code가 의미적으로 primary/supporting을 고르면 안 된다.
- code는 role 값의 유효성, source id 존재 여부만 검사한다.

### 4. node_2 prompt 보강

node_2에게 메타정보 기준을 명시한다.

반드시 포함할 교육:

```text
절대정보:
코드/파일/trace/data/schema/tool result처럼 시스템이 값과 존재를 확인할 수 있는 정보.

상대정보:
특정 하나의 절대정보 record/field에 대응하는 해석/판단/요약.

혼합정보:
여러 절대정보 묶음 또는 하나로 고정하기 부적절한 source bundle에 근거한 해석/판단/요약.

너의 answer_basis_mode 선택은 보통 상대정보 또는 혼합정보다.
절대정보 자체가 아니다.
따라서 mode_selection_reason에는 어떤 근거들을 보고 그렇게 판단했는지 밝혀라.
```

node_2는 다음을 해야 한다.

```text
1. answer_basis_mode를 3개 중 하나로 고른다.
2. basis_reason_codes를 고른다.
3. mode_selection_reason을 쓴다.
4. 각 source의 evidence_role을 지정한다.
5. 판단 불확실성이 있으면 mixed_or_uncertain을 선택한다.
```

### 5. code fallback 정책

node_2 LLM mode selection이 실패했을 때 code가 의미 판단으로 대신 고르면 안 된다.

실패 시 safe frame:

```text
answer_basis_mode = mixed_or_uncertain
basis_reason_codes = ["llm_mode_selection_failed"]
mode_selection_reason = "CODE_STATUS:node2_answer_basis_mode_selection_failed"
generated_by = CODE:FALLBACK
info_class = absolute_status
semantic_judgement_status = failed
evidence_roles = []
```

이 fallback은 "의미상 mixed가 맞다"는 판단이 아니다.
단지 안전한 불확실성 모드로 닫는 것이다.

### 6. node_3 input brief 연결

node_3 input brief에 다음을 포함한다.

```text
answer_basis_mode
basis_reason_codes
mode_selection_reason
evidence_roles
```

node_3 prompt에는 다음 경계를 넣는다.

```text
absolute_first:
- 코드/문서/trace/data로 확인 가능한 사실을 우선한다.
- 추측을 줄인다.
- 확인되지 않은 내용은 확인되지 않았다고 말한다.

relative_allowed:
- 해석/조언/비판/구상이 가능하다.
- 다만 절대정보처럼 단정하지 않는다.

mixed_or_uncertain:
- 출처 묶음과 한계를 드러낸다.
- 부분 근거와 불확실성을 말한다.
- 부족한 근거를 지어내지 않는다.
```

### 7. node_4 guard는 약화하지 않는다

이번 발주에서 node_4 자동 재작성 루프는 열지 않는다.

다만 가능하면 최소 guard를 추가할 수 있다.

- `absolute_first`인데 node_3가 근거 없는 추측을 강하게 단정하면 needs_revision
- `mixed_or_uncertain`인데 불확실성/부분 근거를 전혀 표시하지 않으면 needs_revision
- `relative_allowed`라도 절대정보처럼 거짓 단정하면 needs_revision

이 guard는 작게만 한다.
복잡한 자동 재작성은 후속 발주로 미룬다.

## 메타정보 분류

절대정보:

- answer_basis_mode enum 값 자체
- basis_reason_codes 값 자체
- schema validation 결과
- source_data_ids 존재 여부
- fallback 발생 여부
- semantic_judgement_status 값

상대정보:

- 특정 하나의 source record를 근거로 한 mode_selection_reason
- 특정 하나의 source에 대한 evidence_role 판단

혼합정보:

- 여러 source bundle을 보고 고른 answer_basis_mode 판단
- 여러 source bundle을 종합한 mode_selection_reason
- 여러 자료 사이의 역할 분류 판단

주의:

- answer_basis_mode 값은 schema상 기록된 값이라는 점에서는 절대정보다.
- 그러나 그 값이 "의미적으로 옳다"는 것은 절대정보가 아니다.
- node_2가 왜 그 모드를 골랐는지는 LLM 판단이며 상대/혼합정보로 드러나야 한다.

## 금지

- answer_basis_mode를 3개보다 늘리지 마라.
- document_primary, recent_conversation_primary 같은 세부 모드를 이번에 만들지 마라.
- code가 의미적으로 모드를 고르지 마라.
- code fallback을 "LLM 판단"처럼 보이게 하지 마라.
- node_3가 answer_basis_mode를 무시하게 만들지 마라.
- node_4 guard를 제거하거나 약화하지 마라.
- W/R loop 열지 마라.
- scheduler/외부 DB/vector DB/장기기억 DB 건드리지 마라.
- same-turn L reroute 횟수 늘리지 마라.
- node_4 자동 재작성 루프 열지 마라.

## 테스트 요구

기존 재정립 루틴을 반드시 따른다.

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

추가 smoke/pytest 기대:

1. node_2가 `absolute_first`를 선택하는 fixture
   - runtime count 또는 문서 원문 확인 요청
   - mode_selection_reason 존재
   - generated_by=LLM:NODE_2 또는 test fake equivalent
   - info_class가 상대/혼합으로 드러남

2. node_2가 `relative_allowed`를 선택하는 fixture
   - 구조 의견/다음 목표/브레인스토밍 요청
   - 절대정보 부족만으로 blocking하지 않음
   - generated_by/source 정보 유지

3. node_2가 `mixed_or_uncertain`을 선택하는 fixture
   - 여러 source bundle 또는 partial evidence 상황
   - basis_reason_codes에 multi_source_bundle 또는 partial_evidence_only 포함

4. LLM selection 실패 fixture
   - code fallback 발생
   - answer_basis_mode=mixed_or_uncertain
   - basis_reason_codes=["llm_mode_selection_failed"]
   - generated_by=CODE:FALLBACK
   - semantic_judgement_status=failed

5. node_3 input brief 연결 확인
   - answer_basis_mode가 brief에 들어감
   - evidence_roles가 brief에 들어감
   - node_3 payload가 raw internal id를 user-facing 답변에 누출하지 않음

6. terminal/runtime 표시 확인
   - answer_basis_mode 표시
   - basis_reason_codes 표시
   - generated_by 표시
   - fallback 여부 표시

## 완료 보고에 반드시 포함할 것

- Node2AnswerBasisFrame 위치
- answer_basis_mode enum 위치
- node_2가 mode를 선택하는 위치
- node_2 prompt에 들어간 메타정보 교육 요약
- code fallback 정책
- node_3 brief 연결 방식
- terminal/runtime 표시 변경
- node_4 guard를 바꿨는지 여부
- 추가한 pytest/smoke 이름
- compileall / pytest / smoke-test 결과
- 이번 발주에서 일부러 하지 않은 것
