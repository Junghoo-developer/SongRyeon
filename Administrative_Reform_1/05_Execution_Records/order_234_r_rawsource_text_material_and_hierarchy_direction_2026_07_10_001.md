# ORDER 234 실행 기록: R RawSource text material and hierarchy direction

## 상태

- Date: 2026-07-10
- Implementation: completed
- Deterministic verification: passed
- Neo4j verification: passed
- Qwen end-to-end recheck after final guard: passed after ORDER 235

## 원인

ORDER 233 live에서 RawSource 노드까지 도달했지만 R3는 `low_summary / insufficient / deeper`를 반환했다.

감사 결과:

- RawSource에는 본문 대신 `source_text:*` 좌표가 있었다.
- 실제 원문 3,722자는 별도 GraphMemorySource record에 있었다.
- 기존 R3 selected record에는 원문이 없었다.
- RawSource를 요약한 source-leaf summary가 RawSource의 lower child로 잘못 노출됐다.
- `raw_original_material_seen_count`는 실제 text 열람이 아니라 RawSource 노드 선택을 셌다.

## 변경

- RawSource의 `source_text:*` 절대 좌표를 정확히 조회한다.
- source text ID, 본문, 글자 수, path, 생성 주체, info class를 packet에 보존한다.
- 원문 본문은 R1/R2 후보 카드에 노출하지 않고 선택된 RawSource의 R3 재료로만 노출한다.
- RawSource가 자기 source-leaf summary로 되돌아가는 역방향 child를 제거했다.
- 다음 count를 분리했다.
  - `raw_original_node_selected_count`
  - `raw_original_text_read_count`
  - 기존 `raw_original_material_seen_count`는 호환용 legacy node count로 표시한다.
- `child_count=0 + recommended_next_action=deeper`를 구조 모순으로 검증한다.
- 원문이 공급된 RawSource를 `low_summary`로 쓰면 구조 모순으로 검증한다.
- 두 구조 모순은 기존 R3 schema repair 1회 경로를 사용한다.

## 실제 Neo4j 확인

- read_status: passed
- entry candidates: 155
- summary candidates: 100
- source text targets: 149
- source text resolved: 149
- source text missing: 0
- 감사 RawSource text status: available
- 감사 RawSource text chars: 3,722
- 감사 RawSource text data ID: `source_text:internal_document:7d6d7bace1cf9012`
- 감사 RawSource lower child IDs: 0

packet 전체 JSON은 약 1,633,183자이며 그중 원문 text는 약 406,569자다. 원문은 R1/R2 LLM 입력 후보 카드에는 복사되지 않는다.

## 검증

```powershell
python -m compileall songryeon_core main.py
```

통과.

```powershell
python -m pytest tests/test_order_175_vessel_backed_r_read_packet.py tests/test_order_183_r_vessel_hierarchical_child_surface.py tests/test_order_186_r_vessel_exact_child_expansion.py tests/test_order_187_r_vessel_summary_layer_before_raw.py tests/test_order_188_r_vessel_raw_original_cap.py tests/test_order_190_r_vessel_token_summary_deeper_child_expansion.py tests/test_order_195_r_vessel_activity_ledger.py tests/test_order_214_r3_schema_repair_once.py tests/test_order_216_r_loop_step_memory.py tests/test_order_221_r_child_summary_layer_visibility.py tests/test_order_228_r_continuation_work_order.py tests/test_order_233_r_source_leaf_exact_raw_resolution.py tests/test_order_234_r_rawsource_text_material_and_hierarchy_direction.py -q
```

결과: `33 passed`.

```powershell
python main.py quick-smoke
```

결과: `QUICK_SMOKE_OK`.

`git diff --check` 통과.

## Qwen live 기록

원문 공급과 역방향 child 제거 후 첫 live는 RawSource까지 6단계로 도달했다.

- RawSource node selected: 1
- raw original text read: 1
- legacy node count: 1
- source-text 및 Neo4j 오류: 없음

이 실행에서 Qwen은 아직 `low_summary / deeper`를 반환했다. 이후 해당 구조 모순 validator를 추가했다.

최종 guard 적용 후 재실행:

1. 첫 R2에서 `none_selected`, step 0 종료
2. 첫 R2에서 `none_selected`, step 0 종료
3. R2는 TimeAxis를 선택했으나 step 2에서 Ollama runner가 HTTP 500으로 종료

따라서 최종 guard를 거친 Qwen end-to-end 완주 결과는 아직 미확인이다. 구조 경계는 deterministic tests로 검증했다.

## 남은 위험

- R2 첫 단계가 유일한 TimeAxis 후보를 `none_selected`로 닫을 수 있다.
- 연속 Qwen 실행 중 Ollama runner가 resource/internal error로 중단될 수 있다.
- source text를 packet에 미리 보존하므로 그래프 규모가 커지면 lazy exact fetch 전환을 검토해야 한다.

## ORDER 235 이후 최종 Qwen 완주

R2 일반형 entry-selection 계약을 적용하고 Ollama runner를 정상 해제 후 다시 실행했다.

- traverse_status: completed
- step_count: 6
- final_graph_node_id: `graph:raw_source:internal_document:a825aad2a17dc819`
- final_sufficiency_status: sufficient
- final_continuation_status: stop_sufficient
- r_loop_task_status: sufficient
- RawSource node selected: 1
- raw original text read: 1
- raw original cap reached: false

최종 R3는 실제 RawSource 원문에서 `sufficient / stop`을 반환했다.
