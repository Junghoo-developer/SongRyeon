# node_3 실제 시야와 오답 원인 감사 2026-07-11

## 범위

다음 라이브 실행의 `Node3InputBriefFrame`, node_3 LLM call payload audit,
prompt, raw response, 최종 report assembly를 대조했다.

- L 원문 확보 시험
- R partial 이후 L 전환 시험
- route 2 단순 인사 시험

코드와 prompt는 수정하지 않았다.

## 결론

node_3는 사용자 질문과 필요한 재료를 받았다. 주된 문제는 재료 누락이 아니라 다음 세 가지다.

1. 사용자 과업보다 훨씬 큰 운영 장부와 중복 규칙을 함께 받는다.
2. node_2가 실제 답변 재료보다 L2 검색 계획 또는 trace를 answer basis로 지정한다.
3. prompt가 `사용자 질문에 직접 답하라`면서 동시에 `공급된 근거에서만 보고하라`고 해,
   외부 근거가 필요 없는 인사/생성 요청도 근거 부족으로 거절할 수 있다.

## 실제 입력 크기

node_3 prompt 자체:

```text
134 lines
14,314 characters
```

node_3 input payload:

```text
L 시험: 42,475 characters / 36 top-level keys
R -> L 시험: 75,149 characters
route 2 인사 시험: 11,204 characters
```

Node3InputBriefFrame은 별도로 41개의 `reporting_rules`를 매 턴 payload에 넣는다.
이 규칙은 prompt의 규칙과 상당 부분 중복된다.

```text
reporting rule count: 41
reporting rule text: 약 2,828 characters
```

## 발견 1: 사용자 질문은 정상 공급됐다

세 실행 모두 payload 첫 필드에 원문 `user_question`이 보존됐다.
따라서 질문 누락이나 ID 연결 실패가 직접 원인은 아니다.

## 발견 2: L 시험에서 좋은 재료가 실제로 있었다

L 시험의 node_3 brief에는 ORDER 255 실행 기록을 설명하는 L3 요약이 들어 있었다.

```text
plain summary:
검색 후보와 원문 확보 상태를 none / candidates_only /
original_material_acquired로 구분한다.

task-relevant summary:
candidates_only와 original_material_acquired의 차이,
minimum_read_documents 요구 충족 상태를 설명한다.
```

따라서 node_3가 ORDER 255 핵심을 답하지 못한 것은 필요한 의미 재료가 전혀 없어서가 아니다.

## 발견 3: 유용한 요약보다 장부가 더 크다

L 시험의 주요 brief 재료 크기:

```text
document material ledger: 28 items / 약 19,182 JSON characters
runtime task sequence: 14 items / 약 2,463 JSON characters
L3 document summaries: 4 items / 약 4,801 JSON characters
```

node_3 payload는 다음을 한꺼번에 공급한다.

- 실제 read_doc 목록
- source-code read 목록
- material delivery policy
- 문서별 후보/read/supplied/excluded/unread 전체 장부
- 최종 후보와 누적 후보
- 제외 문서 전체 목록
- raw context 또는 L3 문서별 요약
- allowed claims
- 최근 기억
- answer basis
- L 결과
- R 결과
- Vessel R 재료
- 현재 턴 task sequence
- 41개 reporting rules

이 중 `runtime_task_sequence`와 `reporting_rules`는 payload 뒤쪽에 위치한다.
실제 raw response는 사용자 질문보다 이 실행 순서 자료를 중심으로 답했다.

## 발견 4: node_2가 검색 과정 자체를 주근거로 골랐다

L 시험의 node_2 evidence roles:

```text
primary_answer_basis: L2 query plan
primary_answer_basis: L2 revision query plan 1
supporting_context: L2 revision query plan 5
```

실제 ORDER 255 L3 요약이나 문서 context가 주근거로 선택되지 않았다.

R -> L 시험에서는 초기 trace 하나만 supporting context로 골랐고,
route 2 인사 시험에서는 node_2 input frame 존재만 supporting context로 골랐다.

node_2 answer-basis 입력에는 절대정보가 804개 있었지만 code는 앞쪽 절대정보 16개,
상대/혼합정보 각각 앞쪽 12개만 sample로 제공한다. 이 L 시험의 mixed sample은 전부
`l2_query_candidate_purpose`, 즉 검색 계획의 목적 문장이었다. node_2는 자신에게 보인
semantic sample 안에서 검색 계획을 고른 셈이다.

