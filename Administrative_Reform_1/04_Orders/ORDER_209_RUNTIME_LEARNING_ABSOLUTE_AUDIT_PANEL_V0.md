# ORDER_209_RUNTIME_LEARNING_ABSOLUTE_AUDIT_PANEL_V0

## 상태

구현 완료.

## 배경

최근 live 테스트에서 사용자는 긴 runtime 출력 안에서 다음 절대정보를 직접 확인하기 어려웠다.

1. 이번 턴이 L로 갔는지 R로 갔는지.
2. R handoff는 준비되어 있었지만 실제 R route가 실행됐는지.
3. 이전 턴 최근 기억 selector가 후보를 골랐는지.
4. 선택된 최근 기억 context가 node_3 brief까지 갔는지.
5. 이전 L loop의 read_doc / activity ledger 근거가 다음 턴 답변 재료로 들어갔는지.
6. node_4가 몇 개 claim을 검사했고, unsupported/contradiction count가 얼마인지.

기존 terminal runtime view는 많은 절대정보를 이미 표시하지만, 학습자가 먼저 봐야 할 핵심 count가 여러 구역에 흩어져 있다.
따라서 새 기능을 열기 전에, 사람이 문제를 직접 읽고 판단할 수 있는 학습용 절대정보 감사판을 추가한다.

## 목표

`render_runtime_view()` 상단에 학습용 절대정보 감사판을 추가한다.

감사판은 다음 정보를 한곳에 모은다.

1. route sequence, final route, route path step count.
2. L run count, same-turn L reroute blocked count.
3. R handoff status, R entry node count, R vessel ledger count.
4. memory relevance selector status/candidate/selected count.
5. selected recent memory copied/missing count와 node_3 brief selected context count.
6. L activity ledger count, read_doc record count, node_0 material packet count, node_3 actual/supplied document count.
7. node_3 Vessel R material status/item count.
8. node_4 gate status, checked/unsupported/contradiction count, recent memory guard status.

## 원칙

1. code는 의미 판단을 하지 않는다.
2. 감사판은 "좋다/나쁘다"를 말하지 않고 절대 count/status만 표시한다.
3. 모든 절대정보를 전부 펼치지 않는다.
4. 긴 trace 원문, 전체 source_data_ids, LLM raw text 전문은 생략한다.
5. 생략 사실은 감사판에 명시한다.
6. 기존 상세 runtime 출력은 유지한다.

## 완료 조건

1. `python -m compileall songryeon_core/runtime/terminal_view.py`
2. `python -m pytest tests/test_order_209_learning_absolute_audit_panel.py`
3. `python -m pytest tests/test_order_206_release_friendly_fake_turn.py tests/test_order_209_learning_absolute_audit_panel.py`

## 금지

1. R/L routing 정책을 이번 발주에서 바꾸지 않는다.
2. node_3 prompt를 더 세게 훈육하지 않는다.
3. node_4 guard를 이번 발주에서 새로 확장하지 않는다.
4. 이전 턴 L read_doc 재공급 로직을 이번 발주에서 구현하지 않는다.
5. trace/data 원문을 무제한 terminal에 출력하지 않는다.
