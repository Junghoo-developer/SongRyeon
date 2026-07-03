# ORDER 185 R Terminal Material Budget And Early Stop Guard 실행 기록

## 결론

ORDER_185를 구현했다.

R Vessel multi-step traversal은 이제 R3가 `sufficient`를 내더라도, terminal material을 아직 하나도 보지 않았고 하위 후보와 예산이 남아 있으면 `stop_sufficient`를 그대로 수용하지 않는다.

## 핵심 변경

- `R_TRAVERSE_MIN_TERMINAL_MATERIAL_READS = 1` 정책 추가.
- terminal material 판정 추가:
  - 텍스트가 있는 summary node
  - raw source node
  - raw capsule node
- `RLoopVesselTraverseResultFrame`에 다음 절대 카운트 추가:
  - `terminal_material_seen_count`
  - `min_terminal_material_count`
  - `early_stop_guard_trigger_count`
- 조기 종료 guard 추가:
  - R3가 sufficient/stop을 내도
  - terminal material count가 최소치보다 낮고
  - child candidate가 있고
  - 예산이 남아 있으면
  - continuation을 `continue_deeper`로 기록한다.
- guard reason:

```text
CODE_STATUS:r_loop_terminal_material_not_seen
```

## 메타정보 경계

code는 답변 의미의 충분성을 판단하지 않았다.

code가 한 일은 다음 절대정보 확인뿐이다.

- 현재까지 terminal material을 몇 개 봤는지
- 현재 노드에 child candidate가 있는지
- traversal budget이 남아 있는지

R2의 후보 선택과 R3의 충분성 판단은 그대로 LLM 책임으로 남겼다.

## 검증

```powershell
python -m pytest tests/test_order_184_r_vessel_multi_step_traversal.py tests/test_order_185_r_terminal_material_guard.py -q
# 3 passed

python -m compileall songryeon_core main.py
# passed

python main.py fast-test --profile graph --skip-compileall
# FAST_TEST_OK
# 134 passed

python main.py smoke-test
# SMOKE_TEST_OK

git diff --check
# passed
```

## 수동 CLI 확인

Codex 작업 셸에서는 Neo4j 비밀번호 환경변수가 설정되어 있지 않아 다음 명령은 read packet 단계에서 `neo4j_config_missing`으로 닫혔다.

```powershell
python main.py vessel-r-traverse "송련 Core의 그래프 기억 구조에서 source summary와 token layer summary가 어떻게 이어지는지 계층적으로 탐색해줘" --database neo4j --llm-mode fake --format text
```

다만 새 출력 필드(`terminal_material_seen_count`, `min_terminal_material_count`, `early_stop_guard_trigger_count`)는 renderer에 노출되는 것을 확인했다.

## 남은 범위

- live Qwen `vessel-r-traverse` 재실행으로 실제 조기 종료 개선을 확인해야 한다.
- 아직 R route를 node_1 field loop에 연결하지 않았다.
- 아직 R 결과를 node_0 memory packet이나 node_3 final answer에 자동 공급하지 않았다.
