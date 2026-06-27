# ORDER 112: Explicit Artifact Priority And Whole Document Packing v0

## 상태

발주서 초안.

사용자 승인 후 구현한다.

## 배경

최근 qwen-turn 테스트에서 다음 문제가 확인됐다.

사용자 요청:

```text
ORDER_100, ORDER_101, ORDER_104, ORDER_105, ORDER_108, ORDER_109, ORDER_110 관련 문서를 가능한 한 많이 찾고 흐름을 정리해줘.
```

현재 L루프는 예산을 넓히고 L3가 `partial`을 내면 L2 revision query를 반복할 수 있다.
실제로 continuation과 revision query는 여러 번 실행됐다.

하지만 검색기는 `search_docs` 임베딩 검색 기반이다.
그래서 명시된 ORDER 원문 대신 다음 문서가 먼저 걸릴 수 있다.

- README
- 실행기록 요약
- 이전 테스트 report
- 여러 ORDER를 묶은 draft 문서

그 결과 node_3는 "읽은 문서 기준"으로 답하지만, 사용자가 명시한 ORDER 원문을 각각 직접 읽지는 못할 수 있다.

## 목표

명시된 ORDER/document ID가 사용자 입력에 있을 때, 임베딩 검색 후보보다 먼저 해당 원문 문서를 직접 후보로 세운다.

그리고 node_3에 공급할 문서는 "몇 개까지"가 아니라 "전체 문서 context 예산 안에서" whole-document 방식으로 packing한다.

핵심 원칙:

```text
문서는 중간에서 자르지 않는다.
다음 문서 전체를 넣으면 예산을 넘는 순간, 그 문서와 이후 후보는 node_3 read_documents에 넣지 않는다.
```

이 발주는 A안, 즉 strict rank order 정책을 따른다.

## 구현 범위

### 1. 명시 artifact reference 추출

사용자 입력에서 다음처럼 표면에 드러난 artifact reference를 추출한다.

예:

```text
ORDER_100
ORDER_101
ORDER_104
ORDER_105_MEMORY_SELECTION_TO_NODE2_HANDOFF_V0
04_Orders/ORDER_105_MEMORY_SELECTION_TO_NODE2_HANDOFF_V0.md
```

경계:

- code는 문자열/파일명/경로 패턴만 본다.
- code는 "중요해 보이는 문서"를 의미 판단으로 고르지 않는다.
- 추출된 explicit reference는 사용자 입력에 실제로 등장한 절대 좌표 후보로 기록한다.

### 2. explicit reference direct resolve

추출된 reference는 `search_docs`보다 먼저 document memory index 또는 artifact resolver로 대조한다.

정책:

- unique match이면 direct document candidate로 등록한다.
- ambiguous이면 임의 선택하지 않고 ambiguous 상태와 후보 목록을 기록한다.
- not_found이면 not_found 상태로 기록하고, 이후 embedding search가 보조적으로 찾을 수 있게 둔다.

권장 우선순위:

```text
사용자 입력에 나온 순서의 explicit unique match
-> embedding search의 unique doc_id 후보
```

README, map, digest, execution summary 문서는 명시된 ORDER 원문을 대체하지 않는다.
다만 사용자가 개요를 요구했거나 explicit 원문을 못 찾은 경우 보조 후보가 될 수 있다.

### 3. whole-document context packing A안

정렬된 후보 문서 목록을 앞에서부터 누적한다.

정책:

```text
whole_document_only = true
strict_rank_order = true
```

규칙:

1. 문서 원문은 중간에서 자르지 않는다.
2. 다음 문서 전체를 추가하면 `max_document_context_chars` 또는 향후 `max_document_context_tokens`를 초과하는지 계산한다.
3. 초과하지 않으면 included로 넣는다.
4. 초과하면 그 문서는 excluded_due_to_context_budget으로 기록한다.
5. A안이므로 그 이후 후보도 node_3 read_documents에 넣지 않는다.
6. 이후 후보는 `excluded_after_strict_rank_cutoff`로 기록한다.

예:

```text
budget = 30000 chars

ORDER_100 = 5000  -> included, total 5000
ORDER_101 = 7000  -> included, total 12000
ORDER_104 = 9000  -> included, total 21000
ORDER_105 = 11000 -> excluded_due_to_context_budget
ORDER_108 = 4000  -> excluded_after_strict_rank_cutoff
```

ORDER_108은 작더라도 ORDER_105 뒤에 있으므로 넣지 않는다.
이유는 순위 보존과 정직성을 우선하기 때문이다.

### 4. context pack frame 추가

후보 schema 이름:

```text
DocumentContextPackFrame
```

후보 필드:

