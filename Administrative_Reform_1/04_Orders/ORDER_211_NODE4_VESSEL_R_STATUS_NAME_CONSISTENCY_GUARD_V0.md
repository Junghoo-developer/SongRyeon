# ORDER_211_NODE4_VESSEL_R_STATUS_NAME_CONSISTENCY_GUARD_V0

## 상태

즉시 구현 승인.

## 배경

ORDER_210 live 테스트에서 node_1은 R route를 정상 선택했다.

그러나 R traversal 후 node_3 brief에는 다음 절대 상태가 기록됐다.

- `vessel_r_material.material_status=failed`
- `vessel_r_material.r_loop_task_status=failed`
- `vessel_r_material.material_items=[]`

그런데 node_3 최종 답변 본문은 `vessel_r_material.task_status`를 `insufficient`라고 표현했다.
node_4는 "R 성공 과장"은 막지만, `failed` 상태를 다른 상태명으로 바꿔 말하는 경우는 아직 별도 code guard로 잡지 않는다.

## 목표

node_4가 Vessel R material의 상태명을 최종 답변 본문과 비교한다.

특히 다음 경우를 잡는다.

1. brief의 `vessel_r_material_status`가 `failed`인데 본문이 `present`, `available`, `insufficient`, `partial`, `sufficient` 등 다른 상태명으로 직접 표현하는 경우.
2. brief의 `vessel_r_material.r_loop_task_status`가 `failed`인데 본문이 `insufficient`, `partial`, `sufficient` 등 다른 task status로 직접 표현하는 경우.

## 원칙

1. 일반적인 "자료가 부족하다" 표현을 과도하게 막지 않는다.
2. `status`, `task_status`, `상태` 같은 상태명 표기 문맥에서만 검사한다.
3. node_4 기존 성공 과장 guard는 유지한다.
4. R2 enum 실패 원인은 이번 발주에서 고치지 않는다.

## 완료 조건

1. failed Vessel R material을 `insufficient` status로 직접 말한 보고문을 node_4가 needs_revision 처리한다.
2. 기존 graph node ID leak / success overclaim guard가 깨지지 않는다.
3. 관련 pytest가 통과한다.
