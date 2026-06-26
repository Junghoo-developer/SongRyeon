# L3 Continuation Memory Packet 2026-06-24 001

## 목적

ORDER 089의 3단계인 `0 summary`를 구현했다.

L3가 `partial`, `failed`, `missing` 계열의 판정을 낸 뒤 곧바로 route=2로 내려가기 전에, 0이 L2 재시도에 필요한 정보를 구조화된 memory packet으로 공급할 수 있게 하는 것이 목적이다.

## 구현 파일

- `songryeon_core/nodes/node_0_memory_supplier.py`
- `songryeon_core/runtime/smoke_test.py`
- `Administrative_Reform_1/04_Orders/ORDER_089_L_LOOP_CONTINUATION_V0.md`

## 추가된 0 mode

```text
l3_continuation_summary_for_L2
```

이 mode는 L3 이후 L2 재검색을 준비할 때 쓰는 0의 기억 공급 모드다.

## 핵심 함수

```text
record_l3_continuation_summary_for_l2(...)
build_l3_continuation_summary_items(...)
```

`record_l3_continuation_summary_for_l2`는 다음을 수행한다.

1. `LLoopContinuationFrame`을 읽는다.
2. 그 frame이 가리키는 `L3:achievement_frame`과 `L2:query_frame`을 읽는다.
3. 값을 해석하지 않고, 필요한 필드를 `MemoryItem`으로 복사한다.
4. `memory_packet:L2:l3_continuation_summary_for_L2:{attempt}` record를 남긴다.

## memory packet에 들어가는 정보

현재 smoke 기준으로 다음 항목이 들어간다.

- `l_loop_continuation_status`
- `l3_goal_status_copy`
- `l3_feedback_text_copy`
- `previous_l2_query_copy`
- `tool_budget_status_copy`
- `read_and_unread_candidate_ids_copy`

## 메타정보 원칙

이번 구현에서 0은 의미판단을 하지 않는다.

L3 reason, 이전 L2 query, 읽은 문서 후보 등은 모두 원본 record에서 복사한 값이다. 따라서 memory item text에는 다음 식별자를 사용했다.

```text
CODE_STATUS:...
COPIED_FIELDS:...
```

`generated_by`는 계속 `CODE:RULE_STUB`이고, `llm_semantic_summary_status`는 `not_run`이다.

## 중요한 미구현 사항

아직 실제 live runtime에서 `continue -> 0 -> L2` 재실행 그래프를 연결하지 않았다.

즉, 지금 구현은 다음 단계의 안전한 부품이다.

```text
L3 partial/failed
-> LLoopContinuationFrame 기록
-> 0이 L2용 continuation memory packet 기록 가능
```

다음 단계에서 해야 할 일은 다음이다.

- L루프 내부에서 continuation decision이 `continue`일 때 0 summary helper를 실제 호출한다.
- L2가 `revision_query_plan` 모드로 해당 memory packet을 입력받게 한다.
- 도구 실행 후 L3를 다시 호출한다.
- runtime view에 continuation attempt를 표시한다.

## 검증

```text
python -m compileall songryeon_core main.py dry_run.py
python main.py smoke-test
```

검증 결과:

```text
SMOKE_TEST_OK
l_loop_continuation_stop = stop_achieved
l_loop_continuation_continue = continue
l3_continuation_memory_mode = l3_continuation_summary_for_L2
l3_continuation_memory_item_count = 6
```

