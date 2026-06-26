# ORDER 093: Node4 Grounding Count Guard v0

## 목적

node_3 최종 답변의 `근거 기준` count가 `Node3InputBriefFrame`과 다를 때
node_4가 반드시 반려하도록 만든다.

## 문제

실제 테스트에서 다음 모순이 관찰되었다.

```text
runtime:
  node_3 input brief: search_candidates=10

answer:
  검색 후보 문서: 0개
```

프롬프트에는 count mismatch를 반려하라고 되어 있었지만,
node_4 LLM이 이를 놓치고 `pass`를 낼 수 있었다.

이 문제는 의미 판단이 아니라 산술/형식 검사다.
따라서 LLM에게만 맡기지 않고 코드 guard로 검사해야 한다.

## 정책

node_4는 보고문 첫머리의 `근거 기준:` 블록에서 다음 count를 파싱한다.

```text
- 읽은 문서: N개
- 검색 후보 문서: N개
- 현재 턴 실행 순서 자료: N개
```

그리고 `Node3InputBriefFrame`의 절대 count와 비교한다.

```text
len(read_documents)
search_candidate_count
len(runtime_tasks)
```

불일치하면 LLM gate가 `pass`를 냈더라도 `needs_revision`으로 강제한다.

## Runtime 라벨

count guard가 작동하면 gate generation source에 다음 라벨이 붙는다.

```text
CODE:GROUNDING_COUNT_GUARD
```

reason에는 다음 라벨을 포함한다.

```text
CODE_STATUS:grounding_count_mismatch
```

