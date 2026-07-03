# ORDER 176 Execution Record: Vessel R One-Step Traversal

## Summary

ORDER_176을 구현했다.

ORDER_175의 `RLoopVesselReadPacketFrame`을 입력으로 받아 R1/R2/R3가 한 단계만 Vessel 후보를 탐색하는 실험용 R one-step traversal을 추가했다.

## Changed Files

- `songryeon_core/prompts/r1_vessel_goal_setter_v0.md`
- `songryeon_core/prompts/r2_vessel_node_selector_v0.md`
- `songryeon_core/prompts/r3_vessel_inspector_v0.md`
- `songryeon_core/loops/r_loop_vessel_one_step.py`
- `songryeon_core/runtime/r_loop_vessel_one_step.py`
- `main.py`
- `songryeon_core/runtime/fast_test.py`
- `tests/test_order_176_vessel_r_one_step_traversal.py`
- `Administrative_Reform_1/04_Orders/ORDER_176_VESSEL_R_ONE_STEP_TRAVERSAL_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`

## Behavior

- 새 CLI `vessel-r-one-step`을 추가했다.
- 실행 흐름은 다음과 같다.
  - read-only Vessel packet 생성
  - R1 LLM goal/granularity 판단
  - code one-step budget 생성
  - R2 LLM candidate 선택
  - code가 선택 ID가 packet 안에 있는지 검증
  - R3 LLM sufficiency/granularity/branch 판단
  - code continuation/return summary/result frame 기록
- R2가 packet 밖 ID를 고르면 schema failure로 닫는다.
- R3가 child node ID를 invent해도 code는 사용하지 않고 packet 안의 `source_graph_node_ids` / `target_graph_node_id`만 복사한다.
- adapter가 없으면 선택 fallback을 만들지 않고 `adapter_missing` 실패 frame으로 닫는다.

## Metainfo Boundary

- R1/R2/R3의 판단 frame은 `generated_by=LLM:*`, `info_class=mixed`, `semantic_judgement_status=ran`이다.
- budget/continuation/return summary/result frame은 code 생성 절대정보이며 `semantic_judgement_status=not_run`이다.
- code는 후보 관련성, 충분성, branch 의미 판단을 대신하지 않는다.

## Verification

```powershell
python -m compileall songryeon_core main.py
```

통과.

```powershell
python -m pytest tests/test_order_176_vessel_r_one_step_traversal.py -q
```

결과: `6 passed in 0.15s`

```powershell
python main.py fast-test --profile graph
```

결과: `FAST_TEST_OK`, `114 passed in 51.19s`

```powershell
python main.py smoke-test
```

결과: `SMOKE_TEST_OK`

```powershell
git diff --check
```

통과.

## Manual CLI Note

Codex 셸에서 아래 명령을 추가로 시도했다.

```powershell
python main.py vessel-r-one-step "송련 Core의 그래프 기억 구조를 한 단계만 탐색해줘" --llm-mode fake --format text --allow-no-auth
```

이 셸에는 사용자의 Neo4j env가 로드되어 있지 않아 기본 `bolt://localhost:7687`로 연결을 시도했고, 로컬 Neo4j 연결 거부로 `read_packet` 단계에서 실패했다.
이는 ORDER_176 deterministic 테스트 실패가 아니라 수동 CLI 실행 환경 문제다.
사용자 PowerShell에서 `.env.vessel.local.ps1`을 로드한 뒤 `--database neo4j`로 다시 실행하면 실제 Vessel에 대해 확인할 수 있다.

## Non-goals Preserved

- 기본 live `qwen-chat` route=R은 열지 않았다.
- multi-step Vessel R traversal은 열지 않았다.
- R 결과를 node_3 최종 답변에 자동 주입하지 않았다.
- semantic axis를 만들지 않았다.
- Neo4j write는 수행하지 않았다.
