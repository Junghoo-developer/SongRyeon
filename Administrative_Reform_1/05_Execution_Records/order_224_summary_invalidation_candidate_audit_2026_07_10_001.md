# ORDER 224 실행 기록: Summary Invalidation Candidate Audit v0

## 구현 일시

- 2026-07-10

## 구현 요약

Neo4j Vessel 안의 source version lineage와 summary graph node를 read-only로 읽어서 source 변경 때문에 무효화 후보가 되는 summary를 계산하는 감사 기능을 추가했다.

추가 명령:

```powershell
python main.py vessel-summary-invalidation-candidate-audit --database neo4j --format text
```

감사 기준:

- `source_version_lineage_frame.lineage_status == content_changed`
- 해당 lineage에 `superseded_source_graph_node_ids`가 있음
- summary payload의 `source_graph_node_ids`가 superseded source id를 포함함
- 이미 `validity_status=invalidated_by_source_change`인 summary는 새 후보가 아니라 already invalidated로 분리함

## 변경 파일

- `Administrative_Reform_1/04_Orders/ORDER_224_SUMMARY_INVALIDATION_CANDIDATE_AUDIT_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`
- `main.py`
- `songryeon_core/core/graph_vessel_summary_invalidation_candidate_audit.py`
- `songryeon_core/runtime/graph_vessel_summary_invalidation_candidate_audit.py`
- `tests/test_order_224_summary_invalidation_candidate_audit.py`

## 검증

- `python -m compileall songryeon_core main.py`: 통과
- `python -m pytest tests/test_order_224_summary_invalidation_candidate_audit.py -q`: 4 passed
- `python main.py quick-smoke`: `QUICK_SMOKE_OK`
- `git diff --check`: 통과

## 하지 않은 것

- Neo4j summary node 수정
- `validity_status` 실제 변경
- summary 삭제
- legacy summary 자동 무효화
- source lineage 재계산
- LLM 호출
- R/L loop 변경

## 다음 후보

실제 Neo4j에서 ORDER 224 명령을 실행해 후보 수를 확인한 뒤, 후보가 타당하면 ORDER 225에서 별도 apply 명령을 만들 수 있다. ORDER 225도 삭제가 아니라 `validity_status=invalidated_by_source_change` 적용과 적용 장부 기록으로 제한해야 한다.

