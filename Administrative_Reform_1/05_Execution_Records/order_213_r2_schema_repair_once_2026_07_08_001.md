# order_213_r2_schema_repair_once_2026_07_08_001

## 작업 범위

ORDER_213 R2 Schema Repair Once를 구현했다.

## 구현 내용

- `songryeon_core/loops/r_loop_vessel_one_step.py`
  - `R2_SCHEMA_REPAIR_MAX_ATTEMPTS = 1`을 추가했다.
  - one-step과 multi-step traverse의 R2 호출을 `_run_r2_with_schema_repair()`로 감쌌다.
  - 최초 R2 호출이 copy-contract 계열 `schema_failed`일 때만 repair 입력을 만들어 한 번 더 호출한다.
  - repair 입력에는 실패 reason, 실패 output 핵심 field, 허용 surface/node ref 표, 허용 granularity enum을 포함한다.
  - repair가 실패하면 기존처럼 R2 schema_failed로 닫는다.

- `songryeon_core/prompts/r2_vessel_node_selector_v0.md`
  - `schema_repair_request`가 있을 때는 보고된 copy-contract field만 고치고,
    `r2_copy_repair_table`의 공식 ref만 사용하라는 경계를 추가했다.

- `tests/test_order_213_r2_schema_repair_once.py`
  - one-step R2 copy-contract 실패가 repair 1회 후 통과하는지 검증했다.
  - multi-step traverse R2 copy-contract 실패가 repair 1회 후 계속 진행되는지 검증했다.

## 원칙 확인

- code가 대신 graph node를 선택하지 않는다.
- R2 validator를 약화하지 않는다.
- 유사도/키워드 fallback을 추가하지 않는다.
- repair는 LLM에게 schema copy-contract를 다시 맞추게 하는 절차이며, 성공 여부는 기존 validator가 다시 판정한다.

## 검증

```powershell
python -m compileall songryeon_core\loops\r_loop_vessel_one_step.py
python -m pytest tests\test_order_213_r2_schema_repair_once.py tests\test_order_176_vessel_r_one_step_traversal.py::test_vessel_r_one_step_rejects_r2_selection_outside_packet tests\test_order_181_r2_official_selection_ref_map.py::test_r2_invented_short_refs_still_fail_with_diagnostics -q
python -m pytest tests\test_order_181_r2_official_selection_ref_map.py tests\test_order_184_r_vessel_multi_step_traversal.py tests\test_order_191_r2_branch_role_surface_stability.py tests\test_order_201_r2_granularity_and_vessel_r_display.py tests\test_order_213_r2_schema_repair_once.py -q
git diff --check
python -m compileall songryeon_core main.py
python main.py smoke-test
```

결과:

- `r_loop_vessel_one_step.py` compileall 통과
- ORDER_213 + 기존 R2 실패 유지 테스트: 4 passed
- 관련 R loop 테스트 묶음: 10 passed
- `git diff --check` 통과
- 저장소 기본 compileall 통과
- smoke-test 통과: `SMOKE_TEST_OK`

전체 pytest도 시도했지만 10분 제한에서 timeout 됐다.
이번 패치 관련 테스트 묶음은 통과했으며, timeout 뒤 남은 python 프로세스는 없음을 확인했다.

## 추가 live 확인

사용자 요청 후 다음 live R traverse를 실행했다.

```powershell
python main.py vessel-r-traverse "송련 Core의 그래프 기억 구조에서 소스 요약과 토큰 묶음 요약이 어떻게 이어지는지 계층적으로 탐색해줘. 과거 대화 기억 가지가 아니라 코드/문서 소스 가지를 우선 보고, 시간축에서 시작해서 어떤 묶음을 거쳐 내려가는지 말해줘." --database neo4j --llm-mode qwen --timeout 180 --format text
```

결과:

```text
status: R_LOOP_VESSEL_TRAVERSE_NOT_PASSED
read_packet_status: passed
step_count: 1
failure_stage: R3:step_0002
failure_type: schema_failed
failure_reason: R3 current_information_granularity is invalid
```

관찰:

- 이전 주요 실패였던 `R2 selected_surface_ref must be in available_surface_refs`는 이 실행에서는 발생하지 않았다.
- R2는 step 2에서 `graph:source_ingest_time_bundle:...` 선택까지 진행했다.
- 새 병목은 R3의 `current_information_granularity` enum copy-contract 실패로 이동했다.
- 따라서 ORDER_213은 R2 copy-contract 병목 완화에는 효과가 있으나, R3에도 유사한 schema repair 또는 enum copy-contract 안정화가 필요할 수 있다.
