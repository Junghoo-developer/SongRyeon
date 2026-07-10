# order_211_node4_vessel_r_status_name_consistency_guard_2026_07_08_001

## 작업 범위

ORDER_211 Node4 Vessel R Status Name Consistency Guard를 구현했다.

## 구현 내용

- `songryeon_core/nodes/node_4_gatekeeper.py`
  - Vessel R material 상태명 정합성 guard를 추가했다.
  - `vessel_r_material_status` / `vessel_r_material.r_loop_task_status`가 brief와 다른 상태명으로 직접 표기되면 `CODE_STATUS:vessel_r_material_claim_mismatch`로 막는다.
  - 성공 과장 guard, document evidence role guard, graph node ID leak guard는 유지했다.

- `tests/test_order_211_vessel_r_status_name_guard.py`
  - `failed` 상태를 `insufficient`로 직접 표기한 답변을 node_4가 `needs_revision` 처리하는지 검증했다.
  - 일반적인 "자료가 제한된다" 표현은 과도하게 막지 않는지 검증했다.

## 보강한 경계

이번 guard는 모든 "부족하다" 표현을 막지 않는다.
다음처럼 상태 필드/상태명 문맥이 직접 드러날 때만 검사한다.

```text
`vessel_r_material.task_status`는 `insufficient`
status=insufficient
R 탐색 상태는 partial
```

## 검증

```powershell
python -m pytest tests\test_order_211_vessel_r_status_name_guard.py tests\test_order_212_runtime_vessel_r_failure_diagnostics.py -q
python -m pytest tests\test_order_193_r_result_to_node3_vessel_material.py tests\test_order_200_vessel_r_live_gated_integration.py tests\test_order_209_learning_absolute_audit_panel.py tests\test_order_211_vessel_r_status_name_guard.py tests\test_order_212_runtime_vessel_r_failure_diagnostics.py -q
```

결과:

- ORDER_211/212 좁은 테스트: 3 passed
- 관련 R/material/runtime 테스트 묶음: 14 passed

## live 확인

live qwen 재확인에서 node_3 답변은 이번에는 `failed` 상태를 그대로 말했고 node_4가 pass했다.
따라서 guard가 실제 답변을 불필요하게 막지는 않았고, 상태명 오표기 케이스는 pytest로 고정했다.

## 미구현

- R2 schema 실패 원인 자체는 고치지 않았다.
- node_4 자동 재작성 루프는 열지 않았다.
