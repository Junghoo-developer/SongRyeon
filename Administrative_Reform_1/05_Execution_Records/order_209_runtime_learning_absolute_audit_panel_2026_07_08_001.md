# order_209_runtime_learning_absolute_audit_panel_2026_07_08_001

## 작업 범위

ORDER_209 Runtime Learning Absolute Audit Panel을 구현했다.

## 구현 내용

- `songryeon_core/runtime/terminal_view.py`
  - `render_runtime_view()` 상단에 `학습용 절대정보 감사판`을 추가했다.
  - 감사판은 route/L/R/memory/node3/node4 핵심 count와 status만 표시한다.
  - 긴 trace 원문, 전체 source_data_ids, LLM raw text 전문은 생략한다고 명시한다.

- `tests/test_order_209_learning_absolute_audit_panel.py`
  - 핵심 count가 감사판에 표시되는지 검증하는 테스트를 추가했다.
  - 관련 record가 없는 경우에도 `not_recorded` / `final=none` 형태로 정직하게 닫히는지 검증했다.

- `Administrative_Reform_1/04_Orders/ORDER_209_RUNTIME_LEARNING_ABSOLUTE_AUDIT_PANEL_V0.md`
  - 발주서를 추가했다.

- `Administrative_Reform_1/04_Orders/README.md`
  - ORDER_209 등록 및 현재 정식 발주서 범위를 갱신했다.

## 표시하는 절대정보

- route sequence / final route / route path step count
- L run count / same-turn L blocked reroute count
- R handoff status / R entry node count / R vessel ledger count
- recent memory selector candidate/selected count
- selected recent memory copied/missing count
- node_3 selected recent memory context count
- L activity ledger count / read_doc record count
- node_0 document material count / node_3 actual/supplied document count
- node_3 Vessel R material status/item count
- node_4 checked/unsupported/contradiction count / recent memory guard status

## 일부러 생략한 절대정보

- 전체 trace 원문
- 전체 DataStore payload 원문
- 전체 source_data_ids 목록
- LLM raw text 전문
- 긴 문서 원문

이 정보들은 기존 상세 runtime과 DataStore에는 남아 있지만, 학습용 상단 감사판에는 넣지 않았다.
이유는 모든 절대정보가 학습자에게 동등하게 중요한 것은 아니며, 전부 펼치면 route/memory/node3/node4 상태를 읽는 목적이 흐려지기 때문이다.

## 검증

```powershell
python -m compileall songryeon_core\runtime\terminal_view.py
python -m pytest tests\test_order_209_learning_absolute_audit_panel.py -q
python -m pytest tests\test_order_206_release_friendly_fake_turn.py tests\test_order_209_learning_absolute_audit_panel.py -q
python main.py fake-turn "송련이 뭔지 짧게 설명해줘" --pretty
```

결과:

- compileall 통과
- ORDER_209 pytest: 2 passed
- ORDER_206 + ORDER_209 pytest: 5 passed
- fake-turn pretty 출력에서 `학습용 절대정보 감사판` 확인

## 미구현

- node_1 R/L routing 정책 변경 없음
- 이전 턴 L read_doc 재공급 로직 구현 없음
- node_3 prompt 강화 없음
- node_4 question alignment / memory count contradiction guard 추가 없음
- trace/data 원문 전체 출력 없음
