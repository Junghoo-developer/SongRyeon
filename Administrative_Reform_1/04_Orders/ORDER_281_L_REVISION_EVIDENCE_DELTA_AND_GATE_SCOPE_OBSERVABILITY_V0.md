# ORDER 281: L Revision Evidence Delta And Gate Scope Observability v0

- 상태: 구현 및 검증 완료
- 작성일: 2026-07-20
- 선행 증거: `live_self_status_freshness_failure_2026_07_20_001.md`

## 1. 문제

라이브 자기상태 질문에서 최초 L3는 읽은 두 문서가 최근 개발 진도를 직접 설명하지 못한다고
`partial`로 판단했다. revision은 검색 후보만 추가했고 새 원문은 읽지 않았지만, 최신 L3는
같은 원문으로 `matched / achieved`로 승격했다. node_4는 공급된 문서와 답변의 일관성을
검사해 `pass`했지만, 현재 저장소 현실과의 최신성은 검사하지 않았다.

시간적 최신성의 의미·선택 정책은 사용자 결재 대상으로 남긴다. 이번 발주는 판정 변화와
검사 범위를 절대정보로 드러내는 데만 한정한다.

## 2. 목표

1. 최초 L3와 각 revision L3의 원문 근거 집합을 CODE가 대조한다.
2. 새 원문, 새 검색 후보, 판정 변화 여부를 별도 절대정보로 기록한다.
3. 새 원문 없이 판정이 바뀐 사실을 숨기지 않는다.
4. node_4의 `pass`가 공급 근거 일관성 검사이며 프로젝트 현재성 검사가 아님을 구조와
   terminal에 표시한다.

## 3. 구현 범위

L3 achievement frame에 다음 CODE-owned 관측값을 검토한다.

- `previous_achievement_frame_id`
- `previous_achievement_status`
- `new_read_doc_ids`
- `new_read_doc_count`
- `new_read_code_file_paths`
- `new_read_code_file_count`
- `new_original_material_count`
- `evidence_set_changed`
- `candidate_set_changed`
- `achievement_status_changed`
- `achievement_changed_without_new_original_material`

node_4 gate frame에는 검사 범위를 나타내는 고정 CODE 필드를 검토한다.

- `gate_evidence_scope=supplied_evidence_bundle`
- `project_currentness_check_status=not_run`

terminal은 위 값을 사람이 읽을 수 있게 표시한다.

## 4. 권한 경계

- 전후 ID 집합, count, status 차이: CODE 절대정보
- 새 원문이 의미상 더 좋은지: 판단하지 않음
- 같은 원문에 대한 L3 재평가 허용 여부: 이번 발주에서 변경하지 않음
- 무엇이 최신 문서인지와 최신성을 언제 요구하는지: 이번 발주에서 결정하지 않음
- node_4의 기존 의미 검사와 guard: 약화하거나 확장하지 않음

## 5. 테스트

1. 최초 L3는 previous 없음과 delta 0을 기록한다.
2. revision에서 새 검색 후보만 생기고 원문 집합이 같으면 candidate changed와
   new original 0을 기록한다.
3. 위 상태에서 `partial -> achieved`면 changed-without-new-original이 true다.
4. revision에서 새 read_doc이 생기면 정확한 ID/count를 기록한다.
5. node_4 frame과 terminal은 supplied-evidence scope와 currentness not-run을 표시한다.
6. 기존 L3 승격 정책과 node_4 pass/block 동작은 바꾸지 않는다.

## 6. 금지

- `최근/현재/최신` 키워드 휴리스틱
- 문서 시각 기반 정렬·필터·선택 정책
- 새 원문 없으면 무조건 승격 금지
- L3 의미 판단을 CODE가 교정
- node_4를 프로젝트 전체 사실 검사기로 과장
- 검색 예산, L/R router, R/Neo4j 변경

## 7. 완료 조건

- 라이브 실패의 `partial -> achieved`가 어떤 근거 변화와 함께 일어났는지 절대정보로 보인다.
- node_4 `pass`의 검사 범위가 terminal에서 오해 없이 보인다.
- compileall, 표적 pytest, 전체 pytest, smoke-test를 통과한다.
- 실행 기록과 잔여 정책 질문을 남긴다.
