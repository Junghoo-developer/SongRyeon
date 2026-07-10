# order_214_r3_schema_repair_once_2026_07_08_001

## 작업 범위

ORDER_214 R3 Schema Repair Once를 구현한다.

## 구현 내용

- `songryeon_core/loops/r_loop_vessel_one_step.py`
  - R3 enum/status copy-contract 실패에 한해 repair 1회를 허용한다.
  - one-step과 multi-step traverse의 R3 호출부에 동일하게 적용한다.
  - code는 sufficiency/status 의미 판단을 대신하지 않는다.
  - R3 입력 payload에 `allowed_r3_status_values`와 `r3_status_contract`를 추가했다.

- `songryeon_core/prompts/r3_vessel_inspector_v0.md`
  - `schema_repair_request`가 있을 때는 enum/status field만 허용 표에서 다시 고치라는 경계를 추가한다.

- `tests/test_order_214_r3_schema_repair_once.py`
  - one-step R3 enum 실패 repair 통과를 검증한다.
  - multi-step traverse R3 enum 실패 repair 통과를 검증한다.

## 검증

```powershell
python -m compileall songryeon_core\loops\r_loop_vessel_one_step.py
python -m pytest tests\test_order_214_r3_schema_repair_once.py tests\test_order_213_r2_schema_repair_once.py -q
python -m pytest tests\test_order_176_vessel_r_one_step_traversal.py tests\test_order_181_r2_official_selection_ref_map.py tests\test_order_184_r_vessel_multi_step_traversal.py tests\test_order_191_r2_branch_role_surface_stability.py tests\test_order_201_r2_granularity_and_vessel_r_display.py tests\test_order_213_r2_schema_repair_once.py tests\test_order_214_r3_schema_repair_once.py tests\test_order_215_r_traverse_path_duplicate_preservation.py -q
python -m compileall songryeon_core main.py
python main.py smoke-test
```

결과:

- `r_loop_vessel_one_step.py` compileall 통과
- ORDER_213/214 좁은 테스트: 4 passed
- 관련 R loop 테스트 묶음: 19 passed
- 저장소 기본 compileall 통과
- smoke-test 통과: `SMOKE_TEST_OK`

## live 확인

ORDER_214 구현 후 동일 live R traverse를 다시 실행했다.
R3 enum 실패는 더 이상 발생하지 않았다.

다만 R3 repair 이후 `RLoopVesselTraverseResultFrame selected path mismatch` 코드 예외가 드러났고,
이는 ORDER_215에서 별도 장부 패치로 처리했다.
