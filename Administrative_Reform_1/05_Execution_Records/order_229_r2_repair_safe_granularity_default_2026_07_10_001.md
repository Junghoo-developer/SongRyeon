# ORDER 229 실행 기록: R2 repair safe granularity default

## 상태

- Date: 2026-07-10
- Status: implemented
- Scope: Vessel R / R2 schema repair enum stability

## 발생한 문제

ORDER 228 구현 후 live Vessel R 강제 테스트에서 R2가 continuation work order를 따라 더 깊은 후보를 선택하는 데는 성공했다.
하지만 repair 모드의 R2가 `expected_information_granularity`에 `child_candidate`를 써서 schema 실패가 발생했다.

이 값은 후보 종류/구조 라벨이지 허용된 정보 농도 enum이 아니다.

## 변경 요약

R2 schema repair payload의 `r2_copy_repair_table`에 `safe_output_defaults.expected_information_granularity`를 추가했다.
기본값은 허용 enum 중 `unknown`이 있으면 `unknown`으로 둔다.

R2 prompt는 repair 모드에서 이 값을 그대로 복사하도록 수정했다.

## 코드 변경

- `songryeon_core/loops/r_loop_vessel_one_step.py`
  - `_safe_r2_repair_granularity_default()` 추가
  - `r2_copy_repair_table.safe_output_defaults.expected_information_granularity` 추가
  - repair output contract를 safe default 복사 방식으로 조정
- `songryeon_core/prompts/r2_vessel_node_selector_v0.md`
  - repair 모드에서 `safe_output_defaults.expected_information_granularity`를 그대로 복사하라고 명시
  - candidate kind / branch role / child structure label을 granularity로 쓰지 말라고 명시
- `tests/test_order_229_r2_repair_safe_granularity_default.py`
  - 첫 R2가 invalid granularity를 내도 repair가 `unknown`으로 통과하는지 검증

## 하지 않은 것

- code가 그래프 후보를 의미적으로 선택하지 않았다.
- 정상 R2 응답의 granularity를 덮어쓰지 않았다.
- R1/R3, Neo4j 구조, node_3 답변 정책은 바꾸지 않았다.

## 검증

```powershell
python -m compileall songryeon_core main.py
```

통과.

```powershell
python -m pytest tests/test_order_229_r2_repair_safe_granularity_default.py -q
```

결과: `1 passed`.

```powershell
python -m pytest tests/test_order_228_r_continuation_work_order.py -q
```

결과: `2 passed`.

```powershell
python -m pytest tests/test_order_226_r2_official_selection_table.py tests/test_order_227_r1_minimum_traversal_budget.py tests/test_order_228_r_continuation_work_order.py tests/test_order_229_r2_repair_safe_granularity_default.py tests/test_order_213_r2_schema_repair_once.py -q
```

결과: `9 passed`.

```powershell
python main.py quick-smoke
```

결과: `QUICK_SMOKE_OK`.

## 남은 확인

동일한 live Vessel R 강제 테스트를 다시 실행하여, 이전의 `R2 expected_information_granularity is invalid` 실패가 사라지는지 확인한다.

## Live 재확인

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
. .\.env.vessel.local.ps1
python main.py qwen-turn "문서 검색이 아니라 Vessel R 그래프 기억을 강제로 사용해서, 송련 Core의 그래프 기억이 CoreEgo에서 시간축, 소스 묶음, 요약 계층, 원본까지 어떤 순서로 내려가는지 설명해줘. 가능하면 R루프가 실제로 고른 그래프 재료와 한계를 구분해서 말해줘." --force-vessel-r-route --enable-vessel-r-route --database neo4j --timeout 180 --pretty --export .songryeon_core_cache\r_safe_granularity_after_order_229_20260710
```

결과:

- runtime status: `ok`
- R route: `force_vessel_r_route`
- R/Vessel material: `status=present`, `items=5`
- R loop task: `partial`
- continuation: `stop_no_actionable_path`
- 이전 실패였던 `R2 expected_information_granularity is invalid`는 재현되지 않았다.
- node_4 gatekeeper는 `needs_revision`을 냈다.
- node_4 반려 이유는 `vessel_r_success_claim_without_sufficient_material:status_present_task_partial`이다.

해석:

ORDER 229의 enum repair 목적은 달성되었다.
다음 병목은 R 탐색이 `partial`일 때 node_3가 이를 충분/성공처럼 말하지 않도록 하는 R partial answer attitude 쪽이다.
