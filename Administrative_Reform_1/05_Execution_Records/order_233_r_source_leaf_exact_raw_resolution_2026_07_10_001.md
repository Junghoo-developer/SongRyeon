# ORDER 233 실행 기록: R source-leaf exact RawSource resolution

## 상태

- Date: 2026-07-10
- Status: implemented
- Scope: Vessel R read packet / source-leaf summary to RawSource coordinate resolution

## 감사 기준선

ORDER 232 live export의 5단계 source-leaf 요약은 다음 RawSource 좌표를 보존하고 있었다.

- summary: `graph:summary:source_leaf:03bc386f0d35aa36:night_changed_sources_2026_07_02T14_02_36_242082`
- raw target: `graph:raw_source:internal_document:a825aad2a17dc819`

Neo4j 직접 read-only 조회에서 RawSource 노드와 `SUMMARY_OF` 관계가 확인됐다. 그러나 당시 read packet은 entry 후보 100개 안에 해당 RawSource를 싣지 못했고, source-leaf child resolver는 packet에 없는 ID를 조용히 제외했다.

## 변경

- 보이는 active source-leaf 요약에서 `graph:raw_source:*` 정확한 좌표만 수집한다.
- broad entry 후보 제한 밖에 있어도 같은 Neo4j 읽기 결과에 존재하는 정확한 RawSource 레코드를 packet에 추가한다.
- target/resolved/appended/missing 좌표를 read packet 절대정보로 기록한다.
- 후보 ID가 없으면 다른 원본을 고르지 않고 missing 목록에 남긴다.
- R1/R2/R3 prompt, 의미 판단, 원본 최대 5회 정책은 변경하지 않았다.

## 검증

```powershell
python -m compileall songryeon_core main.py
```

통과.

```powershell
python -m pytest tests/test_order_233_r_source_leaf_exact_raw_resolution.py -q
```

결과: `2 passed`.

```powershell
python -m pytest tests/test_order_175_vessel_backed_r_read_packet.py tests/test_order_183_r_vessel_hierarchical_child_surface.py tests/test_order_186_r_vessel_exact_child_expansion.py tests/test_order_187_r_vessel_summary_layer_before_raw.py tests/test_order_188_r_vessel_raw_original_cap.py tests/test_order_190_r_vessel_token_summary_deeper_child_expansion.py tests/test_order_216_r_loop_step_memory.py tests/test_order_221_r_child_summary_layer_visibility.py tests/test_order_228_r_continuation_work_order.py tests/test_order_233_r_source_leaf_exact_raw_resolution.py -q
```

결과: `25 passed`.

```powershell
python main.py quick-smoke
```

결과: `QUICK_SMOKE_OK`.

## 실제 Vessel 확인

Neo4j read packet을 실제로 다시 만들었다.

- read_status: `passed`
- entry candidates: 155
- summary candidates: 100
- source-leaf RawSource targets: 68
- resolved: 68
- appended outside prior packet: 55
- missing: 0
- 감사 대상 RawSource resolved: true

## Qwen live 확인

ORDER 090 문서의 계층을 RawSource까지 내려가도록 Vessel R traverse를 실행했다.

- traverse_status: `completed`
- step_count: 6
- final_graph_node_id: `graph:raw_source:internal_document:a825aad2a17dc819`
- raw_original_material_seen_count: 1
- raw_original_read_cap_reached: false
- driver/schema failure: 없음

실제 경로는 다음과 같았다.

1. TimeAxis
2. SourceIngestTimeBundle
3. internal_document SourceKindBundle
4. token_budget_bundle_summary
5. source_leaf_summary
6. RawSource

## 남은 위험

원본까지 도달한 뒤에도 R3가 `insufficient/deeper`를 반환해 최종 상태는 `stop_budget_exhausted/partial`이었다. source-leaf에서 RawSource로 가는 연결은 복구됐지만, 원본 노드에서 더 내려갈 수 없는 구조와 R3의 `deeper` 요청을 어떻게 정직하게 닫을지는 별도 감사 대상이다.
