# ORDER 222 실행 기록: Night Summary Run Provenance v0

## 구현 일시

- 2026-07-09

## 구현 요약

심야 정부 LLM 요약 frame/node payload에 생성 실행 좌표를 절대정보로 기록하게 했다.

대상:

- `NightSourceLeafSummaryFrame`
- `NightTimeBundleSummaryFrame`
- `NightTokenBudgetBundleSummaryFrame`

추가 필드:

- `summary_run_id`
- `night_turn_id`
- `night_batch_id`
- `summary_created_at`
- `run_provenance_status`

새로 생성되는 요약은 `run_provenance_status=recorded`로 기록한다.
기존 legacy payload는 일괄 무효화하지 않기 위해 `legacy_not_recorded` 상태를 허용한다.

## 변경 파일

- `Administrative_Reform_1/04_Orders/ORDER_222_NIGHT_SUMMARY_RUN_PROVENANCE_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`
- `songryeon_core/core/schema_parts/graph_memory.py`
- `songryeon_core/nodes/night_summarize_time_bundle.py`
- `songryeon_core/nodes/night_summarize_source_leaf.py`
- `songryeon_core/nodes/night_summarize_token_budget_bundle.py`
- `tests/test_order_222_night_summary_run_provenance.py`

## 검증

- `python -m compileall songryeon_core main.py`: 통과
- `python -m pytest tests/test_order_222_night_summary_run_provenance.py -q`: 3 passed
- `python -m pytest tests/test_order_166_night_time_bundle_summary_node.py tests/test_order_168_night_summarize_changed_source_leaves.py tests/test_order_171_night_token_budget_layer_summary.py tests/test_order_222_night_summary_run_provenance.py -q`: 16 passed
- `python main.py quick-smoke`: `QUICK_SMOKE_OK`
- `git diff --check`: 통과

## 하지 않은 것

- 기존 Neo4j payload 일괄 수정
- 기존 요약 일괄 무효화
- 요약 의미 내용 변경
- R/L routing 변경
- LLM에게 run provenance 작성을 맡기는 변경

## 남은 주의점

기존 그래프 DB에 이미 들어간 요약 payload는 새 필드가 없을 수 있다. 이들은 즉시 불량 처리하지 않고, 추후 감사/백필 정책에서 `legacy_not_recorded` 또는 `backfilled_from_trace`로 다룬다.

