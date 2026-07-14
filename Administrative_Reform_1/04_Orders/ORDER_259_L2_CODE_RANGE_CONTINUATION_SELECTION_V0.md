# ORDER 259: L2 Code Range Continuation Selection v0

## 상태

구현 및 검증 완료.

## 배경

ORDER 258은 `read_code_file`의 경로, 실제 문자 구간, 전체 길이, truncation,
최대/사용/남은 code-read 예산을 L2 revision과 downstream에 보존했다.

그러나 L2 출력에는 다음 시작점을 구조적으로 적는 필드가 없어서, 같은 파일을 다시 선택해도
항상 `start_char=0`으로 앞부분을 반복해서 읽었다.

## 목표

L2 revision LLM이 code가 공급한 미열람 연속 구간 후보 중 하나를 선택하고,
revision tool runner가 해당 `start_char`부터 실제 원문을 이어서 읽게 한다.

## 구현 범위

### 1. code-owned continuation option

code는 기존 `CodeReadRangeRecord`만 사용해 다음 구조를 만든다.

- `file_path`
- `start_char`
- `previous_range_end_char_exclusive`
- `total_char_count`
- `remaining_char_count`
- `source_tool_result_data_id`

option은 다음 조건을 모두 만족할 때만 생성한다.

- 직전 range의 `read_status=ok`
- 직전 range의 `truncated_after=true`
- `start_char=직전 range_end_char_exclusive`
- 같은 파일에서 해당 `start_char`로 시작한 range가 아직 없음

이 계산은 의미 판단이 아니라 기존 문자 범위의 절대 연속성 계산이다.

### 2. L2 선택 필드

`L2QueryPlanCandidate`와 `L2QueryFrame`에 `read_code_file_start_char`를 추가한다.

- 일반 최초 L2 read에는 `0`만 허용한다.
- revision L2 read에서 기존에 읽은 파일을 다시 고르면 code가 공급한 option의
  `(file_path, start_char)` 쌍과 정확히 일치해야 한다.
- 처음 읽는 새 파일은 기존 호환을 위해 `start_char=0`을 허용한다.
- 다른 도구 후보는 `read_code_file_start_char=0`이어야 한다.

L2 LLM은 어느 option이 목표에 필요한지 판단한다. code는 의미상 우선순위를 정하지 않는다.

### 3. continuation과 실행

- query 예산이 0이어도 미열람 code continuation option과 code-read 예산이 남으면
  L continuation을 허용한다.
- revision query setter는 선택된 `start_char`를 query frame에 복사한다.
- revision tool runner는 해당 값으로 `read_code_file`을 실행한다.
- tool result와 ORDER 258 range ledger가 실제 새 구간을 다시 기록한다.

### 4. 표시와 추적

- L2 revision input에 continuation option을 보존한다.
- terminal은 L2 revision이 선택한 code path/start_char를 구분해 표시한다.
- 선택값은 절대 실행 인자이며, 선택 이유는 L2 LLM의 판단으로 남긴다.

## 메타정보 경계

- 기존 range, 다음 연속 시작점, 예산, 실제 실행 구간은 절대정보다.
- 어떤 다음 구간을 읽을지는 L2 LLM의 source-bundle 기반 판단이다.
- code는 파일명, 키워드, 함수명의 의미를 보고 다음 구간을 선택하지 않는다.

## 금지

- 코드 키워드 휴리스틱
- code의 의미 기반 file/range 선택
- 같은 prefix 자동 재읽기
- 예산 증액
- L3/node_4 guard 약화
- W/R/scheduler/외부 DB 변경
- same-turn L reroute 횟수 변경

## 완료 조건

1. L2 revision input이 정확한 continuation option을 만든다.
2. L2가 option의 `(file_path, start_char)`를 선택하면 schema가 통과한다.
3. 허용되지 않은 경로/시작점과 이미 읽은 시작점은 실패한다.
4. 일반 최초 L2는 nonzero start를 사용할 수 없다.
5. query 예산 0이어도 code continuation option과 read budget이 있으면 continuation이 열린다.
6. revision 실행 결과의 range가 이전 range 끝에서 이어진다.
7. code-read 사용량과 남은 예산이 ORDER 258 장부에 누적된다.
8. `python -m compileall songryeon_core main.py` 통과.
9. `python -m pytest` 통과.
10. `python main.py smoke-test` 통과.
