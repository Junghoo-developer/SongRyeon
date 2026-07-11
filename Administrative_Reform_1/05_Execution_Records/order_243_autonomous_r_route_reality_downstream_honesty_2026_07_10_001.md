# ORDER 243 실행 기록

- 날짜: 2026-07-10
- 결과: 구현 및 강제 옵션 없는 live 검증 통과
- 발주서: `ORDER_243_AUTONOMOUS_R_ROUTE_REALITY_AND_DOWNSTREAM_HONESTY_V0.md`

## 원인

- node_1 capability 설명이 R의 최신 능력을 반영하지 않아, 이미 적재된 RawSource 원문도 L만 읽을 수 있다고 오판했다.
- explicit artifact parser가 `ORDER_090`은 인식했지만 사람이 쓴 `ORDER 090`은 인식하지 못했다.
- L3는 explicit artifact resolver 결과를 목표 대조에 사용하지 않아, 다른 문서를 읽고도 특정 문서 요청이 없었다고 처리할 수 있었다.
- node_3 accidental grounding 제거는 본문 첫 줄만 검사했고, node_4는 두 번째 grounding heading을 세지 않았다.

## 변경

- node_1 R capability에 이미 적재된 RawSource 원문까지 내려갈 수 있음을 명시했다.
- L은 미적재 source와 graph 관측보다 최신인 현재 disk 상태를 확인하는 route로 경계를 좁혔다.
- `ORDER 090`을 visible raw text로 보존하면서 resolver 입력만 `ORDER_090`으로 정규화했다.
- L3가 `node_output:explicit_artifact_reference_frame`의 selected document ID를 실제 read 결과와 대조하게 했다.
- 명시 문서를 읽지 않은 L 결과는 LLM이 achieved라고 써도 code guard가 partial/failed로 낮춘다.
- node_3는 본문 위치와 무관하게 accidental grounding block을 제거한다.
- node_4는 grounding heading이 정확히 1개가 아니면 code count guard 위반으로 기록한다.

## 자동 검증

- `python -m compileall songryeon_core main.py`: 통과
- `python -m pytest`: `394 passed, 5 deselected`
- `python main.py smoke-test`: `SMOKE_TEST_OK`
- `git diff --check`: 통과
- ORDER 243 좁은 회귀 및 관련 회귀: `21 passed`

## 강제 옵션 없는 live 검증

- 질문: Vessel R 그래프 기억으로 ORDER 090 L Loop Budget Plan을 RawSource 원문까지 확인해 설명하도록 요청
- 옵션: `--enable-r-route-experimental --enable-vessel-r-route`, force flag 없음
- route sequence: `R -> 2`
- node_1 route source: `LLM:qwen3:14b`
- R path step count: 7
- R selected/inspected node count: 6
- final RawSource: `graph:raw_source:internal_document:a825aad2a17dc819`
- final source path: `Administrative_Reform_1/04_Orders/ORDER_090_L_LOOP_BUDGET_PLAN_V0.md`
- raw original text: available, 3,722 chars
- R task: `sufficient / stop_sufficient / within_budget`
- node_3 Vessel material: 6 items, source summaries 2, raw originals 1
- node_4: `pass`, unsupported 0, contradictions 0
- export: `.songryeon_core_cache/r_autonomous_integration_order_243_20260710_001`

## 경계

- code가 질문 키워드로 R을 강제하지 않았다.
- R/L 의미 선택은 node_1 LLM 판단으로 유지했다.
- Neo4j 내용, R/L 예산, same-turn reroute 정책은 변경하지 않았다.
