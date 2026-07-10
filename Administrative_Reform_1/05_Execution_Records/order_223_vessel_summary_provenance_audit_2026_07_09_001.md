# ORDER 223 실행 기록: Vessel Summary Provenance Audit v0

## 구현 일시

- 2026-07-09

## 구현 요약

Neo4j Vessel에 이미 저장된 summary graph node들이 ORDER 222의 run provenance 필드를 갖고 있는지 read-only로 감사하는 기능을 추가했다.

추가 명령:

```powershell
python main.py vessel-summary-provenance-audit --database neo4j --format text
```

감사 대상 필드:

- `summary_run_id`
- `night_turn_id`
- `night_batch_id`
- `summary_created_at`
- `run_provenance_status`

분류:

- `recorded`: 필수 provenance 필드가 모두 있는 요약
- `legacy`: provenance 필드가 전혀 없는 ORDER 222 이전 요약
- `incomplete`: provenance 필드가 일부만 있는 요약
- `invalid_status`: 허용되지 않은 `run_provenance_status` 값을 가진 요약

## 변경 파일

- `Administrative_Reform_1/04_Orders/ORDER_223_VESSEL_SUMMARY_PROVENANCE_AUDIT_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`
- `main.py`
- `songryeon_core/core/graph_vessel_summary_provenance_audit.py`
- `songryeon_core/runtime/graph_vessel_summary_provenance_audit.py`
- `tests/test_order_223_vessel_summary_provenance_audit.py`

## 검증

- `python -m compileall songryeon_core main.py`: 통과
- `python -m pytest tests/test_order_223_vessel_summary_provenance_audit.py -q`: 4 passed
- `python main.py quick-smoke`: `QUICK_SMOKE_OK`
- `git diff --check`: 통과

## 하지 않은 것

- Neo4j summary node 수정
- legacy summary 자동 backfill
- summary node 삭제
- summary node 무효화
- source 변경 무효화 정책 구현
- R/L loop 변경

## 다음 후보

ORDER 224 후보는 source 변경 시 summary invalidation 정책 MVP다. ORDER 223의 감사 결과에서 legacy/incomplete 현황을 확인한 뒤, 기존 노드를 삭제하지 않고 `invalidated_by_source_change` 같은 상태로 추적하는 방향이 안전하다.

