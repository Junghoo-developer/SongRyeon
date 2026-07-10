# ORDER 223: Vessel Summary Provenance Audit v0

## 목표

기존 Neo4j Vessel에 저장된 summary graph node들이 ORDER 222의 run provenance 필드를 갖고 있는지 read-only로 감사한다.

## 배경

ORDER 222부터 새로 생성되는 LLM 요약에는 다음 필드가 기록된다.

- `summary_run_id`
- `night_turn_id`
- `night_batch_id`
- `summary_created_at`
- `run_provenance_status`

하지만 ORDER 222 이전에 이미 Neo4j에 들어간 요약 노드는 이 필드가 없을 수 있다. 이 노드들을 바로 삭제하거나 무효화하면 추적 가능성이 깨진다. 먼저 수량과 샘플을 절대정보로 세어야 한다.

## 구현 범위

새 CLI를 추가한다.

```powershell
python main.py vessel-summary-provenance-audit --database neo4j --format text
```

감사 결과는 다음을 보고한다.

- 전체 summary node 수
- provenance가 완전한 summary 수
- legacy로 분류되는 summary 수
- provenance가 일부만 있는 summary 수
- invalid status summary 수
- provenance status별 count
- data_kind별 count
- legacy/incomplete 샘플

## 분류 기준

- `recorded`: 필수 provenance 필드가 모두 있고 status가 정상인 요약
- `legacy`: provenance 필드가 전혀 없는 기존 요약
- `incomplete`: provenance 필드가 일부만 있는 요약
- `invalid_status`: `run_provenance_status` 값이 허용 목록 밖인 요약

## 하지 않는 것

- Neo4j 기록 수정
- summary node 삭제
- summary node 무효화
- legacy node 자동 backfill
- source 변경 무효화 정책 구현
- R/L loop 변경

## 완료 조건

- Neo4j summary provenance audit CLI가 추가된다.
- 감사 결과는 절대정보로 기록된다.
- missing/incomplete 상태를 사람이 볼 수 있다.
- 기존 DB payload를 수정하지 않는다.
- `python -m compileall songryeon_core main.py`
- 관련 pytest 통과
- `python main.py quick-smoke`

