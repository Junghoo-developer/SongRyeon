# ORDER 176: Vessel R One-Step Traversal v0

## 1. Goal

ORDER_175에서 만든 `RLoopVesselReadPacketFrame`을 R루프가 실제로 한 번 읽고, LLM이 후보 하나를 선택한 뒤, code가 그 선택을 검증하는 최소 R 탐색 MVP를 만든다.

이번 발주는 full R loop가 아니다.
목표는 Neo4j Vessel에 저장된 entry/summary 후보를 R1/R2/R3가 한 단계만 다뤄보고, 선택과 검사 결과를 trace/DataStore에 남기는 것이다.

## 2. Required Behavior

- 새 CLI `vessel-r-one-step`을 추가한다.
- 실행 흐름은 다음 순서로 제한한다.
  - `vessel-r-read-packet`과 같은 read-only packet 생성
  - R1: graph search goal / desired granularity 판단
  - code: one-step budget frame 생성
  - R2: packet 안의 `available_graph_node_ids` 중 하나 선택
  - code: R2 선택 ID가 packet 안에 있는지 검증
  - R3: 선택된 candidate record를 보고 sufficiency / granularity / branch 판단
  - code: continuation / return summary / one-step result frame 기록
- R2가 packet 밖 ID를 고르면 schema failure로 닫는다.
- R3가 child node id를 invent해도 code는 사용하지 않는다.
  - child 좌표는 packet 안의 `source_graph_node_ids` / `target_graph_node_id`만 사용한다.
- adapter가 없으면 선택 fallback을 만들지 않고 실패 frame으로 닫는다.
- 기본 live qwen-chat route=R은 열지 않는다.

## 3. Metainfo Boundary

- R1/R2/R3의 goal/selection/inspection reason은 LLM 의미 판단이므로 `info_class=mixed`, `semantic_judgement_status=ran`으로 기록한다.
- code가 만든 budget/continuation/return summary/result frame은 구조화된 절대정보이므로 `info_class=absolute`, `semantic_judgement_status=not_run`으로 기록한다.
- code는 candidate relevance, sufficiency meaning, branch meaning을 대신 판단하지 않는다.
- code는 ID 존재 여부, 예산, packet 내부 좌표 복사만 맡는다.

## 4. Non-goals

- R route를 기본 live route로 열지 않는다.
- multi-step R traversal을 실제 Vessel DB에 연결하지 않는다.
- R 결과를 node_3 최종 답변에 자동 주입하지 않는다.
- semantic axis를 만들지 않는다.
- Neo4j에 새 노드/관계를 쓰지 않는다.
- summary 생성/수정/무효화를 하지 않는다.

## 5. Test Plan

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_176_vessel_r_one_step_traversal.py -q
python main.py fast-test --profile graph
git diff --check
```

수동 확인:

```powershell
python main.py vessel-r-one-step "송련 Core의 그래프 기억 구조를 한 단계만 탐색해줘" --database neo4j --llm-mode fake --format text
```
