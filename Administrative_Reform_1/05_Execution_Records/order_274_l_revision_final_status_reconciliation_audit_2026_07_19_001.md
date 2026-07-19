# ORDER 274 L Revision Final Status Reconciliation 감사 기록

## 1. 판정

`l_loop_final_decision`은 revision 포함 최종 결과가 아니라 최초 L2 tool-controller 구간의
마지막 decision이다. revision 구간이 이 필드를 갱신하지 않으므로 stale failure가 남는다.

## 2. 확인한 코드 사실

### 최초 control 단계

- `songryeon_core/loops/l_loop.py`
- `read_artifact`가 unique match를 만들지 못하면 `LLoopControlFrame(decision=stop_failed)`를 기록한다.
- 이때 `final_control_data_id`와 `final_control_decision`이 설정된다.

### revision 단계

- 같은 파일의 continuation/revision loop는 revision query, tool result, revision L3를 만든다.
- `current_l3_achievement_id`와 `final_continuation_status`는 최신값으로 갱신된다.
- `final_control_data_id`와 `final_control_decision`은 갱신되지 않는다.

### LLoopResult/export

- `LLoopResult`는 최초 구간의 `final_control_*`와 revision 포함 `final_continuation_*`를 동시에 반환한다.
- `songryeon_core/runtime/dry_run.py`는 전자를 `l_loop_final_decision`으로 그대로 export한다.
- `songryeon_core/runtime/user_turn.py`도 같은 이름을 외부 요약에 복사한다.

### 사용자 답변 경로

- `songryeon_core/nodes/node_0_memory_supplier.py`는 최신 revision L3 achievement와 최신 continuation을 선택한다.
- node_0 return summary의 task/failure/route hint는 이 최신 record를 기준으로 생성된다.
- stale `final_control_decision`은 현재 node_0 -> node_1 -> node_2 -> node_3 답변 경로의 최종 판단에 쓰이지 않는다.

## 3. ORDER 273 재현 증거

사례 D export:

- 최초 `read_artifact`: unique document 미확보
- 최초 control: `stop_failed`
- revision `read_doc`: 원문 1개 확보
- 최신 L3: `achieved / matched / ran / none`
- 최신 continuation: `stop_achieved`
- export `l_loop_final_decision`: `stop_failed`
- node_4: `pass`
- 최종 답변: Neo4j 실패 공개 + L 문서 근거 사용

## 4. 영향 평가

| 영역 | 현재 영향 | 이유 |
| --- | --- | --- |
| 사용자 답변 | 낮음 | 최신 L3/continuation을 별도로 사용함 |
| runtime/export | 중간 | `final`이라는 이름과 실제 scope가 다름 |
| 활동 장부 | 낮음 | 모든 control/L3/continuation ID 자체는 보존됨 |
| 미래 자동 복구 | 높음 | stale field를 canonical status로 오인할 수 있음 |

## 5. 테스트 공백

revision 구성요소별 테스트는 있지만 `초기 실패 -> revision 성공 -> 최종 상태 source 정렬`을 한 번에
검증하는 통합 테스트가 없다.

## 6. 권고

ORDER 275에서 과거 실패 이력을 유지한 채 다음을 분리한다.

- pre-revision terminal control
- latest L3 achievement
- final continuation
- canonical final status source ID

code는 최신 source record를 선택하고 출처를 복사한다. 의미 성공을 새로 판단하지 않는다.

## 7. 검증

- 정적 코드 감사: 완료
- ORDER 273 cache 재검토: 완료
- 제품 코드 변경: 없음
- 테스트 실행: 없음. 감사 전용 문서 변경이므로 기존 ORDER 273 live 결과를 사용함

