# ORDER 271 Local Turn Wall-Clock Observation 실행 기록

## 1. 실행 일자

- 2026-07-18

## 2. 작업 배경

ORDER 269/270으로 개별 LLM 호출 시간과 transport timeout은 확인할 수 있게 됐지만,
사용자가 실제로 기다린 한 턴 전체 시간은 별도 절대정보로 남지 않았다. 전체 턴 제한을
성급하게 추가하지 않고, 먼저 전체 대기시간을 관측할 수 있는 작은 계기판을 만들었다.

## 3. 구현 내용

- `run_fake_user_turn()`과 `run_qwen_user_turn()` 진입 시 `time.monotonic_ns()`를 기록한다.
- 응답을 반환하기 직전에 `turn_timing` runtime metadata를 붙인다.
- 정상 응답뿐 아니라 Qwen의 `blocked`, `skipped`, `structure_failed` 반환에도 같은 구조가
  보존된다.
- terminal은 `전체 턴 시간 [CODE/LOCAL_USER_TURN_WALL_CLOCK]`을 표시한다.
- 이 값은 TraceStore/DataStore 사건이 아니라 `response_runtime_only` 관측값임을 드러낸다.

기록 필드는 다음과 같다.

```text
timing_status=recorded
scope=local_user_turn_entry_to_response
execution_duration_ms=<code measured integer>
record_scope=response_runtime_only
generated_by=CODE:LOCAL_USER_TURN_WALL_CLOCK
info_class=absolute
semantic_judgement_status=not_run
```

## 4. 정보 경계

전체 턴 시간과 기존 LLM call 합계는 각각 code가 측정한 절대정보다. 두 값의 차이가
검색, 파일 읽기, schema 검증, renderer 중 어디에서 발생했는지는 이번 코드가 추측하지
않는다. 실행 중단이나 노드 생략 정책도 추가하지 않았다.

## 5. 검증 결과

```text
python -m compileall songryeon_core main.py
-> passed

ORDER 269/270/271 표적 pytest
-> 10 passed in 0.45s

python -m pytest
-> 498 passed, 1 skipped, 5 deselected in 150.14s

python main.py smoke-test
-> SMOKE_TEST_OK in 153s
-> trace_count=55, data_record_count=93
```

Windows host에서 symbolic link 생성 권한이 없어 ORDER 267 테스트 하나가 기존과 같이
skip됐다.

## 6. 일부러 하지 않은 것

- 전체 턴 wall-clock timeout
- 노드 호출 생략 또는 retry 변경
- L/R 반복 횟수와 도구 예산 변경
- 관측 시간 차이에 대한 code 의미 판단
- LLM call timing schema 변경

## 7. 다음 판단

대표적인 짧은 질문, workspace 파일 조사, L/R 경로에서 `전체 턴 시간`과 `LLM call
timing total_ms`를 비교한 뒤에만 전체 턴 예산 정책을 논의한다.

## 8. 실제 Qwen 대표 질문 3회 측정

같은 로컬 `qwen3:14b`, direct Ollama transport, 호출별 timeout 60초로 세 질문을
순서대로 실행했다. 동시에 실행하지 않았다.

### 8.1 검색 없는 해석 질문

```text
질문 종류 = 외부 문서/그래프 조사가 필요 없는 한 문단 의견
route = 2
turn_execution_duration_ms = 40172
llm_call_count = 5
llm_call_total_ms = 40172
slowest = node_2 answer basis, 13171ms
node_4 = pass
```

### 8.2 외부 workspace 명시 코드 파일 읽기

```text
workspace = songryeon_core/tools
requested_file = workspace_policy.py
route = L -> 2
turn_execution_duration_ms = 94578
llm_call_count = 9
llm_call_total_ms = 94499
actual_read_code_file_unique_count = 1
actual_read_code_file_range_count = 1
read_range = [0, 6923) / total 6923 / not truncated
node_4 = pass
```

최초 L3 의미판단은 `L3 semantic evidence excerpt is too long` schema failure를 기록했다.
그러나 code-owned 원문 확보 상태는 `original_material_acquired`, 원문 요구 충족으로
보존됐고 node_3에는 코드 원문 1개가 공급됐다.

### 8.3 내부 발주서 명시 문서 읽기

```text
requested_file = ORDER_270_DIRECT_OLLAMA_TRANSPORT_TIMEOUT_AND_HONEST_RECOVERY_V0.md
resolved_file = 04_Orders/ORDER_270_DIRECT_OLLAMA_TRANSPORT_TIMEOUT_AND_HONEST_RECOVERY_V0.md
route = L -> 2
turn_execution_duration_ms = 91609
llm_call_count = 10
llm_call_total_ms = 88812
actual_read_doc_count = 1
read_doc_chars = 2263 / not truncated
slowest = L3_document_summary, 11813ms
node_4 = pass
```

최초 L3 의미판단은 `L3 semantic evidence excerpt must be copied exactly from supplied
material` schema failure를 기록했다. 별도 L3 문서 요약은 성공했고 node_3는 그 요약을
받아 답변했으며 node_4가 통과시켰다.

## 9. 관찰 판정

1. 세 표본 모두 configured timeout 안에 완료됐고 최종 gate를 통과했다.
2. 이 세 표본에서는 전체 턴 시간 대부분이 기록된 순차 LLM 호출 시간과 겹쳤다.
3. 검색 없는 경로도 Qwen을 5회 호출해 약 40초가 걸렸다.
4. L 경로는 9~10회 호출되어 약 92~95초가 걸렸다.
5. 두 L 표본 모두 실제 원문은 확보했지만 최초 L3 schema 검증이 실패했다. 전체 턴
   timeout 정책보다 먼저 이 반복 실패의 입력·출력 계약을 좁게 감사할 가치가 있다.

이 세 표본만으로 일반 성능이나 평균 시간을 단정하지 않는다.
