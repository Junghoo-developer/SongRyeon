# ORDER 110 Node4 Recent Memory Utterance Guard - 2026-06-26-001

## Source Order

- `Administrative_Reform_1/04_Orders/ORDER_110_NODE4_RECENT_MEMORY_UTTERANCE_GUARD_V0.md`

## 구현 범위

`node_4 gatekeeper`가 최종 report 안의 최근 기억 관련 발화를 `SelectedRecentMemoryContextFrame`과 `Node3InputBriefFrame` 범위 안에서 검사하도록 보강했다.

node_4 LLM 입력 payload에는 다음 필드를 명시했다.

```text
selected_recent_memory_contexts
selected_recent_memory_context_frame_id
memory_selection_status
memory_selection_info_class
```

`Node4GatekeeperFrame`에는 최근 기억 검수 상태를 별도 필드로 남긴다.

```text
recent_memory_guard_status
recent_memory_guard_reason_codes
recent_memory_claim_count
unsupported_recent_memory_claim_count
recent_memory_internal_id_leak_count
recent_memory_revision_targets
```

## Reason Codes

이번 작업에서 node_4가 남길 수 있는 최근 기억 전용 반려 code를 추가했다.

```text
CODE_STATUS:recent_memory_claim_without_selected_context
CODE_STATUS:recent_memory_claim_not_supported_by_context
CODE_STATUS:recent_memory_truncated_context_overclaim
CODE_STATUS:recent_memory_selector_judgement_overstated_as_fact
CODE_STATUS:recent_memory_internal_id_leak
```

## Code Guard Boundary

code guard는 절대 정보로 판별 가능한 좁은 검사만 수행한다.

- selected context가 없는데 이전 대화 발화를 하는지 확인한다.
- raw internal id, trace id, data id 노출 패턴을 확인한다.
- selected raw text에 없는 짧은 literal을 이전 대화 내용처럼 말하는지 얕게 확인한다.
- truncated flag가 있는데 "전체 대화" 같은 과잉 단정 표현이 있는지 확인한다.

문장 의미 동등성, 과거 발화 의도, 자연스러움 평가는 code fact로 취급하지 않는다.

## Runtime Display

terminal/runtime view는 node_4 구역에 최근 기억 guard 상태를 표시한다.

```text
recent memory guard: pass / claims=... / unsupported=... / internal_id_leak=...
```

반려가 있으면 `recent_memory_guard_reason_codes`도 함께 보인다.

## Safe Blocking

node_4가 최근 기억 발화 문제로 `needs_revision`을 내면 기존 safe blocking answer를 유지한다.

검증 smoke에서 unsafe report 본문이 사용자 최종 답변으로 새지 않고 `FINAL_BLOCKED_BY_GATEKEEPER`가 출력되는 것을 확인했다.

## Verification

```powershell
python -m compileall songryeon_core main.py
```

결과: 통과.

```powershell
python main.py smoke-test
```

결과: 통과. `SMOKE_TEST_OK`.

ORDER_110 관련 smoke 결과:

```text
node4_recent_memory_guard_pass=pass
node4_recent_memory_guard_without_context=needs_revision
node4_recent_memory_guard_unsupported=needs_revision
node4_recent_memory_guard_internal_id=needs_revision
node4_recent_memory_guard_truncated=needs_revision
node4_recent_memory_guard_safe_blocking=true
```

## 범위 밖

이번 작업은 다음을 구현하지 않았다.

- node_5 기억 압축기
- 장기기억 DB
- vector DB
- memory graph
- node_4에서 node_3로 자동 remand하는 재작성 루프
- raw 원문 삭제
- 기억 요약 승인
