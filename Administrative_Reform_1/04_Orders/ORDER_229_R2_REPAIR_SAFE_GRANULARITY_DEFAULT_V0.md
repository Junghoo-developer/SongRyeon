# ORDER 229: R2 Repair Safe Granularity Default v0

## 상태

- Status: implemented
- Date: 2026-07-10
- Scope: Vessel R / R2 schema repair stability

## 배경

ORDER 228 이후 live Vessel R 테스트에서 R2는 continuation work order를 따라 더 깊은 후보를 선택했다.
하지만 schema repair 모드에서 `selected_surface_ref`와 `selected_node_ref`는 올바르게 복사했음에도, `expected_information_granularity`에 `child_candidate` 같은 구조 라벨을 넣어 schema 실패가 발생했다.

이 문제는 후보 선택 실패가 아니라 enum 복사 실패다.
따라서 code가 의미 후보를 대신 고르지 않고, repair 모드에서만 보수적인 enum 안전 기본값을 제공한다.

## 목표

R2 schema repair 모드에서는 `expected_information_granularity`를 보수적으로 `unknown`으로 복사하게 하여, ref 선택은 유지하면서 enum 자유문구로 R루프가 실패하지 않게 한다.

## 변경

- `r2_copy_repair_table.safe_output_defaults.expected_information_granularity`를 추가한다.
- 기본값은 가능한 경우 `unknown`으로 둔다.
- repair prompt에 이 값을 그대로 복사하도록 명시한다.
- `candidate_kind`, `branch_role`, child structure label을 `expected_information_granularity`로 쓰지 못하게 경계를 추가한다.

## 하지 않는 것

- code가 어떤 그래프 후보를 의미적으로 선택하지 않는다.
- 정상 R2 첫 응답의 `expected_information_granularity`를 강제로 덮어쓰지 않는다.
- R1/R3 역할, Neo4j 구조, node_3 답변 정책은 변경하지 않는다.

## 완료 조건

- R2 첫 응답이 invalid granularity로 schema 실패해도 repair payload에 안전 기본값이 들어간다.
- repair 응답은 valid ref를 유지하면서 `expected_information_granularity=unknown`으로 통과한다.
- ORDER 228 continuation work order 테스트를 깨지 않는다.
