# ORDER 271: Local Turn Wall-Clock Observation v0

## 1. 배경

ORDER 269는 개별 LLM 호출의 시작·종료·경과시간을 기록했고, ORDER 270은 direct
Ollama transport에 호출별 timeout을 실제로 연결했다. 그러나 한 사용자 턴 전체가
얼마나 걸렸는지는 runtime 결과에 별도 절대정보로 남지 않는다.

개별 LLM 호출 시간만으로는 검색, 파일 읽기, schema 검증, renderer를 포함한 전체
사용자 대기시간과 비교할 수 없다. 전체 턴 제한을 도입하기 전에 먼저 관측값이 필요하다.

## 2. 목표

fake/Qwen 로컬 사용자 턴의 진입부터 응답 dict 반환 직전까지 wall-clock 경과시간을
code가 측정해 runtime 응답과 terminal에 표시한다.

## 3. 구현 범위

1. `time.monotonic_ns()`로 local user turn 경과시간을 측정한다.
2. 정상, blocked, skipped, structure_failed 응답에 같은 `turn_timing` 구조를 붙인다.
3. 다음 절대정보를 보존한다.
   - `timing_status=recorded`
   - `scope=local_user_turn_entry_to_response`
   - `execution_duration_ms`
   - `record_scope=response_runtime_only`
   - 생성자와 정보 등급, 의미판단 미실행 상태
4. terminal에서 전체 턴 시간과 기존 LLM 호출 시간표를 함께 볼 수 있게 한다.

## 4. 정보 권한

- 경과시간과 측정 범위는 code-owned absolute 정보다.
- 전체 턴 시간과 LLM 호출 합계의 차이가 왜 생겼는지는 이번 코드가 의미 판단하지 않는다.
- 이 관측값은 TraceStore/DataStore 사건이 아니라 사용자 응답 runtime metadata다.

## 5. 금지

- 전체 턴 timeout 또는 강제 중단 추가
- 노드 호출 생략, retry, L/R 반복 횟수 변경
- 두 시간의 차이를 검색 비용이나 renderer 비용으로 단정
- 외부 API, Neo4j, 심야정부 변경
- 기존 LLM call timing schema 변경

## 6. 완료 조건

1. fake/Qwen 로컬 턴 응답에 `turn_timing`이 존재한다.
2. Qwen의 blocked/structure_failed 경로에서도 시간이 사라지지 않는다.
3. terminal이 전체 턴 경과시간을 code absolute로 표시한다.
4. 기존 LLM 호출별 시간표와 timeout 진단이 유지된다.
5. compileall, 표적 pytest, 전체 pytest, smoke-test를 통과한다.

## 7. 후속 경계

관측값을 여러 live 시험에서 모은 뒤에만 전체 턴 wall-clock budget 필요 여부를 결재한다.
ORDER 271은 계기판만 추가하며 실행 정책은 바꾸지 않는다.
