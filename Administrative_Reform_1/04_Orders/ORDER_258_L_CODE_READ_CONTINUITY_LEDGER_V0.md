# ORDER 258: L Code Read Continuity Ledger v0

## 상태

구현 및 검증 완료.

## 배경

기존 라이브 실행에서 L loop는 같은 코드 파일을 여러 번 읽었지만 질문에 필요한 뒤쪽 구현까지 도달하지 못했다.

감사 결과 다음 절대정보가 서로 이어지지 않았다.

- 어떤 코드 경로를 읽었는가
- 파일의 어느 문자 구간을 반환했는가
- 파일 앞/뒤가 잘렸는가
- code read 예산을 몇 번 사용했고 몇 번 남았는가
- revision L2/L3와 node_3가 이 경계를 계속 볼 수 있는가

## 목표

L loop의 code-read continuity를 위한 절대정보 장부와 downstream 전달 경계를 만든다.

### 1. read_code_file 결과 경계

`read_code_file` 결과에 다음 값을 기록한다.

- `file_path`
- `range_start_char`
- `range_end_char_exclusive`
- `returned_char_count`
- `char_count` 또는 `total_char_count`
- `truncated_before`
- `truncated_after`
- 호환용 `truncated`

도구는 optional `start_char`를 받을 수 있다. 이번 발주에서는 L2가 다음 start_char를 자동 선택하지 않는다.

### 2. code-read 예산 장부

`ToolUseBudgetFrame`에 다음 값을 추가한다.

- 최대 code read 횟수
- 실제 code read 횟수
- 남은 code read 횟수를 계산할 수 있는 구조
- 읽은 code path/range record 목록

`LToolBudgetPartitionFrame.code_read_budget`을 최대 code read 횟수의 source로 사용한다.

### 3. revision 기억 보존

`L2RevisionInputFrame`은 다음 절대정보를 받는다.

- 직전 실제 code tool 이름
- 이미 읽은 code path/range 목록
- 남은 code read 횟수

revision L3 입력에는 최초 `L_tool_scope_frame`과 code budget partition ID를 계속 포함한다.

### 4. node_3 및 terminal 표시

node_3 brief와 LLM payload에 code-read boundary를 공급한다.

- 전체 파일을 읽었는지
- 앞부분 또는 뒷부분이 잘렸는지
- 실제 공급 text가 어느 문자 구간인지
- code read 예산이 얼마나 남았는지

terminal은 최신 code read count/budget과 최근 range를 사람이 읽을 수 있게 표시한다.

## 메타정보 경계

- path, range, count, truncation, budget은 code가 확정하는 절대정보다.
- 어느 다음 구간이 의미상 중요한지는 code가 판단하지 않는다.
- LLM이 다음 구간을 선택하도록 만드는 자동화는 후속 발주로 미룬다.
- 같은 코드가 중요하다는 키워드 휴리스틱을 추가하지 않는다.

## 금지

- 예산 수치 증액
- L2의 자동 next-range 선택
- 파일 의미를 code가 해석하는 휴리스틱
- raw tool event 삭제
- node_4 guard 약화
- W/R/scheduler/외부 DB 변경
- same-turn L reroute 횟수 변경

## 완료 조건

1. `read_code_file(start_char=N)`이 실제 반환 범위와 truncation을 정확히 기록한다.
2. `ToolUseBudgetFrame`이 code-read 사용량과 range history를 보존한다.
3. code-read 사용량이 최대 예산을 넘으면 validator가 실패한다.
4. revision input이 code read history와 남은 예산을 보존한다.
5. revision L3가 최초 code tool scope source를 잃지 않는다.
6. node_3 brief/payload가 code path/range/truncation을 보존한다.
7. terminal에서 code-read budget과 range를 구분해 볼 수 있다.
8. `python -m compileall songryeon_core main.py` 통과.
9. `python -m pytest` 통과.
10. `python main.py smoke-test` 통과.
