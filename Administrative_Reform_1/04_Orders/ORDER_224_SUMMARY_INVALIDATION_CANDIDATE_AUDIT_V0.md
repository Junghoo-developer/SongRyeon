# ORDER 224: Summary Invalidation Candidate Audit v0

## 목표

Neo4j Vessel 안의 source version lineage와 summary graph node를 읽어서, source 변경 때문에 무효화 후보가 되는 summary를 read-only로 계산한다.

## 배경

ORDER 164 계열에서 로컬 DataStore 기준 source 변경과 summary invalidation ledger 기반은 이미 마련되어 있다.

하지만 Neo4j Vessel에 이미 적재된 summary 노드에 실제로 어떤 무효화 후보가 있는지는 별도 read-only 감사가 필요하다.

ORDER 223 결과에 따르면 현재 Neo4j summary 598개는 모두 ORDER 222 이전 legacy 요약이다. legacy라는 이유만으로 무효화하지 않는다. 무효화 후보는 source lineage에서 `content_changed`가 확인되고, summary가 superseded source graph node를 근거로 삼은 경우에만 잡는다.

## 구현 범위

새 CLI를 추가한다.

```powershell
python main.py vessel-summary-invalidation-candidate-audit --database neo4j --format text
```

감사 결과는 다음을 보고한다.

- 전체 summary 수
- source lineage 수
- `content_changed` lineage 수
- superseded source 수
- invalidation candidate summary 수
- 이미 invalidated 상태인 후보 수
- 수동 검토 후보 수
- 후보 sample records

## 후보 판정 기준

1. source lineage payload의 `lineage_status`가 `content_changed`다.
2. 해당 lineage의 `superseded_source_graph_node_ids`가 있다.
3. summary payload의 `source_graph_node_ids` 안에 superseded source id가 있다.
4. summary가 이미 `validity_status=invalidated_by_source_change`이면 새 후보가 아니라 already invalidated로 센다.

## 하지 않는 것

- Neo4j summary node 수정
- `validity_status` 실제 변경
- summary 삭제
- legacy summary 자동 무효화
- source lineage 재계산
- LLM 호출
- R/L loop 변경

## 완료 조건

- Neo4j read-only candidate audit CLI가 추가된다.
- 후보 계산은 code absolute 정보만 사용한다.
- 결과는 local TraceStore/DataStore에 audit frame으로 기록된다.
- 실제 Neo4j record는 수정하지 않는다.
- `python -m compileall songryeon_core main.py`
- 관련 pytest 통과
- `python main.py quick-smoke`

