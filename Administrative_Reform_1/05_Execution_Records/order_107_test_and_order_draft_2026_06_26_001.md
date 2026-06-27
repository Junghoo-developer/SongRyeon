# ORDER 107 Test And Order Draft 2026-06-26 001

## 요청

사용자가 ORDER_105 구현 보고 이후 다음 단계로 테스트와 발주서 작성을 요청했다.

## 테스트 결과

### compileall

명령:

```powershell
python -m compileall .\songryeon_core .\main.py
```

결과:

```text
passed
```

### smoke-test

명령:

```powershell
python .\main.py smoke-test
```

결과:

```text
SMOKE_TEST_OK
```

확인한 주요 값:

```text
live_trace_line_count=12
live_trace_matches_trace_count=true
live_trace_no_report_body=true
recent_memory_relevance_selection_selected=selected
recent_memory_relevance_selection_none=none_selected
recent_memory_relevance_selection_failed=failed
recent_memory_relevance_selection_no_candidates=none_selected
memory_selection_handoff_status=selected
memory_selection_handoff_selected_count=1
memory_selection_boundary_mixed=true
memory_selection_node3_selected_count=1
memory_selection_no_raw_answer_leak=true
```

### fake-turn live trace

명령:

```powershell
python .\main.py fake-turn "최근 기억 선택과 진행상황을 확인해줘" --live-trace
```

결과:

```text
status=ok
trace_count=55
node4_gate_status=pass
recent_memory_relevance_selection_status=none_selected
recent_memory_relevance_selection_candidate_count=0
recent_memory_relevance_selection_selected_count=0
```

비고:

이 수동 실행은 새 임시 턴 기준이라 recent memory 후보가 0개로 닫혔다.
live trace line은 생성되었고, report 본문 streaming은 하지 않았다.

### qwen-turn live trace

명령:

```powershell
python .\main.py qwen-turn "최근 기억 선택과 진행상황을 확인해줘" --timeout 120 --pretty --live-trace
```

결과:

```text
상태=ok
trace/data=71/103
task ledger=16/16
node4_gate_status=pass
recent memory selector status=none_selected
candidates=0
selected=0
```

확인:

- Qwen 경로에서도 live trace가 trace_000001부터 trace_000071까지 출력되었다.
- 최근 기억 후보가 없을 때 selector는 `CODE_STATUS:no_memory_relevance_candidates`로 닫혔다.
- node_3 brief에는 memory selection material이 `status=none_selected`, `selected=0`, `info_class=absolute_status`로 들어갔다.
- node_4는 최종 report를 통과시켰다.

## 발주서 작성

다음 발주서를 추가했다.

- `Administrative_Reform_1/04_Orders/ORDER_107_RAW_MEMORY_WINDOW_AND_COMPRESSION_CANDIDATE_POLICY_V0.md`

ORDER_107의 목표:

```text
최근 원문 기억이 9턴으로 넘칠 때 최신 5턴은 retained raw window로 남기고,
그보다 오래된 4턴은 node_5가 나중에 압축할 compression candidate 좌표로 분리한다.
```

## 비고

ORDER_107은 구현하지 않았다.

이번 작업은 테스트와 발주서 작성만 수행했다.
