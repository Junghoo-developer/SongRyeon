# ORDER 234: R RawSource Text Material And Hierarchy Direction v0

## 상태

- Status: implemented / Qwen end-to-end passed after ORDER 235
- Date: 2026-07-10
- Scope: Vessel R RawSource text supply / hierarchy direction / runtime count honesty

## 배경

ORDER 233 live에서 R은 source-leaf 요약 다음의 정확한 RawSource 노드까지 도달했다. 하지만 R3는 RawSource를 `low_summary`, `insufficient`, `deeper`로 판단했다.

추가 감사에서 다음을 확인했다.

- RawSource 노드 자체에는 원문 text가 없고 `source_text:*` 절대 좌표가 있다.
- 실제 3,722자 원문은 해당 `GraphMemorySource` support record에 있다.
- R3 selected candidate에는 RawSource 메타데이터만 공급됐다.
- RawSource를 요약한 source-leaf summary가 RawSource의 하위 child로 다시 노출됐다.
- 기존 `raw_original_material_seen_count`는 원문 열람이 아니라 RawSource 노드 선택을 셌다.

## 목표

- RawSource가 가진 정확한 `source_text:*` 좌표를 code가 조회해 선택된 RawSource의 원문 재료로 공급한다.
- RawSource를 요약한 summary를 더 낮은 계층 child로 취급하지 않는다.
- RawSource 노드 선택 수와 실제 원문 text 열람 수를 분리해 기록한다.

## 구현 경계

- code는 RawSource payload의 `source_data_ids` 안에 있는 `source_text:*`만 조회한다.
- 조회된 원문은 절대정보이며 source text data ID, 글자 수, path와 함께 기록한다.
- R1/R2에는 원문 text를 주지 않고 선택된 RawSource를 검사하는 R3에만 원문을 노출한다.
- 원문을 찾지 못하면 `missing`으로 기록하고 다른 자료로 대체하지 않는다.
- 기존 원본 노드 선택 최대 5회 안전 상한은 유지한다.

## 하지 않는 것

- 키워드, 유사도, 최신성 휴리스틱을 넣지 않는다.
- R3의 의미 충분성 판단을 code가 대신하지 않는다.
- source-leaf summary나 RawSource를 새로 생성하지 않는다.
- Neo4j 데이터나 기존 요약을 삭제하지 않는다.
- R1/R2 선택 정책과 예산 상한을 변경하지 않는다.

## 완료 조건

- 실제 Neo4j RawSource가 가리키는 source text가 read packet에 정확한 출처와 함께 보존된다.
- R3 selected record에는 선택된 RawSource 원문이 보인다.
- R2 후보 카드에는 원문 text가 노출되지 않는다.
- RawSource에서 source-leaf summary로 되돌아가는 가짜 child가 사라진다.
- runtime에 RawSource 노드 선택 수와 실제 원문 text 열람 수가 따로 보인다.
- compileall, 관련 pytest, quick-smoke, Qwen live가 통과한다.
