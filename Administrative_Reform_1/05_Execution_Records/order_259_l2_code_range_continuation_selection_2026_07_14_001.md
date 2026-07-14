# ORDER 259 실행 기록: L2 Code Range Continuation Selection v0

## 결과

구현 및 검증 완료.

## 출발점

ORDER 258 이후 L2는 이미 읽은 코드 경로, 문자 구간, truncation, 남은 code-read 예산을
볼 수 있었다. 그러나 L2 query schema에 시작 위치가 없어서 같은 파일을 다시 선택하면
`start_char=0`으로 앞부분을 반복해서 읽었다.

## 구현

### code-owned continuation option

`build_code_read_continuation_options()`가 성공한 `CodeReadRangeRecord`만 읽고 다음 값을 만든다.

```text
file_path
start_char
previous_range_end_char_exclusive
total_char_count
remaining_char_count
source_tool_result_data_id
```

다음 시작점은 기존 range의 exclusive end와 정확히 같고, 같은 파일에서 이미 해당 위치로
시작한 성공 range가 있으면 option을 만들지 않는다. 파일명이나 코드 내용의 의미는 보지 않는다.

### L2 선택과 이중 검증

`L2QueryPlanCandidate`와 `L2QueryFrame`에 `read_code_file_start_char`를 추가했다.

- 일반 최초 L2는 항상 0만 사용한다.
- revision L2가 성공 이력이 있는 파일을 고르면 code가 공급한 `(file_path, start_char)`와
  정확히 일치해야 한다.
- 처음 읽는 새 파일은 0부터 읽을 수 있다.
- 다른 도구 후보는 start 값을 사용할 수 없다.

LLM payload validator에서 한 번 검사하고, revision tool runner가 실행 직전에 같은 range history로
다시 검사한다. query frame을 우회해 잘못된 시작점을 넣어도 실행되지 않는다.

### continuation과 실행

query 예산이 0이어도 다음 조건이면 L continuation이 L2로 열린다.

- L3가 아직 목표를 달성하지 못함
- 전체 tool 예산이 남음
- code-read 예산이 남음
- 아직 실행하지 않은 code continuation option이 있음

revision runner는 L2가 고른 `start_char`를 `read_code_file`에 넘긴다. 실행 결과는 ORDER 258의
range ledger에 누적되며, terminal은 revision query의 선택 시작점을 표시한다.

테스트를 위해 revision runner에 선택적 `code_root`를 추가했다. 운영 기본값은 기존 workspace
루트를 그대로 유지한다.

## 검증

```text
python -m compileall songryeon_core main.py
passed

ORDER 259 전용 테스트
7 passed

ORDER 258+259 전용 테스트
11 passed

관련 L 회귀 테스트
32 passed

python -m pytest
455 passed, 5 deselected in 81.96s

python main.py smoke-test
SMOKE_TEST_OK in 106.3s

git diff --check
passed
```

검증한 경우는 다음과 같다.

- `[0, 12000)` 다음 option은 12000이다.
- `[12000, 24000)`을 읽으면 12000 option은 사라지고 24000이 새 option이 된다.
- L2가 정확한 option을 고르면 query frame에 12000이 보존된다.
- L2가 같은 파일의 0을 다시 고르면 schema가 실패한다.
- 최초 L2가 nonzero 시작점을 쓰면 실패한다.
- query 예산 0에서도 code continuation option이 있으면 L2로 이어진다.
- 실제 25,000자 파일에서 두 번째 호출이 `[12000, 24000)`의 12,000자를 반환한다.
- terminal이 `code range start: 12000`을 표시한다.

## 일부러 하지 않은 것

- code의 의미 기반 file/range 우선순위 선택
- 파일명, 함수명, 키워드 휴리스틱
- 예산 증액
- L3의 partial/achieved 의미 판단 대체
- W/R/scheduler/외부 DB 변경
- same-turn L reroute 횟수 변경

## 남은 위험

- 실제 Qwen L2가 새 필드를 정확히 출력하고 적절한 option을 고르는 품질은 별도 live 시험이 필요하다.
- 한 턴 도중 파일 내용이 바뀌면 과거 문자 위치의 의미가 달라질 수 있다. 이번 order는 동일 L 실행
  안에서 코드 파일이 안정적이라는 현재 실행 전제를 유지한다.
- L3가 첫 구간만으로도 목표를 달성했다고 판단하면 continuation은 열리지 않는다. truncation 자체를
  code가 의미상 실패로 강제하지 않은 것은 의도된 경계다.
