# ORDER_202 Vessel R Safe User-Facing Material 실행 기록

## 실행 일시

2026-07-06

## 문제

Vessel R live route 테스트에서 R 탐색 자체는 node_3까지 material을 전달했지만, node_3 최종 답변에 내부 `graph:...` node ID가 노출되었다.

node_4는 이를 `CODE_STATUS:vessel_r_material_claim_mismatch`와 `vessel_r_graph_node_id_leak_count`로 반려했다.

## 판단

이 문제는 R 탐색 깊이나 Neo4j 연결 문제가 아니라, 내부 감사용 graph ID와 사용자-facing 답변 재료의 경계 문제다.

내부 장부에는 graph ID가 남아야 하지만, node_3 LLM payload에는 raw graph ID를 직접 보여줄 필요가 없다.

## 수정

- `node_2_handoff.py`에 Vessel R LLM payload 전용 graph ID redaction을 추가했다.
- `display_name`이 내부 graph ID뿐이면 `material_label`로 대체한다.
- `summary_text` 안에 섞인 `graph:...` 문자열은 `[internal graph id omitted]`로 바꿔 node_3 LLM에게 전달한다.
- DataStore/brief 내부 감사용 source ids는 유지했다.
- node_4 graph ID leak guard는 유지했다.

## 검증 결과

```powershell
python -m compileall songryeon_core main.py
# 통과

python -m pytest tests/test_order_193_r_result_to_node3_vessel_material.py
# 5 passed

python -m pytest tests/test_order_200_vessel_r_live_gated_integration.py tests/test_order_201_r2_granularity_and_vessel_r_display.py
# 5 passed

python -m pytest tests/test_order_198_r_vessel_return_packet.py tests/test_order_199_r_vessel_answer_demo_route.py
# 9 passed

python main.py smoke-test
# SMOKE_TEST_OK
```
