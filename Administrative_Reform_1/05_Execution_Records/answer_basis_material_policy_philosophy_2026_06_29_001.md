# answer_basis_material_policy_philosophy_2026_06_29_001

작성일: 2026-06-29
대상 문서: `Administrative_Reform_1/00_Philosophy/Answer_Basis_Mode_And_Evidence_Role_Philosophy_2026_06_26.md`

## 1. 기록 목적

사용자가 제안한 장기 구조 감각을 철학 문서에 반영했다.

핵심 제안:

- 장기적으로 메타정보 판단은 턴 앞, 턴 중간, 턴 끝 모두에서 필요해질 수 있다.
- 하지만 지금 당장 전체 구조를 열지 않는다.
- 단기적으로는 node_2가 node_3에게 답변 태도를 정해 주는 선에서만 다룬다.

## 2. 반영 내용

철학 문서에 `2026-06-29 추가 메모: 메타정보 판단의 장기 위치` 섹션을 추가했다.

추가한 경계:

- `absolute_first`일 때는 원문, count, trace/data 장부, document material packet 같은 검증 가능한 재료를 우선한다.
- `relative_allowed` 또는 `mixed_or_uncertain`일 때는 장기적으로 L3, 5, 또는 별도 요약 노드가 source가 붙은 요약 카드/문서별 근거 카드를 만들 수 있다.
- 단, 요약은 code의 절대정보가 아니라 LLM이 생성한 상대정보 또는 혼합정보로 보존해야 한다.
- 지금 구현 범위는 node_2 -> node_3 답변 태도 전달까지만 둔다.

## 3. 하지 않은 것

- 새 발주서 작성 없음
- 코드 변경 없음
- 테스트 실행 없음
- L3 per-document summary 구현 없음
- node_5 기억 압축 구현 없음
- 전역 메타정보 판단 루프 구현 없음

## 4. 후속 후보

나중에 다음 주제를 별도 발주서로 좁힐 수 있다.

- answer material policy
- absolute_first일 때 raw evidence 우선 공급
- relative/mixed일 때 source-attached summary card 공급
- L3 문서별 요약과 node_4 검토 연결
- node_5 기억 압축 요약과 node_4 승인 연결
