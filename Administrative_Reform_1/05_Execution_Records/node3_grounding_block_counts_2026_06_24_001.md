# node3 grounding block counts 2026-06-24 001

## 배경

`node_3`가 근거 종류를 말하기 시작했지만,
실제 읽은 문서 수와 검색 후보 문서 수를 명확히 분리하지 못할 여지가 남아 있었다.

특히 사용자가 "여러 문서를 열람"하라고 했는데 실제로는 `read_doc`이 1회만 실행된 경우,
`node_3`가 검색 후보를 읽은 문서처럼 말하면 사용자 통제력이 떨어진다.

## 구현

`Node3InputBriefFrame`에 다음 절대정보 필드를 추가했다.

- `search_candidate_count`
- `search_candidate_documents`

이 필드는 L3가 보존한 search_docs 후보 문서에서 사람이 읽을 수 있는 문서명만 뽑아 만든다.
후보 문서는 원문을 읽은 문서가 아니므로, `read_documents`와 분리한다.

`node_3` 프롬프트에는 최종 답변 첫머리 고정 블록을 요구했다.

```text
근거 기준:
- 읽은 문서: N개
- 검색 후보 문서: N개
- 현재 턴 실행 순서 자료: N개
- 답변 한계: ...
```

`node_4`는 이 블록이 없거나, count가 brief와 다르거나,
검색 후보 문서를 읽은 문서처럼 말하면 `needs_revision`으로 볼 수 있다.

## 의미

이번 변경은 `node_3`가 더 똑똑해졌다는 뜻이 아니다.

대신 `node_3`가 자기 답변의 재료 규모를 사용자 앞에 먼저 펼치도록 만든다.
이렇게 하면 "검색은 했지만 읽지는 않았다"와 "문서를 실제로 읽었다"가 섞이기 어렵다.

## 검증

- `python -m compileall songryeon_core`
- `python main.py smoke-test`

두 검증을 통과했다.

