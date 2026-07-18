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
