# ORDER_215_R_TRAVERSE_PATH_DUPLICATE_PRESERVATION_V0

## 상태

즉시 구현 승인.

## 배경

ORDER_214 live 확인 중 R3 schema repair 이후 다음 코드 예외가 발생했다.

```text
ValueError: RLoopVesselTraverseResultFrame selected path mismatch
```

감사 결과 `RLoopVesselTraverseResultFrame`은
`selected_graph_node_ids`를 R2 선택 frame 수와 같은 길이의 traversal path로 검증한다.
하지만 builder는 `_unique_strings()`로 selected/inspected graph node id를 중복 제거하고 있었다.

즉, R traversal이 같은 graph node를 다시 밟거나 같은 id가 반복되면
path 길이가 줄어들어 result frame validator와 충돌한다.

## 목표

R traversal의 selected/inspected graph node path는 중복 제거하지 않고 순서대로 보존한다.

## 구현 범위

1. path용 helper를 추가한다.
   - 빈 값은 제거한다.
   - 중복 graph node id는 제거하지 않는다.

2. 다음 frame builder에서 path field는 path helper를 사용한다.
   - `RLoopVesselTraverseResultFrame.selected_graph_node_ids`
   - `RLoopVesselTraverseResultFrame.inspected_graph_node_ids`

3. `RLoopReturnSummaryFrame`은 기존 schema처럼 중복 제거를 유지한다.

4. provenance/source id 묶음은 기존처럼 중복 제거를 유지한다.

## 금지

- R2/R3 의미 판단을 바꾸지 않는다.
- R traversal 선택 정책을 바꾸지 않는다.
- validator를 약화하지 않는다.
- 중복 선택을 성공처럼 미화하지 않는다. 단, path 장부는 실제 밟은 순서를 보존한다.

## 완료 조건

1. 같은 graph node id가 반복된 R path도 result frame이 path 길이를 보존한다.
2. ReturnSummary와 source/provenance id는 기존처럼 중복 제거된다.
3. 관련 pytest / compileall / smoke-test가 통과한다.
