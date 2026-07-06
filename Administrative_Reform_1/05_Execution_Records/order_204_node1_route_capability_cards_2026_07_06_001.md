# ORDER_204 Node1 Route Capability Cards 실행 기록

## 작업 범위

- 발주서 추가: `ORDER_204_NODE1_ROUTE_CAPABILITY_CARDS_FOR_L_R_SELECTION_V0.md`
- node_1 LLM router 입력에 `route_capability_cards`와 `route_selection_policy` 추가
- node_1 router prompt에 L/R/2의 근거 표면 비교 규칙 추가
- R route 설명을 "실험용 skeleton" 중심 표현에서 Vessel/Neo4j graph-memory traversal 중심 표현으로 정리
- node_2 answer-basis validator의 검증용 placeholder source ID 누수 구멍 수정

## 핵심 변경

node_1은 이제 route 선택 전에 다음 카드들을 입력으로 받는다.

- `L`: 문서, 코드, artifact, 아직 읽지 않은 project source evidence를 찾거나 읽는 길
- `R`: 명시적으로 허용된 경우에만, 이미 Vessel/Neo4j graph memory에 적재된 CoreEgo/time-axis/source-bundle/summary-layer 구조를 탐색하는 길
- `2`: 이미 공급된 memory/context만으로 답할 수 있을 때 바로 node_2/node_3 보고 경로로 가는 길

코드는 사용자의 질문이 어떤 route에 맞는지 의미 판단하지 않는다. `route_selection_policy.code_semantic_routing_status=not_run`으로 두고, LLM node_1이 `route_reason`에서 근거 표면 비교를 설명하게 했다.

## 같이 고친 작은 live-blocker

live qwen 테스트 중 node_2 answer-basis가 `Node2EvidenceRole.source_data_id must exist in frame.source_data_ids`로 `structure_failed`가 났다.

원인은 `_validate_answer_basis_payload()`가 검증용 `validation_data`를 허용 source 목록에 넣고 있어서, LLM payload 검증은 통과하지만 실제 frame 검증에서 실패할 수 있는 구멍이었다.

수정:

- 검증 frame의 `source_data_ids`에서 `validation_data` 제거
- `validation_data`를 evidence role로 쓰면 fallback으로 닫히는 회귀 테스트 추가

이 수정은 의미 판단 fallback을 만들지 않고, 기존 `CODE:FALLBACK + mixed_or_uncertain + schema_failed` 경로를 정상 작동하게 한 것이다.

## 검증

- `python -m compileall songryeon_core main.py`: 통과
- `python -m pytest tests/test_order_204_node1_route_capability_cards.py -q`: 3 passed
- `python -m pytest tests/test_order_121_answer_basis_and_l3_attitude.py tests/test_order_204_node1_route_capability_cards.py -q`: 8 passed
- `python -m pytest tests/test_order_145_r_loop_pre_live_route_baseline.py tests/test_order_146_r_route_experimental_gate.py tests/test_order_147_r_result_to_node3_brief.py -q`: 17 passed
- `python -m pytest tests/test_order_200_vessel_r_live_gated_integration.py tests/test_order_201_r2_granularity_and_vessel_r_display.py tests/test_order_204_node1_route_capability_cards.py -q`: 9 passed
- `python -m pytest`: 316 passed in 808.99s
- `python main.py smoke-test`: `SMOKE_TEST_OK`
- `git diff --check`: 통과

## Live qwen 확인

명령:

```powershell
python main.py qwen-turn "송련 Core의 그래프 기억 구조를 설명해줘. 문서 검색보다 그래프 기억 탐색이 적합한지 판단해서 답해줘." --enable-vessel-r-route --database neo4j --timeout 180 --pretty
```

결과:

- 상태: `ok`
- node_1 최초 route: `R`
- route_source: `LLM:qwen3:14b`
- policy_flag: `enable_r_route_experimental`
- route path: `1:route=R_vessel_experimental -> 0:vessel_r_read_packet -> 0:vessel_r_start_handoff -> R:Vessel_R1_R2_R3_traverse -> 0:vessel_r_return_packet -> 1:route=2 -> 0:final_trace_for_2`
- `R_vessel_ledgers=1`
- node_4 gatekeeper: pass

단, 이 Codex shell 환경에는 Neo4j password env가 설정되어 있지 않아 Vessel read material은 `failed`로 닫혔다. 중요한 확인값은 node_1이 `--enable-vessel-r-route` 상태에서 L이 아니라 R을 LLM 판단으로 선택했다는 점이다.

## 남은 판단

ORDER_204는 "R route를 강제로 타게 하는 기능"이 아니라 "node_1이 L/R 차이를 이해할 수 있게 설명 표면을 정돈하는 작업"이다.

이제 기능 확장 속도를 줄이고, 인간 중심 학습 루프로 전환할 조건이 상당히 충족되었다.

권장 다음 상태:

- R/L 자동 선택 live 테스트를 몇 개 더 사람이 읽으며 확인
- 바로 새 기능을 크게 열지 않기
- AGENTS/개발 루틴에 `Human Learning First` 규칙 추가
- 코드 청소와 학습 주석, 시스템 설명 훈련을 우선순위로 올리기
