# ORDER 226 실행 기록: R2 Official Selection Table

## 일시

- 2026-07-10

## 목적

R2가 긴 candidate payload 안에서 선택 가능한 ref를 놓치지 않도록, R2 input payload 최상단에 `official_selection_table`을 추가했다.

## 구현 요약

- `songryeon_core/loops/r_loop_vessel_one_step.py`
  - `_r2_input_payload()`가 `official_selection_table`을 첫 번째 key로 넣는다.
  - `_r2_official_selection_table()`을 추가했다.
  - schema repair의 `r2_copy_repair_table`도 official table을 보존한다.
- `songryeon_core/prompts/r2_vessel_node_selector_v0.md`
  - R2가 `official_selection_table`을 우선 사용하도록 prompt 경계를 갱신했다.
- `tests/test_order_226_r2_official_selection_table.py`
  - R2 payload 첫 key가 official table인지 검증한다.
  - official table만 보고도 R2 선택이 통과하는지 검증한다.
  - schema repair에서도 official table과 valid refs가 보존되는지 검증한다.

## 정책 경계

- code는 의미적으로 어떤 후보가 맞는지 선택하지 않는다.
- code는 공식 번호표를 만들고 validator로 표 밖 선택을 차단한다.
- R3/continuation/Neo4j 구조는 변경하지 않았다.

## 검증

- `python -m compileall songryeon_core main.py`: 통과
- `python -m pytest tests/test_order_226_r2_official_selection_table.py -q`: 2 passed
- `python -m pytest tests/test_order_217_r2_candidate_card_enrichment.py tests/test_order_213_r2_schema_repair_once.py -q`: 5 passed
- `python -m pytest tests/test_order_225_llm_input_payload_audit_snapshot.py tests/test_order_226_r2_official_selection_table.py -q`: 4 passed
- `python main.py quick-smoke`: `QUICK_SMOKE_OK`
- `git diff --check`: 통과

## Live 확인

강제 Vessel R live 검증을 실행했다.

```powershell
python main.py qwen-turn "문서 검색이 아니라 Vessel R 그래프 기억을 강제로 사용해서, 송련 Core의 그래프 기억이 CoreEgo에서 시간축, 소스 묶음, 요약 계층, 원본까지 어떤 순서로 내려가는지 설명해줘. 가능하면 R루프가 실제로 고른 그래프 재료와 한계를 구분해서 말해줘." --force-vessel-r-route --enable-vessel-r-route --database neo4j --timeout 180 --pretty --export .songryeon_core_cache\r2_official_table_after_order_226_20260710
```

확인 결과:

- R2 step 1은 official table을 받고 `graph:axis:time`을 선택했다.
- R2 step 2는 schema repair 후 `graph:source_ingest_time_bundle:night_changed_sources_2026_07_02T14_02_36_242082:source_manifest`까지 내려갔다.
- 즉 ORDER 225 감사 때 보였던 “후보 ref가 없어서 못 고른다” 상태에서 한 단계 진전했다.
- 최종 R task는 아직 `partial / stop_no_actionable_path`이고 node_4는 `vessel_r_material_claim_mismatch`로 최종 답변을 막았다.
- 따라서 다음 병목은 R2 공식 선택표 자체보다, 더 아래 계층 continuation/후보 표시 또는 node_3의 partial R 태도 처리 쪽이다.
