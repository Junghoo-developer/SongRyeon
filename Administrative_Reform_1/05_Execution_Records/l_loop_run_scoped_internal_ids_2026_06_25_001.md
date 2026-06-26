# L Loop Run-Scoped Internal IDs - 2026-06-25-001

## 목적

상위 L 재라우팅을 열기 전, 같은 턴에서 L루프가 두 번 실행될 때 L 내부 주요 기록 ID가 충돌하지 않도록 run-scoped ID 구조를 확장했다.

## 변경

- `LRunIds`에 control, continuation, revision, tool catalog, tool choice, tool budget, failure, tool result, tool distillation, continuation memory packet ID 생성 규칙을 모았다.
- `run_index=1`은 기존 legacy ID를 유지한다.
- `run_index>=2`는 legacy ID 앞에 `L:run:0002:` 같은 실행 이름표를 붙인다.
- L1/L2/L3 primary ID뿐 아니라 L 내부 control/tool/budget/revision 계열 호출부에 `id_namespace`를 전달했다.
- `LLoopRunFrame.rerun_block_reason`은 다음 남은 차단 사유를 `node0_return_summary_and_route_reentry_ids` 계열로 바꿨다.

## 아직 열지 않은 것

상위 L 재라우팅은 아직 열지 않았다.

남은 차단 사유:

- `L:return_summary_frame`
- `memory_packet:node_1:loop_return_summary`
- 상위 route 재진입 계열 ID

이 ID들이 아직 고정이므로 `same_turn_rerun_allowed=false`를 유지한다.

## 검증

- `python -m compileall songryeon_core main.py` 통과.
- `python main.py smoke-test` 통과.

smoke-test는 다음을 확인한다.

- `run_index=1`은 기존 ID를 유지한다.
- `run_index=2`는 control/tool/budget/revision 계열 ID를 `L:run:0002:*`로 계산하고 실제 DataStore에 저장한다.
- `LLoopRunFrame.rerun_block_reason`이 다음 남은 차단 사유를 말한다.
- `same_turn_rerun_allowed=false`가 유지된다.
