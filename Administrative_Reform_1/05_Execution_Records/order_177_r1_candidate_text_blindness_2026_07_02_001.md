# ORDER 177 Execution Record: R1 Candidate Text Blindness

## Summary

ORDER_177을 구현했다.

R1이 Vessel 후보 summary 본문이나 개별 후보 샘플에 끌려 사용자 질문 밖으로 graph search goal이 새는 문제를 줄이기 위해, R1 input을 packet-level count/kind/depth/budget 중심으로 제한했다.

## Changed Files

- `songryeon_core/loops/r_loop_vessel_one_step.py`
- `songryeon_core/runtime/fast_test.py`
- `tests/test_order_177_r1_candidate_text_blindness.py`
- `Administrative_Reform_1/04_Orders/ORDER_177_R1_CANDIDATE_TEXT_BLINDNESS_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`

## Behavior

- R1 input에서 candidate sample과 summary text를 제거했다.
- R1은 다음만 본다.
  - user question
  - read packet id
  - entry candidate count
  - summary candidate count
  - summary count by data kind
  - summary count by depth
  - one-step policy
  - candidate text visibility policy note
- R2는 기존처럼 후보 목록과 summary text를 볼 수 있다.
- R3는 R2가 선택한 후보 하나의 record를 볼 수 있다.
- R1 graph_search_goal이 user question의 명시 ASCII anchor를 전혀 보존하지 않으면 schema failure로 닫는다.
- 이 anchor 검사는 의미 판단이 아니라 사용자 질문에 명시된 영문/숫자 토큰을 완전히 버리는 drift를 막는 최소 구조 검사다.

## Verification

```powershell
python -m compileall songryeon_core main.py
```

통과.

```powershell
python -m pytest tests/test_order_176_vessel_r_one_step_traversal.py tests/test_order_177_r1_candidate_text_blindness.py -q
```

결과: `9 passed in 0.15s`

```powershell
python main.py fast-test --profile graph
```

결과: `FAST_TEST_OK`, `117 passed in 51.07s`

```powershell
python main.py smoke-test
```

결과: `SMOKE_TEST_OK`

```powershell
git diff --check
```

통과.

## Non-goals Preserved

- R route를 기본 live route로 열지 않았다.
- R2/R3의 선택/충분성 품질을 크게 바꾸지 않았다.
- multi-step Vessel traversal을 열지 않았다.
- Neo4j write를 수행하지 않았다.
- summary 생성/수정/무효화를 하지 않았다.
