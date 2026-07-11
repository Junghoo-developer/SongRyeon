# ORDER 230 실행 기록: Vessel R negated success guard

## 상태

- Date: 2026-07-10
- Status: implemented
- Scope: node_3 grounding wording / node_4 Vessel R guard

## 발생한 문제

ORDER 229 이후 live Vessel R 강제 테스트에서 이전의 R2 enum schema 실패는 사라졌다.
R 탐색은 5개 재료를 node_3에 넘겼지만, `r_loop_task_status=partial`이었고 node_4는 최종 보고를 반려했다.

반려 원인을 감사한 결과, node_3 본문 자체는 partial 한계를 언급하고 있었다.
하지만 code가 만든 grounding block의 `graph memory 탐색 성공으로 단정하지 않는다`라는 부정문이 node_4 정규식 guard에 의해 성공 주장으로 오탐되었다.

## 변경 요약

- node_3 grounding limit 문구를 `성공으로 단정하지 않는다`에서 `요구 수준에 도달했다고 보지 않는다`로 바꿨다.
- node_4 Vessel R success claim guard가 성공/충분을 부정하는 문장을 성공 주장으로 오탐하지 않게 했다.
- 진짜 성공 과장 문장은 계속 차단되도록 기존 guard를 유지했다.

## 코드 변경

- `songryeon_core/nodes/node_3_reporter.py`
  - partial R/Vessel limit 문구 조정
- `songryeon_core/nodes/node_4_gatekeeper.py`
  - `_claims_vessel_r_success()`를 match 단위 검사로 변경
  - `_vessel_r_success_match_is_negated()` 추가
- `tests/test_order_230_vessel_r_negative_success_guard.py`
  - 부정문 오탐 방지 테스트
  - grounding block 문구 테스트

## 검증

```powershell
python -m compileall songryeon_core main.py
```

통과.

```powershell
python -m pytest tests/test_order_230_vessel_r_negative_success_guard.py -q
```

결과: `2 passed`.

```powershell
python -m pytest tests/test_order_193_r_result_to_node3_vessel_material.py::test_node4_blocks_vessel_r_success_claim_when_material_is_failed -q
```

결과: `1 passed`.

```powershell
python -m pytest tests/test_order_193_r_result_to_node3_vessel_material.py tests/test_order_211_vessel_r_status_name_guard.py tests/test_order_230_vessel_r_negative_success_guard.py -q
```

결과: `9 passed`.

```powershell
python main.py quick-smoke
```

결과: `QUICK_SMOKE_OK`.

## 남은 확인

같은 live Vessel R 강제 테스트를 다시 실행해서 node_4의 오탐 반려가 사라지는지 확인한다.
