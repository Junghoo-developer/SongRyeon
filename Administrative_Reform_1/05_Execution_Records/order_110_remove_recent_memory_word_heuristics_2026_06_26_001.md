# ORDER_110 recent memory word heuristic removal execution record

## 배경

ORDER_110 구현 감사 중 `node_4_gatekeeper.py`에 최근 기억 발화를 문자열 트리거로 감지하는 code guard가 확인되었다.

예:

- `아까`
- `방금`
- `이전 대화`
- `앞서`
- `말했`
- `말한`

이 방식은 code가 문장 의미를 단어 조합으로 추정하는 휴리스틱이다.
SongRyeon Core 원칙상 최근 기억 발화의 의미 검사는 node_4 LLM의 상대/혼합 판단 책임으로 두고, code가 의미 판단을 대신하지 않아야 한다.

## 변경

`songryeon_core/nodes/node_4_gatekeeper.py`

- `_recent_memory_claim_lines` 제거
- `_has_recent_memory_trigger` 제거
- `_claims_have_context_literal` 제거
- `_RECENT_MEMORY_ALLOWED_TOKENS` 제거
- `_context_tokens` 제거
- `_claim_content_tokens` 제거
- `_normalized_tokens` 제거
- `_normalize_token` 제거
- `_has_truncated_context` 제거
- `_has_truncated_overclaim` 제거
- `_selector_judgement_overstated` 제거
- `CODE:RECENT_MEMORY_UTTERANCE_GUARD`를 `CODE:RECENT_MEMORY_INTERNAL_ID_GUARD`로 축소

남긴 code guard:

- raw internal id 노출 검사

이 검사는 의미 판단이 아니라 내부 좌표 문자열 노출 검사다.

## 정책 결정

code가 더 이상 다음을 직접 판정하지 않는다.

- selected context가 없는데 과거 대화 발화를 했는지
- selected context에 없는 말을 과거 대화로 주장했는지
- truncated context를 전체 이전 대화처럼 과장했는지
- selector 관련성 판단을 code fact처럼 과장했는지

위 항목은 `node_4_gatekeeper_v0.md` prompt에 남아 있는 node_4 LLM의 검수 책임이다.

## Smoke 변경

`songryeon_core/runtime/smoke_test.py`

- `아까 너는 파란노트라고 말했어.`
- `아까 너는 빨간노트라고 말했어.`
- `이전 대화 전체를 보면...`

위 문장들은 fake node_4 환경에서 code word heuristic으로 차단되지 않아야 한다.

새 확인값:

```text
node4_recent_memory_guard_without_context=pass
node4_recent_memory_guard_unsupported=pass
node4_recent_memory_guard_truncated=pass
node4_recent_memory_guard_no_word_heuristic=true
node4_recent_memory_guard_internal_id=needs_revision
```

## 검증

```text
python -m compileall .\songryeon_core .\main.py
```

통과.

```text
python .\main.py smoke-test
```

통과.

최종 상태:

```text
SMOKE_TEST_OK
```
