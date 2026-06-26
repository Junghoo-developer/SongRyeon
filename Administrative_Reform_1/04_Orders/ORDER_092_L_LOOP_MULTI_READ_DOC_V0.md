# ORDER 092: L Loop Multi Read Doc v0

## 목적

L루프가 `search_docs` 결과 후보 중 상위 1개만 읽고 멈추던 구조를 고친다.

`ORDER_090`과 `ORDER_091`을 통해 L1이 여러 문서 열람 예산을 요청하고,
CODE:BUDGET_POLICY가 `read_doc` 예산과 `tool_calls` 예산을 정합적으로 승인할 수 있게 되었다.

그러나 실제 L루프 실행은 여전히 검색 후보 1개만 `read_doc`했다.

## 문제

사용자가 여러 문서의 연관성을 요청한 경우,
L1은 여러 문서 열람을 목표로 잡고 예산도 요청한다.

하지만 기존 L루프는 다음 흐름에 머물렀다.

```text
search_docs
-> top 후보 1개 read_doc
-> L3 partial
-> revision search_docs
```

즉, 검색 후보가 이미 있는데도 다음 후보를 읽지 않고 재검색으로 넘어갔다.

## 정책

`search_docs` 결과에서 문서 후보가 여러 개 있고,
아래 예산이 남아 있으면 후보 문서를 순서대로 읽는다.

```text
tool_call_count < max_tool_calls
read_doc_count < max_read_doc_calls
input_chars_used < max_input_chars
controller iteration budget available
```

검색 후보 문서는 중복 없이 읽는다.

## 기대 효과

여러 문서 비교, 연관점 분석, 랜덤/탐색형 문서 읽기 요청에서
node_3에게 실제 `read_documents`가 여러 개 공급된다.

L3는 후보 수가 아니라 실제 읽은 문서 수를 기준으로 `achieved/partial`을 판단할 수 있다.

