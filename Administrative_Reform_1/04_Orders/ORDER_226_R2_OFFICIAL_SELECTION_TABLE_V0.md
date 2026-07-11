# ORDER 226: R2 Official Selection Table v0

## 상태

- Status: implemented
- Date: 2026-07-10
- Scope: Vessel R / R2 input stability

## 배경

ORDER 225 감사 장치로 R2 LLM 호출 input payload를 확인한 결과, R2 step 2 입력에는 `available_surface_refs`와 `candidate_records_by_surface_ref`가 실제로 들어 있었다.
그러나 Qwen raw output은 `No candidate surface refs provided in runtime input`이라고 응답했다.

따라서 원인은 후보 번호표 누락이 아니라, R2가 긴 payload 안의 번호표를 안정적으로 인식하지 못한 문제로 좁혀졌다.

## 목표

R2가 후보를 고를 때 긴 후보 record 안에서 ID를 찾지 않게 하고, payload 최상단의 `official_selection_table`에서만 `surface_ref`와 `node_ref`를 복사하도록 입력 구조를 안정화한다.

## 변경

- R2 input payload 최상단에 `official_selection_table`을 추가한다.
- `official_selection_table`에는 다음만 담는다.
  - `allowed_surface_refs`
  - `allowed_node_refs_by_surface_ref`
  - `surface_rows`
  - `candidate_rows`
  - `output_contract`
- 실제 graph node id와 summary text는 R2 공식 선택표에 넣지 않는다.
- 기존 `available_surface_refs`와 `candidate_records_by_surface_ref`는 호환용으로 유지한다.
- schema repair payload도 같은 `official_selection_table`을 보존한다.
- prompt는 공식 선택표를 가장 먼저 보도록 갱신한다.

## 하지 않는 것

- code가 어떤 후보가 의미적으로 맞는지 대신 선택하지 않는다.
- R3 권한이나 continuation 정책을 바꾸지 않는다.
- R loop 예산, node_1 라우팅, node_3 답변 정책은 바꾸지 않는다.
- Neo4j 구조나 graph memory 데이터를 변경하지 않는다.

## 완료 조건

- R2 payload 첫 key가 `official_selection_table`이어야 한다.
- R2가 `official_selection_table`만 보고도 valid ref를 선택할 수 있어야 한다.
- schema repair에서도 official table이 보존되어 valid ref를 유지할 수 있어야 한다.
- 기존 R2 validator는 표 밖 선택을 계속 차단해야 한다.
