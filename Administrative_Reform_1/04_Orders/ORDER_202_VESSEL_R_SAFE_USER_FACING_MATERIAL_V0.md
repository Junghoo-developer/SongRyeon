# ORDER_202 Vessel R Safe User-Facing Material v0

## 목표

Vessel R live route가 node_3에게 graph memory material을 전달할 때, 내부 `graph:...` node ID가 최종 사용자 답변에 노출되지 않도록 node_3 LLM용 payload를 안전화한다.

## 배경

ORDER_200과 ORDER_201 이후 Vessel R live route는 실험 gate 아래에서 R 탐색을 실행하고, node_0 return packet을 거쳐 node_3에게 Vessel R graph material을 전달할 수 있다.

하지만 live 테스트에서 node_3 최종 답변이 내부 graph node ID를 일부 노출했고, node_4가 `CODE_STATUS:vessel_r_material_claim_mismatch` / `vessel_r_graph_node_id_leak_count`로 반려했다.

이는 R 탐색 실패가 아니라, 감사용 내부 ID와 사용자-facing 설명 재료의 경계가 부족한 문제다.

## 구현 범위

1. node_3 LLM용 Vessel R material payload에서 내부 graph node ID를 제거하거나 안전한 라벨로 대체한다.
2. `material_label`, `display_name`, `summary_text` 등 LLM이 볼 수 있는 문자열에 `graph:...`가 섞이면 redaction한다.
3. DataStore/brief 내부 감사용 `source_data_ids`, `selected_graph_node_ids`, `inspected_graph_node_ids`는 유지한다.
4. node_4의 graph ID leak guard는 약화하지 않는다.
5. 테스트로 다음을 보장한다.
   - 내부 장부에는 graph ID가 남는다.
   - node_3 LLM payload에는 raw `graph:` ID가 보이지 않는다.
   - node_4는 최종 답변에 graph ID가 나오면 계속 반려한다.

## 금지

- R route 의미 변경 금지
- R traversal depth/예산 변경 금지
- Neo4j schema/데이터 변경 금지
- node_4 guard 약화 금지
- code가 R material의 의미 요약을 새로 작성하는 것 금지

## 검증

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_193_r_result_to_node3_vessel_material.py
python -m pytest tests/test_order_200_vessel_r_live_gated_integration.py tests/test_order_201_r2_granularity_and_vessel_r_display.py
python main.py smoke-test
```

## 완료 기준

- Vessel R material의 내부 ID는 감사 장부에 유지된다.
- node_3 LLM payload에는 raw graph node ID가 없다.
- node_4 graph ID leak guard가 유지된다.
- compileall / pytest / smoke-test가 통과한다.
