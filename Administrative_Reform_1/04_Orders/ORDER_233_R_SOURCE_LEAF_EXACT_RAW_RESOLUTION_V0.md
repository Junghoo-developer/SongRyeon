# ORDER 233: R Source Leaf Exact Raw Resolution v0

## 상태

- Status: implemented
- Date: 2026-07-10
- Scope: Vessel R read packet / source-leaf summary to RawSource coordinate resolution

## 배경

ORDER 232 live 재검증에서 R2는 source-leaf 요약을 선택했고 R3는 더 낮은 정보 농도가 필요하다고 판단했다. R1 예산도 남아 있었지만 `child_count=0`으로 기록되어 `stop_no_actionable_path`로 닫혔다.

감사 결과 다음 절대 사실을 확인했다.

- 선택된 source-leaf 요약에는 정확한 `target_graph_node_id`와 `source_graph_node_ids`가 있었다.
- 해당 RawSource 노드는 Neo4j에 존재했고 요약 노드와 `SUMMARY_OF`로 연결되어 있었다.
- 그러나 제한된 read packet 후보 목록에는 해당 RawSource 레코드가 없었다.
- 기존 child resolver는 packet에 없는 정확한 ID를 조용히 버렸다.

## 목표

- read packet에 보이는 source-leaf 요약이 가리키는 정확한 RawSource 레코드를 packet 후보로 물질화한다.
- 정확한 ID가 Neo4j 읽기 결과에 없으면 누락 좌표를 절대정보 장부에 남긴다.
- R2/R3 의미 판단, 후보 관련성, 예산은 변경하지 않는다.

## 구현 경계

- 입력 좌표는 source-leaf 요약의 `target_graph_node_id`, `source_graph_node_ids`, `source_data_ids`만 사용한다.
- `graph:raw_source:*`인 정확한 ID만 해석한다.
- broad entry 후보 제한 밖에 있더라도 이미 Neo4j에서 읽은 동일 ID 레코드를 추가한다.
- target/resolved/appended/missing ID를 read packet에 기록한다.
- 키워드, 유사도, 최신성, 순서 fallback은 사용하지 않는다.

## 하지 않는 것

- R1/R2/R3 prompt나 의미 판단을 변경하지 않는다.
- 전체 후보 제한을 무작정 늘리지 않는다.
- RawSource를 찾지 못했을 때 다른 원본으로 대체하지 않는다.
- 원본 열람 최대 5회 정책을 변경하지 않는다.
- Neo4j 구조나 심야 요약 계층을 다시 만들지 않는다.

## 완료 조건

- 후보 제한 밖 RawSource도 보이는 source-leaf 요약의 정확한 ID이면 packet에 추가된다.
- 추가된 RawSource가 source-leaf 요약의 계층 자식으로 보인다.
- 실제 레코드가 없으면 `source_leaf_raw_missing_node_ids`에 남는다.
- compileall, ORDER 233 pytest, 관련 R read/traverse pytest, quick-smoke가 통과한다.
