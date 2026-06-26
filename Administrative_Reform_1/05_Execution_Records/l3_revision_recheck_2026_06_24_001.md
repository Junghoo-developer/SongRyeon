# L3 Revision Recheck 2026-06-24 001

## 목표

`ORDER_089_L_LOOP_CONTINUATION_V0`의 다음 조각으로, L2 revision tool attempt 이후 L3가 그 결과를 다시 보존하고 continuation controller가 그 새 L3 판정을 읽을 수 있게 했다.

이번 구현은 live graph 자동 반복이 아니다. 먼저 작은 단위로 다음 흐름이 가능한지 확인했다.

```text
L2 revision query frame
-> revision tool attempt
-> L3 revision recheck
-> continuation decision
```

## 구현 내용

- `songryeon_core/nodes/l3_result_keeper.py`
  - `run_l3_revision_result_keeper` 추가.
  - `L3:revision_preserved_info:0001`, `L3:revision_achievement:0001` 형식의 attempt별 data id 추가.
  - 기존 `L2:query_frame`뿐 아니라 `L2:revision_query_frame:*`도 L3 micro-goal의 query evidence로 인정하도록 보정.

- `songryeon_core/loops/l_loop_continuation.py`
  - `record_l_loop_continuation_decision`이 기본 L3/L2 frame뿐 아니라 호출자가 지정한 L3 achievement frame과 L2 query frame을 읽을 수 있게 확장.

- `songryeon_core/runtime/smoke_test.py`
  - `l3_revision_recheck_status`
  - `l3_revision_recheck_candidates`
  - `l3_revision_continuation`
  항목을 smoke 결과에 추가.

## 메타정보 경계

- L3 revision recheck는 LLM 의미 판단을 새로 실행하지 않는다.
- `achievement_generation_source`는 `CODE:OPERATION_CHECK`로 남는다.
- `llm_semantic_judgement_status`는 `not_run`으로 남는다.
- 이 단계는 "도구 결과 후보가 생겼다"는 구조적 재포장이지, "사용자 목표가 최종 성공했다"는 선언이 아니다.

## 검증

실행:

```powershell
python -m compileall songryeon_core
python main.py smoke-test
```

결과:

```text
SMOKE_TEST_OK
l3_revision_recheck_status = partial
l3_revision_recheck_candidates = 2
l3_revision_continuation = continue
```

## 남은 일

- live L루프에 자동 반복 배선을 연결한다.
- runtime pretty view에서 revision recheck와 second continuation을 노출한다.
- revision attempt 이후 controller success를 어떤 조건에서 만들지 별도 발주/토의로 정한다.