## 발견 5: direct-answer 규칙이 서로 충돌한다

node_3 prompt에는 다음이 동시에 있다.

```text
Answer the supplied user_question directly.
Report only from supplied evidence channels.
If the provided material is too thin, say what information is missing.
```

단순 인사 시험에는 문서/기억/R 재료가 없고 runtime task sequence만 있었다.
사용자 질문 자체는 지시문으로 보존됐지만 `report only from`의 허용 근거 목록에는
사용자 지시를 수행하는 일반 대화/생성 권한이 명확히 들어 있지 않다.

node_2 answer-basis prompt도 인사/변환/창작 같은 근거 비의존 요청을
`relative_allowed`에 명시적으로 포함하지 않고, 애매하면 `mixed_or_uncertain`을 고르게 한다.
실제 인사 시험은 `mixed_or_uncertain`으로 선택됐고 node_3는 근거 부족을 보고했다.

## 발견 6: code grounding block은 본문 모순을 막지 않는다

code는 brief의 절대 count로 올바른 `근거 기준` 블록을 앞에 붙인다.
그러나 node_3 raw response는 L 시험에서 다음 취지의 문장을 별도로 생성했다.

```text
실제 문서 또는 코드 원문 읽기는 발생하지 않았다.
```

실제 절대 count는 `read_doc=7`이었다.

report assembly는 LLM이 다시 쓴 count block을 제거하지만, 위와 같은 일반 문장 속 모순은
제거하거나 검사하지 않는다. node_4의 code count guard도 code가 붙인 첫 grounding block의
정규식 count만 검사한다. code block은 원래 정확하므로 이 검사는 통과한다.

node_4 LLM prompt에는 document contradiction 규칙이 있지만 이번 문장을 놓쳤다.

## 발견 7: R와 L이 함께 있으면 focused payload가 해제된다

R-only focused payload는 Vessel R 재료가 있고 문서/L 재료가 전혀 없을 때만 사용된다.
R partial 뒤 node_1이 L로 전환한 시험은 L 문서도 존재하므로 generic payload로 돌아갔다.

그 결과 R 상태, Vessel 재료, L 문서 원문 5개, 문서 장부, task 22개, 공통 규칙이 합쳐져
node_3 input payload가 75,149자까지 커졌다. 이 시험에서도 node_3는 CoreEgo-Time Axis 관계보다
실행 상태를 나열했다.

## 원인 판정

### 주원인

- node_3 task-first 입력 우선순위 부재
- answer basis evidence source 표의 순서 기반 sample 제한
- 검색 과정 장부를 final answer primary basis로 선택할 수 있는 구조
- 모든 턴에 공통 mega-payload를 보내는 구조
- user-task 수행과 evidence-grounded factual claim을 구분하지 않는 prompt 경계

### 부원인

- 134줄 prompt와 41개 payload reporting rules의 중복
- runtime task sequence가 항상 node_3의 허용 근거로 공급됨
- code grounding block과 LLM 본문의 절대 count 모순을 별도로 검사하지 않음
- node_4에 사용자 과업 충족 여부를 직접 묻는 규칙이 없음

### 현재 증거로 주원인이라 보기 어려운 것

- 사용자 질문 누락
- L3 요약 재료 완전 부재
- Neo4j 연결 실패
- node_3 JSON parse/schema 실패
- Qwen 모델 크기만의 문제

모델 성능이 영향을 줄 수는 있으나, 현재 입력 구조는 큰 모델에도 불필요한 장부와
충돌 규칙을 많이 전달한다. 먼저 구조를 정리하지 않고 모델만 키우면 비용은 늘고
오답 원인은 남을 가능성이 크다.

## 다음 설계 논의 대상

바로 패치하지 않고 다음을 결재해야 한다.

1. node_3가 먼저 받아야 할 `사용자 과업 계약`의 최소 필드
2. node_2가 고른 primary evidence만 node_3 앞쪽에 집중 공급할지 여부
3. runtime task sequence를 사용자가 실행 과정 자체를 물을 때만 선택 재료로 둘지 여부
4. 공통 prompt와 payload reporting rules의 중복 제거 범위
5. node_4에 `사용자 질문에 실제로 답했는가` 검사를 추가할지 여부
6. code grounding count와 반대되는 일반 문장 모순을 구조화해 검사할 방법

키워드 휴리스틱으로 질문 유형을 분류하거나 code가 의미 답변을 대신 만드는 방식은
해결책으로 제안하지 않는다.
