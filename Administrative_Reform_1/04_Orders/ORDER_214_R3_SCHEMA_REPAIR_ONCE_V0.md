# ORDER_214_R3_SCHEMA_REPAIR_ONCE_V0

## 상태

즉시 구현 승인.

## 배경

ORDER_213으로 R2의 surface/node ref copy-contract 실패를 1회 repair하게 만들었다.
이후 live R traverse에서 R2 병목은 넘어갔지만 다음 실패가 R3에서 발생했다.

```text
status: R_LOOP_VESSEL_TRAVERSE_NOT_PASSED
read_packet_status: passed
failure_stage: R3:step_0002
failure_type: schema_failed
failure_reason: R3 current_information_granularity is invalid
```

이는 R3가 선택된 노드의 충분성/입도 판단을 하면서,
정해진 enum 값을 정확히 복사하지 못해 validator에서 반려된 것이다.

## 목표

R3 enum/status copy-contract 실패에 한해서 LLM repair를 최대 1회 허용한다.

## 구현 범위

1. R3 최초 호출이 `schema_failed`이고 실패 이유가 다음 enum/status field 계열이면 repair 입력을 만든다.
   - `current_information_granularity`
   - `sufficiency_status`
   - `granularity_problem_status`
   - `branch_problem_status`
   - `recommended_next_action`

2. repair 입력에는 다음을 포함한다.
   - 실패 reason
   - 실패 output의 핵심 field
   - 각 field별 허용 enum 목록
   - 선택된 후보 record와 child 후보 record는 기존 R3 입력 그대로 유지

3. repair 호출은 최대 1회만 한다.
   - 최초 R3 호출 1회
   - repair R3 호출 최대 1회
   - 총 R3 호출 최대 2회

4. repair 후에도 실패하면 기존처럼 `R3:step_N schema_failed`로 닫는다.

## 금지

- validator를 약화하지 않는다.
- code가 sufficiency/status 의미 판단을 대신하지 않는다.
- R3의 `sufficient/insufficient`를 code가 자동 보정하지 않는다.
- 유사도/키워드 fallback을 넣지 않는다.
- R traversal 예산, R2 선택 정책, node_3 답변 정책을 바꾸지 않는다.

## 완료 조건

1. one-step R3 enum/status 실패가 repair 1회 후 통과하는 테스트가 있다.
2. multi-step traverse R3 enum/status 실패가 repair 1회 후 계속 진행되는 테스트가 있다.
3. repair 후에도 기존 validator가 최종 통과 여부를 판정한다.
4. compileall / 관련 pytest / smoke-test가 통과한다.
