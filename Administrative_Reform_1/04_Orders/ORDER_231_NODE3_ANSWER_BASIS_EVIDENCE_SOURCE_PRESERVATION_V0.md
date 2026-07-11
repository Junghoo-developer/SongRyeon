# ORDER 231: Node3 Answer Basis Evidence Source Preservation v0

## 상태

- Status: implemented
- Date: 2026-07-10
- Scope: node_2 answer-basis -> node_3 input brief source ledger

## 배경

컴퓨터 재시작 이후 Vessel R live 재확인 중 Neo4j 연결 실패 상황이 발생했다.
이때 정상적으로 실패 상태를 보고해야 했지만, node_2 answer-basis에서 생성된 `evidence_roles`가 node_3 brief로 복사되는 과정에서 role의 `source_data_id`가 `Node3InputBriefFrame.source_data_ids`에 포함되지 않아 구조 실패가 발생했다.

오류:

```text
Node2EvidenceRole.source_data_id must exist in frame.source_data_ids
```

## 목표

node_2가 answer-basis에서 부여한 evidence role의 source 좌표를 node_3 input brief가 그대로 보존하게 한다.

## 변경

- `record_node3_input_brief()`가 `answer_basis_frame.source_data_ids`를 node_3 brief source_data_ids에 포함한다.
- `answer_basis_frame.evidence_roles[].source_data_id`도 node_3 brief source_data_ids에 포함한다.
- Vessel R partial/failed 상황에서도 answer-basis evidence role 좌표 누락 때문에 structure_failed가 나지 않게 한다.

## 하지 않는 것

- node_2의 의미 판단을 code가 바꾸지 않는다.
- evidence role 자체를 새로 생성하지 않는다.
- Neo4j 연결 실패를 성공으로 바꾸지 않는다.
- R route 정책이나 R traversal 전략은 변경하지 않는다.

## 완료 조건

- node_2 answer-basis role source가 node_3 brief.source_data_ids에 보존된다.
- `Node2EvidenceRole.source_data_id must exist in frame.source_data_ids` 구조 실패가 재발하지 않는다.
- quick-smoke가 유지된다.
