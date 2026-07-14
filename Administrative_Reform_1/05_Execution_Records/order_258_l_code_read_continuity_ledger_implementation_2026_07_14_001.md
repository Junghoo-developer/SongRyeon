# ORDER 258 실행 기록: L Code Read Continuity Ledger v0

## 결과

구현 및 검증 완료.

## 문제

기존 `read_code_file`은 파일 앞부분을 최대 12,000자까지 반환했지만, L revision과 downstream은
다음 절대정보를 하나의 연속 장부로 보존하지 못했다.

- 실제 코드 경로
- 반환된 문자 구간
- 전체 파일 문자 수
- 구간 앞뒤의 잘림 여부
- code-read 최대/사용/남은 호출 횟수

그 결과 같은 파일 앞부분을 다시 읽어도 런타임이 어느 구간을 읽었는지 정확히 설명하기 어려웠다.

## 구현

### read_code_file 경계

`read_code_file`에 선택적인 `start_char`를 추가했다. 결과 payload는 다음 절대정보를 기록한다.

```text
file_path
requested_start_char
range_start_char
range_end_char_exclusive
returned_char_count
total_char_count
truncated_before
truncated_after
truncated
```

구간 표기는 `[range_start_char, range_end_char_exclusive)` 규칙을 사용한다.

### L code-read 장부와 예산

`ToolUseBudgetFrame`에 `max_read_code_file_calls`, `read_code_file_count`,
`read_code_file_ranges`를 추가했다. 최대 횟수는 기존
`LToolBudgetPartitionFrame.code_read_budget`에서 가져온다.

사용 횟수가 최대 횟수를 넘으면 기존 validator 경계에서 실패하며, silent clamp는 하지 않는다.

### revision과 downstream 보존

- `L2RevisionInputFrame`이 직전 code tool 이름, range history, 남은 code-read 횟수를 받는다.
- revision L3 source bundle에 최초 tool scope와 budget partition ID를 계속 넣는다.
- `LLoopContinuationFrame`과 `LLoopReturnSummaryFrame`이 range와 남은 예산을 보존한다.
- `Node3InputBriefFrame`과 node_3 LLM payload가 path/range/truncation을 받는다.
- terminal이 최신 code-read 사용량과 최근 3개 range를 표시한다.

이 값들은 code가 확정한 절대정보이며, 어느 다음 구간이 의미상 중요한지는 code가 판단하지 않는다.

## 검증

```text
python -m compileall songryeon_core main.py
passed

ORDER 258 집중 테스트
5 passed

기존 L code/budget/material 회귀 테스트
25 passed

python -m pytest
448 passed, 5 deselected in 80.12s

python main.py smoke-test
SMOKE_TEST_OK in 95.4s

git diff --check
passed
```

검증한 경우는 다음과 같다.

- `start_char=3`, `max_chars=4`가 정확히 `[3, 7)`을 반환한다.
- 앞뒤 원문이 모두 남아 있으면 두 truncation flag가 모두 참이다.
- code-read 예산 0에서 range 1개를 기록하려 하면 validator가 실패한다.
- revision L2가 code path/range history와 남은 호출 1회를 보존한다.
- 실제 L 실행의 budget, 0 반환 요약, node_3 brief/payload가 같은 range를 보존한다.
- terminal이 `read_code_file=사용/최대`와 최근 range를 표시한다.

## 일부러 하지 않은 것

- L2의 자동 다음 구간 선택
- 의미상 중요한 코드 위치를 고르는 키워드 휴리스틱
- code-read 예산 증액
- node_4 guard, R/W loop, scheduler, 외부 DB 변경
- same-turn L reroute 횟수 변경

## 남은 위험

- 이번 MVP는 책갈피와 남은 표를 만든 단계다. L2가 `start_char`를 직접 선택해 다음 구간을
  읽는 실행 계약은 아직 없다.
- 문자 위치는 해당 호출 시점의 파일 내용 기준이다. 파일이 바뀐 뒤 과거 range를 현재 파일의
  동일 위치라고 간주하면 안 된다.
- 실제 Qwen revision이 이 장부를 보고 다음 읽기 전략을 얼마나 잘 세우는지는 후속 live 시험 대상이다.
