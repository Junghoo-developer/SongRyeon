# ORDER 277: L Original Material Attitude And Grounding Limit Consistency v0

- 상태: 구현 및 검증 완료
- 작성일: 2026-07-20
- 완료일: 2026-07-20

## 1. 배경

ORDER 276 사례 C에서 실제 `read_doc=0`, `original_material_count=0`인데 CODE grounding
block은 `L 원문은 확보됐지만`이라고 썼다. node_3 본문은 후보 12개와 원문 0개를 정확히
구분했지만, CODE가 붙인 한계 문장 자체가 절대 count와 충돌했다.

## 2. 원인

`node_2_handoff._l_loop_result_attitude_hint()`가 L3 semantic execution 실패만 확인하고
원문 수를 검사하지 않은 채 항상 다음 태도를 선택했다.

```text
l_loop_original_material_acquired_l3_semantic_failed
```

`node_3_reporter`는 이 태도를 받아 `L 원문은 확보됐지만` 문장을 생성했다.

## 3. 목표

semantic failure와 원문 확보 여부를 기존 CODE 절대값으로 분리한다.

- `original_material_count > 0`: 기존 원문 확보 태도 유지
- `original_material_count == 0`: 새 원문 미확보 태도 사용

code는 문서 의미나 관련성을 판단하지 않는다.

## 4. 구현 범위

1. `Node3InputBriefFrame.l_loop_result_attitude_hint` 허용값에
   `l_loop_no_original_material_l3_semantic_failed`를 추가한다.
2. node_2가 `original_material_count`를 읽어 semantic failure 태도를 분기한다.
3. node_3 grounding 한계 문장은 원문 0개일 때 후보/장부를 원문처럼 말하지 않도록 한다.
4. 기존 원문 확보 + L3 semantic failure 태도는 그대로 보존한다.

## 5. 테스트

1. semantic failed + original count 0이면 원문 미확보 태도다.
2. semantic failed + original count 1이면 기존 원문 확보 태도다.
3. 원문 0개 grounding block에 `L 원문은 확보됐지만`이 없어야 한다.
4. 원문 0개 grounding block은 후보/장부를 원문 근거로 말하지 않는다고 표시한다.
5. ORDER 272의 실제 원문 확보 + L3 실패 회귀 계약은 유지한다.
6. 전체 pytest와 smoke-test를 통과한다.

## 6. 금지

- 후보 context를 실제 read_doc 원문으로 재분류
- supplied context count의 의미 변경
- L3 semantic validator 약화
- node_4 guard 약화
- 질문 단어 휴리스틱 추가
- L/R 예산·반복·router·Neo4j 변경

## 7. 완료 조건

- CODE grounding block의 원문 확보 문장이 `original_material_count`와 충돌하지 않는다.
- 기존 원문 확보 semantic failure 경로를 깨지 않는다.
- ORDER 276 사례 C의 모순을 deterministic test로 재현하고 차단한다.
