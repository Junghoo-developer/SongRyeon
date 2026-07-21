# ORDER 282 실행 기록: L1 Temporal Requirement Contract v0

- 실행일: 2026-07-21
- 결과: 완료
- 발주서: `ORDER_282_L1_TEMPORAL_REQUIREMENT_CONTRACT_V0.md`

## 1. 배경

선행 감사에서 현재 L루프에는 시간 중요도를 판단하는 명시적 L1 계약이 없고,
문서·코드 도구에도 파일 시각을 비교하기 위한 전용 계약이 없음을 확인했다.
시간 도구와 선택 정책을 한 번에 열지 않고, 이번 발주는 먼저 현재 사용자 질문 하나를
기준으로 L1이 시간 근거 필요 여부를 판단하는 입력 계약만 추가했다.

## 2. 구현

`L1GoalFrame` schema를 0.4로 올리고 다음 필드를 추가했다.

- `temporal_requirement_status=required|not_required|uncertain`
- `temporal_evidence_goal`
- `temporal_requirement_reason`
- `temporal_requirement_basis_text`
- `temporal_requirement_info_class=relative|absolute_status`
- `temporal_requirement_semantic_judgement_status=ran|failed`

LLM은 현재 `user_query`만 보고 status/goal/reason을 생성한다. CODE는
`temporal_requirement_basis_text`에 실제 `user_query`를 복사하고, LLM이 같은 이름의
필드를 출력해도 사용하지 않는다.

LLM 출력이 검증되면 시간 판단은 `relative + ran`으로 기록한다. 필드 누락, schema
실패, adapter 미사용 시 L1 전체가 기존 rule fallback으로 닫히며 시간 계약은 다음
절대 상태만 기록한다.

```text
status=uncertain
goal=CODE_STATUS:temporal_evidence_goal_not_set
reason=CODE_STATUS:l1_temporal_requirement_judgement_not_run
info_class=absolute_status
semantic_judgement_status=failed
```

terminal과 `run_dry_turn()` 요약은 status, 시간 근거 목표, 이유, 정보 분류, 의미 판단
실행 상태를 표시한다. terminal은 사용자 질문 원문을 중복 노출하지 않고
`basis=current_user_query_copy`라고만 표시한다.

## 3. 유지한 경계

- `최신`, `최근`, 날짜 표현을 찾는 CODE keyword 휴리스틱을 추가하지 않았다.
- 파일 수정 시각 정렬, Git history, 시간 전용 도구를 추가하지 않았다.
- LToolScope, L2, L3, R/Vessel의 의미 정책을 변경하지 않았다.
- CODE는 `required` 또는 `not_required`를 대신 선택하지 않는다.
- 이번 판단에는 memory packet, workspace manifest, 실제 파일 시각을 넣지 않았다.

## 4. 검증

```text
python -m compileall songryeon_core main.py
PASS

python -m pytest tests/test_order_282_l1_temporal_requirement_contract.py -q
5 passed

python -m pytest tests/test_order_282_l1_temporal_requirement_contract.py tests/test_order_279_l_conditional_artifact_requirement.py tests/test_order_135_code_evidence_accounting.py -q
12 passed

python -m pytest
526 passed, 1 skipped, 5 deselected

python main.py smoke-test
SMOKE_TEST_OK

git diff --check
PASS
```

## 5. 다음 단계

다음 결재 대상은 시간 근거를 실제로 공급하는 CODE 도구 계약이다. 그 단계에서는
ToolCatalog capability, 파일 관측/수정 시각의 출처, LToolScope가 시간 도구를 숨기지
않는 규칙을 먼저 설계해야 한다. 이번 ORDER_282만으로 최신 문서를 찾을 수 있다고
주장하지 않는다.
