# ORDER_144_R_ROUTE_DRY_RUN_ONLY_V0

## Status

구현 완료.

ORDER_139~143 결과 위에서 구현한다.

이 발주는 Qwen live R route가 아니다.

실행 기록:

- `Administrative_Reform_1/05_Execution_Records/order_144_r_route_dry_run_only_2026_06_30_001.md`

## 1. 목표

R route를 실제 qwen-chat에 여는 것이 아니라, dry-run/fake adapter 환경에서만 R루프 골격을 좁게 실행해 본다.

핵심:

```text
route=R을 live runtime에 열지 않는다.
dry-run/fake-turn에서만 R1/R2/R3 frame 흐름을 검증한다.
```

## 2. 선행 조건

- ORDER_139 graph memory foundation 완료.
- ORDER_140 R frame/state machine 설계 완료.
- ORDER_143 node_0 R handoff packet 완료.

## 3. dry-run 흐름 후보

```text
0 -> R guide handoff
R1 fake goal frame
R2 fake selection frame
R3 fake inspection frame
R continuation controller
R return summary
1 receives R return summary
```

이 흐름은 fake adapter와 deterministic fixture만 사용한다.

LLM 호출은 하지 않는다.

## 4. R return summary 후보

필드 후보:

```text
r_loop_task_status
selected_entry_node_ids
inspected_graph_node_ids
final_information_granularity
summary_depth_used
continuation_status
budget_status
source_graph_node_ids
source_data_ids
source_trace_ids
generated_by
info_class
semantic_judgement_status
```

## 5. route 연결 경계

이번 후보 발주가 승격되더라도 다음은 금지한다.

- node_1 LLM/router가 실제 route=R을 고르게 하지 않는다.
- qwen-chat에서 R루프를 실행하지 않는다.
- node_3 final answer에 R 결과를 주입하지 않는다.
- R 결과를 stable CoreEgo truth로 표시하지 않는다.

## 6. 테스트 후보

1. dry-run fixture에서 R handoff -> R1 -> R2 -> R3 -> return summary가 생성된다.
2. fake R2는 허용된 graph node id만 선택한다.
3. fake R3의 `continue_deeper` 결과가 controller에 보존된다.
4. 예산 소진 시 `stop_budget_exhausted`로 닫힌다.
5. qwen-turn/qwen-chat 기본 route에는 R이 열리지 않는다.
6. terminal runtime은 dry-run R 상태를 code/fake로 표시한다.

## 7. 완료 조건

구현 후 다음을 통과해야 한다.

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
git diff --check
```
