# order_212_runtime_vessel_r_failure_diagnostics_display_2026_07_08_001

## 작업 범위

ORDER_212 Runtime Vessel R Failure Diagnostics Display를 구현했다.

## 구현 내용

- `songryeon_core/runtime/dry_run.py`
  - runtime result dict에 다음 필드를 추가했다.
    - `vessel_r_failure_stage`
    - `vessel_r_failure_type`
    - `vessel_r_failure_reason`
    - `vessel_r_final_sufficiency_status`
    - `vessel_r_final_continuation_status`

- `songryeon_core/runtime/user_turn.py`
  - qwen-turn summary payload에 위 Vessel R 실패 진단 필드를 연결했다.

- `songryeon_core/runtime/terminal_view.py`
  - 학습용 절대정보 감사판에 `R/Vessel 실패 진단` 줄을 추가했다.
  - node_3 brief의 Vessel R material 표시 아래에 failure type/reason을 표시했다.
  - failure reason은 긴 raw payload 전체를 펼치지 않고 짧게 표시한다.

- `tests/test_order_212_runtime_vessel_r_failure_diagnostics.py`
  - runtime view가 R failure stage/type/reason을 표시하는지 검증했다.

## live 확인

다음 live 명령으로 확인했다.

```powershell
python main.py qwen-turn "최근 발주서를 기준으로 지금 송련 Core가 어디까지 개발됐는지 브리핑해줘" --timeout 180 --pretty --enable-vessel-r-route --database neo4j
```

확인된 표시:

```text
R/Vessel 실패 진단: stage=R2:step_0004 / type=schema_failed / reason=R2 selected_surface_ref must be in available_surface_refs
Vessel R failure: type=schema_failed / reason=R2 selected_surface_ref must be in available_surface_refs
```

이전에는 같은 상황에서 `node3_vessel_status=failed`까지만 보여서 단독 R traverse 명령을 다시 돌려야 원인을 볼 수 있었다.
이제 qwen-turn pretty 출력만으로도 R2 schema 실패 계열 병목을 바로 확인할 수 있다.

## 검증

```powershell
python -m compileall songryeon_core\nodes\node_4_gatekeeper.py songryeon_core\runtime\dry_run.py songryeon_core\runtime\terminal_view.py songryeon_core\runtime\user_turn.py
python -m pytest tests\test_order_211_vessel_r_status_name_guard.py tests\test_order_212_runtime_vessel_r_failure_diagnostics.py -q
python -m pytest tests\test_order_193_r_result_to_node3_vessel_material.py tests\test_order_200_vessel_r_live_gated_integration.py tests\test_order_209_learning_absolute_audit_panel.py tests\test_order_211_vessel_r_status_name_guard.py tests\test_order_212_runtime_vessel_r_failure_diagnostics.py -q
git diff --check
```

결과:

- compileall 통과
- ORDER_211/212 좁은 테스트: 3 passed
- 관련 테스트 묶음: 14 passed
- git diff --check 통과

## 미구현

- R2 enum/surface schema 실패 자체는 고치지 않았다.
- R traversal 정책이나 후보 선택 정책은 바꾸지 않았다.
- R material을 실패 상태에서 억지로 present로 만들지 않았다.
