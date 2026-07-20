# ORDER 276: L Live Final State Reconciliation Matrix v0

- 상태: 실행 및 감사 완료
- 작성일: 2026-07-20
- 완료일: 2026-07-20

## 1. 배경

ORDER 275는 최초 L tool control 판단, revision 포함 최신 L3 achievement, 최종
continuation을 별도 절대정보 좌표로 보존하도록 구현했다. deterministic pytest와 smoke는
통과했지만 실제 Qwen 실행에서 상태와 사용자 답변이 같은 최신 source를 따르는지는 아직
분리 검증하지 않았다.

## 2. 목표

제품 코드를 새로 확장하지 않고 실제 Qwen L 실행 세 사례를 확인한다.

1. 처음부터 원문을 확보해 성공하는 실행
2. 최초 명시 문서 확보 실패 뒤 revision 검색·읽기로 회복하는 실행
3. 검색 후보만 확보하고 원문을 읽지 못하는 실행

## 3. 공통 확인값

- `l_loop_final_decision`
- `l_loop_final_decision_scope`
- `l_loop_pre_revision_terminal_control_decision`
- `l_loop_latest_l3_achievement_data_id`
- `l_loop_final_status`
- `l_loop_final_status_source_data_id`
- `l_loop_final_continuation_status`
- 실제 `read_doc`/`read_artifact` 원문 수
- node_3 brief의 L 상태와 node_4 gate
- 사용자 답변이 원문 확보 수준을 과장하는지 여부

## 4. 사례

### A. 단순 원문 성공

ORDER 275 발주서의 정확한 파일을 직접 읽고 핵심을 설명하게 한다.

기대:

- 최초 control과 최신 L3가 모두 성공 계열
- canonical source가 최신 L3 achievement ID
- node_4 pass 또는 정직한 반려

### B. 초기 실패 뒤 revision 회복

존재하지 않는 명시 파일을 먼저 요청하되, 없으면 실제 ORDER 275 문서를 다시 검색해
원문을 읽도록 요청한다.

기대:

- 초기 실패 record는 보존
- revision L3가 성공하면 `l_loop_final_status=achieved`
- legacy control과 canonical latest status의 source가 분리됨
- downstream은 최신 L3 결과를 사용

### C. 후보만 확보

도구 호출 예산을 검색 1회 수준으로 제한해 후보는 찾되 원문 읽기까지 도달하지 못하는
상태를 관찰한다.

기대:

- 후보와 실제 원문 수가 분리됨
- `candidates_only`, `partial`, 예산 종료 중 실제 record에 맞는 상태가 노출됨
- 최종 답변이 원문을 읽었다고 주장하지 않음

## 5. 판정

- **통과**: canonical source와 최신 L3 ID가 일치하고 downstream이 같은 상태를 사용함
- **부분 통과**: 상태 출처는 정직하지만 사용자 답변 수행이나 회복이 부족함
- **실패**: stale control을 최종 상태로 사용하거나 원문 미확보를 성공으로 과장함
- **환경 미확인**: Ollama/Qwen 실행 자체에 도달하지 못함

## 6. 금지

- 시험 중 validator, prompt, 예산 기본값을 고쳐 결과를 덮기
- 과거 실패 record 삭제
- 후보 존재를 원문 확보로 간주
- Qwen의 의미 판단을 code가 대신 생성
- R/Neo4j, router, node_4, 반복 횟수 변경

## 7. 완료 조건

1. 세 사례의 명령, 주요 절대값, 상대 평가를 실행 기록에 남긴다.
2. 결함이 있으면 바로 패치하지 않고 다음 발주 후보로 분리한다.
3. 통과하면 ORDER 275 L 최종 상태 계약을 안정 기준선으로 둔다.
