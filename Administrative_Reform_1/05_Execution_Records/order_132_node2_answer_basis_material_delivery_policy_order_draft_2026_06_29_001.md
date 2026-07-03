# ORDER_132 Node2 Answer Basis Material Delivery Policy Order Draft 2026-06-29 001

## 작성 배경

ORDER_125에서 L3 문서별 요약 frame이 구현되었다.
다음 단계로 node_3가 원문 문서 context와 L3 요약을 언제 어떤 태도로 사용할지 정해야 한다.

사용자 아이디어:

- node_2가 `absolute_first`에 가까운 판단을 하면 node_3는 원문을 우선 봐야 한다.
- 더 유연한 답변에서는 L3 요약이 문서 폭탄을 줄이는 보조 재료가 될 수 있다.
- 장기적으로는 턴 앞/중간/뒤 모든 단계에서 메타정보 판단이 필요할 수 있지만, 지금은 node_2 -> node_3 답변 재료 전달 정책까지만 연다.

## 작성 내용

- 새 발주서 `ORDER_132_NODE2_ANSWER_BASIS_MATERIAL_DELIVERY_POLICY_V0.md`를 추가했다.
- `Administrative_Reform_1/04_Orders/README.md`의 정식 발주서 범위를 `ORDER_132`까지 갱신했다.
- ORDER_132는 구현 전 발주서이며, 이번 기록에서는 코드 변경을 수행하지 않았다.

## 핵심 방향

- `answer_basis_mode=absolute_first` -> `raw_document_primary`
- `answer_basis_mode=relative_allowed` -> `summary_assisted`
- `answer_basis_mode=mixed_or_uncertain` -> `uncertainty_summary_assisted`

## 제외한 것

- L3 요약으로 원문 context를 자동 대체하지 않았다.
- node_3 context packing 정책을 바꾸지 않았다.
- code가 문서 관련성이나 중요도를 판단하게 만들지 않았다.
- node_0 요약, node_5 기억 압축, 장기기억 DB, vector DB, scheduler, W/R loop는 열지 않았다.

## 검증

- 문서 작성 작업이므로 compileall/pytest/smoke-test는 실행하지 않았다.
