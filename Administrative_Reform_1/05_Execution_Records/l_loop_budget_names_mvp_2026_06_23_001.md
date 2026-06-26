# L Loop Budget Names MVP 2026-06-23 001

## 목표

L루프 예산에서 서로 다른 개념을 분리한다.

기존에는 `max_query_candidates`라는 이름이 "검색 결과 후보 수"처럼 보였지만 실제 동작은 search query 시도 한계에 가까웠다.

## 바뀐 이름

```text
search_top_k
= search_docs 한 번이 반환할 검색 결과 후보 수

max_query_attempts
= L루프 안에서 검색어를 몇 번까지 실행/수정할 수 있는지

max_read_doc_calls
= 검색 후보 중 문서 원문을 몇 개까지 읽을 수 있는지
```

`max_query_candidates`는 과거 호환용 alias로 남겼다.

현재 의미는 `max_query_attempts`와 같다.

## 바뀐 파일

```text
songryeon_core/runtime/defaults.py
songryeon_core/core/schemas.py
songryeon_core/tools/tool_efficiency_policy.py
songryeon_core/tools/document_tools.py
songryeon_core/loops/l_loop.py
songryeon_core/runtime/dry_run.py
songryeon_core/runtime/user_turn.py
songryeon_core/runtime/terminal_view.py
songryeon_core/runtime/replay.py
songryeon_core/runtime/smoke_test.py
main.py
```

## 구현 내용

- 기본값에 `DEFAULT_SEARCH_TOP_K`, `DEFAULT_MAX_QUERY_ATTEMPTS`를 추가했다.
- `ToolUseBudgetFrame`에 `search_top_k`, `max_query_attempts`를 추가했다.
- `search_docs` 결과 payload에 실제 `top_k`를 남긴다.
- L루프의 `search_docs(..., top_k=3)` 하드코딩을 `search_top_k`로 교체했다.
- pretty runtime에 다음 예산 줄을 추가했다.

```text
L 도구 예산: tool_calls=... / query_attempts=... / search_top_k=... / read_doc=... / stop_reason=...
```

- CLI에 다음 옵션을 추가했다.

```text
--search-top-k
--max-query-attempts
```

- 기존 `--max-query-candidates`는 호환용으로 남겼다.

## 확인

```text
python -m compileall songryeon_core main.py
python main.py smoke-test
python main.py fake-turn "문서 메모리 인덱스 확인" --pretty --search-top-k 5 --max-query-attempts 2
```

결과:

```text
SMOKE_TEST_OK
search_top_k_smoke = 5
max_query_attempts_smoke = 2
```

pretty runtime에서도 다음처럼 보였다.

```text
search_docs: 5개 후보(top_k=5)
L 도구 예산: ... query_attempts=1/2 / search_top_k=5 ...
```

## 하지 않은 것

- L3 partial/failed 판정 강화는 아직 하지 않았다.
- L3 -> L2 재검색 루프는 아직 만들지 않았다.
- read_doc을 여러 후보에 자동 분배하는 정책은 아직 만들지 않았다.

## 학습 포인트

이번 MVP는 송련을 더 똑똑하게 만든 것이 아니라, 송련이 얼마나 보고 멈췄는지를 더 정직하게 보이게 만든 작업이다.

이제 데모 로그를 볼 때 다음을 분리해서 볼 수 있다.

```text
검색 결과 후보를 몇 개 받았는가?
검색어 시도를 몇 번 허용했는가?
문서 원문을 몇 개 읽었는가?
도구 호출 총량 때문에 멈췄는가?
```