```text
frame_id
turn_id
source_query_frame_ids
source_search_result_data_ids
source_explicit_reference_data_id
max_document_context_chars
budget_unit
whole_document_only
strict_rank_order
included_documents
excluded_documents
included_document_count
excluded_document_count
included_total_chars
cutoff_reason
generated_by
info_class
source_trace_ids
source_data_ids
```

included document item 후보 필드:

```text
doc_id
document_name
char_count
rank_index
selection_basis
text
source_data_id
```

excluded document item 후보 필드:

```text
doc_id
document_name
char_count
rank_index
selection_basis
exclusion_reason
would_exceed_budget
source_data_id
```

`text`는 included document에만 둔다.
excluded document는 node_3가 읽은 문서로 취급하지 않는다.

### 5. node_3 brief 연결

node_3가 받는 `read_documents`는 included document만 포함한다.

excluded document는 별도 목록으로 전달할 수 있다.

예:

```text
excluded_document_contexts
document_context_pack_status
```

node_3 prompt에는 다음 경계를 명시한다.

- included document만 읽은 원문으로 답한다.
- excluded document는 읽은 문서가 아니다.
- excluded document는 "예산 때문에 공급되지 않은 후보"로만 말할 수 있다.
- README/요약/실행기록은 원문 ORDER를 대체하지 않는다.

### 6. terminal/runtime 표시

runtime view에 다음을 표시한다.

```text
document_context_pack:
  included=3 / excluded=4 / budget=21000/30000 chars
  whole_document_only=true / strict_rank_order=true
  cutoff=excluded_due_to_context_budget at ORDER_105...
```

명시 artifact resolve 결과도 표시한다.

```text
explicit_artifact_refs:
  ORDER_100 -> unique: 04_Orders/ORDER_100...
  ORDER_110 -> not_found
```

## 메타정보 분류

절대정보:

- 사용자 입력에 문자열 `ORDER_100`이 존재한다.
- 특정 doc_id가 존재한다.
- explicit reference가 unique/ambiguous/not_found로 resolve됐다.
- 문서 char_count
- 문서 included/excluded 여부
- context budget 숫자
- cutoff reason code

혼합정보:

- L2가 어떤 query가 더 좋다고 판단한 purpose
- L3가 coverage 부족을 설명한 reason
- node_3가 읽은 문서들을 종합해 흐름을 설명한 보고문

금지:

- code가 의미적으로 중요한 문서를 골랐다고 주장하지 않는다.
- code가 README/요약문서를 원문 ORDER와 같다고 취급하지 않는다.
- excluded 문서를 node_3가 읽은 문서 count에 넣지 않는다.
- 문서를 중간에서 잘라 넣고 전체 문서를 읽은 것처럼 표시하지 않는다.

## 비범위

이번 발주에서 하지 않는다.

- 동적 예산 자동 증액
- tokenizer 기반 정확 토큰 계산
- 외부 DB/vector DB
- 장기기억 DB
- W/R loop
- scheduler 정책
- node_4 자동 재작성 루프
- same-turn L reroute 확대

`max_document_context_chars`는 v0의 현실적 예산 단위다.
나중에 tokenizer가 들어오면 `max_document_context_tokens`로 승격할 수 있다.
그 전까지 char budget을 token budget이라고 부르지 않는다.

## 완료 조건

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
```

추가 smoke 기대값:

- explicit ORDER ID가 사용자 입력에서 추출된다.
- unique explicit ORDER 문서가 embedding search 후보보다 먼저 included 후보가 된다.
- ambiguous explicit reference는 임의 선택되지 않는다.
- whole-document packing은 문서를 중간에서 자르지 않는다.
- 예산 초과 문서는 `excluded_due_to_context_budget`로 기록된다.
- strict rank order 때문에 그 이후 문서는 `excluded_after_strict_rank_cutoff`로 기록된다.
- node_3 input brief의 read document count는 included document count와 일치한다.
- excluded document는 read document count에 들어가지 않는다.
- terminal view가 included/excluded/cutoff를 표시한다.

## 수동 테스트 후보

```powershell
python main.py qwen-turn "송련의 최근 기억 시스템이 어떻게 만들어졌는지 추적해줘. ORDER_100, ORDER_101, ORDER_104, ORDER_105, ORDER_108, ORDER_109, ORDER_110을 각각 가능한 한 직접 찾아 읽고, 각 ORDER가 무엇을 추가했는지와 서로 어떻게 이어지는지 정리해줘. README나 실행기록 요약만 읽었으면 그건 부분 근거라고 밝혀줘." --timeout 240 --pretty
```

기대:

- ORDER 번호별 direct resolve 결과가 runtime에 보인다.
- included 문서와 excluded 문서가 분리된다.
- node_3는 included 문서 기준으로만 답한다.
- 원문을 못 넣은 ORDER는 "읽지 못한/공급되지 않은 문서"로 남는다.
