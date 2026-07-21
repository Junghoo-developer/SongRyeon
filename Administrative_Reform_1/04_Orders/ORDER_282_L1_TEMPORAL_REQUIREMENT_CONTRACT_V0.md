# ORDER 282: L1 Temporal Requirement Contract v0

- 상태: 구현 완료
- 작성일: 2026-07-21
- 선행 감사: `l_temporal_requirement_and_tool_path_audit_2026_07_21_001.md`

## 1. 목표

L1이 현재 사용자 질문 하나를 기준으로 이번 L루프에 시간 근거가 필요한지 판단하고,
그 판단과 출처 경계를 `L1GoalFrame`에 명시한다.

이번 발주는 시간 도구를 실행하지 않는다. 다음 L2 시간 도구 선택 발주의 입력 계약만
만든다.

## 2. 필드

- `temporal_requirement_status=required|not_required|uncertain`
- `temporal_evidence_goal`
- `temporal_requirement_reason`
- `temporal_requirement_basis_text`
- `temporal_requirement_info_class=relative|absolute_status`
- `temporal_requirement_semantic_judgement_status=ran|failed`

`temporal_requirement_basis_text`는 CODE가 현재 `user_query`를 그대로 복사한 절대정보다.
LLM은 이 문자열을 생성하거나 수정하지 않는다.

LLM 판단 성공 시 시간 요구 status/goal/reason은 위 basis field 하나에 대응한 relative
정보다. LLM 실패 또는 adapter 미사용 시 CODE는 의미 판단을 대신하지 않고 다음으로
닫는다.

```text
temporal_requirement_status=uncertain
temporal_requirement_info_class=absolute_status
temporal_requirement_semantic_judgement_status=failed
```

## 3. 경계

- 현재 사용자 질문 하나만 시간 중요도 판단 근거로 사용한다.
- memory packet, workspace manifest, 실제 파일 시각은 이번 판단에 넣지 않는다.
- L2는 다음 발주에서 L1 판단과 ToolCatalog/budget을 함께 보고 mixed 도구 선택을 한다.
- `uncertain`은 CODE가 시간이 중요하다고 판단했다는 뜻이 아니다.

## 4. 표시

terminal과 `run_dry_turn()` 결과에서 다음을 구분한다.

- 시간 요구 status
- 판단 실행 상태
- 정보 분류
- 판단 이유와 시간 근거 목표

## 5. 테스트

1. LLM 성공 시 status/goal/reason과 CODE 복사 basis가 함께 기록된다.
2. LLM이 basis text를 출력하지 않아도 CODE 복사값을 사용한다.
3. 시간 계약 필드가 누락되거나 잘못되면 L1 전체가 정직한 rule fallback으로 닫힌다.
4. fallback은 `uncertain`, `absolute_status`, `failed`이며 시간 의미를 생성하지 않는다.
5. terminal과 dry-run summary가 계약 상태를 표시한다.
6. 기존 artifact/budget/L2/L3 계약은 유지한다.

## 6. 금지

- `최신`, `최근`, 날짜 표현 keyword 휴리스틱
- 파일 수정 시각 정렬
- 시간 도구 또는 Git history 도구 추가
- LToolScope, L2, L3 의미 정책 변경
- CODE가 `required` 또는 `not_required` 선택
- R/Vessel 시간축 변경

## 7. 완료 조건

- compileall 통과
- 표적 pytest 통과
- 전체 pytest 통과
- smoke-test 통과
- 실행 기록 작성
