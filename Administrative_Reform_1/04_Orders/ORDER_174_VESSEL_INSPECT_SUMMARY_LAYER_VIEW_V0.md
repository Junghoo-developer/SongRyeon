# ORDER 174: Vessel Inspect Summary Layer View v0

## 1. Goal

Neo4j Vessel에 저장된 심야정부 요약 노드가 실제로 얼마나 생성됐고, 어떤 계층/종류로 쌓였는지 사람이 바로 볼 수 있게 한다.

현재 `vessel-inspect --format text`는 `CoreEgo -> Time Axis -> Time Bundle -> Raw Capsule` 기본 경로만 보여준다.
그 결과 source leaf summary나 token budget bundle summary가 Neo4j에 들어갔어도 화면에서는 보이지 않는다.

## 2. Required Behavior

- `vessel-inspect`가 read-only로 `SummaryGraphNode`를 조회한다.
- 다음 절대정보를 결과 payload와 text renderer에 표시한다.
  - summary node 총수
  - active / invalidated summary 수
  - `data_kind`별 summary 수
  - `summary_depth`별 summary 수
  - sample summary node 목록
- sample에는 다음 필드를 보여준다.
  - summary data id
  - data kind
  - summary depth
  - info class
  - target graph node id / display name
  - summary text preview
- 코드는 새 요약이나 의미 판단을 만들지 않는다.
- Neo4j에 이미 저장된 node property와 `payload_json`만 읽는다.

## 3. Non-goals

- R loop route를 열지 않는다.
- semantic axis를 만들지 않는다.
- 요약 품질을 평가하지 않는다.
- summary를 새로 생성하거나 수정하지 않는다.
- graph DB schema를 파괴적으로 바꾸지 않는다.

## 4. Test Plan

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_163_vessel_inspect_manual_walk.py tests/test_order_174_vessel_inspect_summary_layer_view.py -q
python main.py fast-test --profile graph
git diff --check
```
