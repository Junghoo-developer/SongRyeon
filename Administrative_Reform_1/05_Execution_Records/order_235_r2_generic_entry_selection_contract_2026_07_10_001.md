# ORDER 235 실행 기록: R2 generic entry selection contract

## 상태

- Date: 2026-07-10
- Status: implemented
- Scope: R2 first-step work order / schema repair / future multi-axis compatibility

## 원인

ORDER 234 최종 guard 재검증 중 R2가 첫 단계 유일 후보를 두 번 `none_selected`로 닫았다. 기존 work order는 continuation 단계에서만 후보가 있으면 선택을 요구했고, 첫 단계는 항상 `none_selected_allowed=true`였다.

## 변경

- 첫 단계 `candidate_count > 0`이면 `none_selected_allowed=false`로 기록한다.
- 첫 단계 후보가 0개일 때만 `none_selected`를 허용한다.
- TimeAxis 이름이나 후보 수 1개를 조건으로 사용하지 않는다.
- 후보가 여러 개이면 R2가 R1 목표에 따라 official selection table 안에서 하나를 고른다.
- 잘못된 first-step `none_selected`는 기존 R2 schema repair 1회 경로로 복구한다.

## 미래 확장 경계

현재 Vessel에는 TimeAxis만 직접 entry로 보이므로 live에서 TimeAxis가 선택됐다. 향후 MeaningAxis나 WorkAxis가 추가되면 code는 축 이름을 판단하지 않고 모든 공식 entry 후보를 제공한다. 어떤 축을 고를지는 R2의 mixed semantic judgement로 남는다.

## 검증

```powershell
python -m pytest tests/test_order_235_r2_generic_entry_selection_contract.py -q
```

결과: `3 passed`.

```powershell
python -m pytest tests/test_order_213_r2_schema_repair_once.py tests/test_order_226_r2_official_selection_table.py tests/test_order_228_r_continuation_work_order.py tests/test_order_229_r2_repair_safe_granularity_default.py tests/test_order_234_r_rawsource_text_material_and_hierarchy_direction.py tests/test_order_235_r2_generic_entry_selection_contract.py -q
```

결과: `13 passed`.

`python -m compileall songryeon_core main.py`, `python main.py quick-smoke`, `git diff --check` 통과.

## Qwen live

Ollama runner를 정상 해제한 뒤 ORDER 090 질문으로 실제 Vessel R traverse를 실행했다.

- traverse_status: completed
- entry candidates: 155
- summary candidates: 100
- step_count: 6
- final RawSource: `graph:raw_source:internal_document:a825aad2a17dc819`
- final sufficiency: sufficient
- final continuation: stop_sufficient
- R task: sufficient
- RawSource node selected: 1
- raw original text read: 1
- raw original cap reached: false

경로:

1. TimeAxis
2. SourceIngestTimeBundle
3. internal_document SourceKindBundle
4. token-budget summary
5. source-leaf summary
6. RawSource original text

최종 R3는 `sufficient / stop`을 반환했다.
