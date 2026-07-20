# ORDER 281 실행 기록: L Revision Evidence Delta And Gate Scope Observability v0

- 실행일: 2026-07-20
- 결과: 완료
- 발주서: `ORDER_281_L_REVISION_EVIDENCE_DELTA_AND_GATE_SCOPE_OBSERVABILITY_V0.md`

## 1. 감사 결론

라이브 자기상태 실패에서 최초 L3는 `partial`이었고 revision L3는 `achieved`로 바뀌었다.
이때 revision은 검색 후보 집합을 바꿨지만 새 `read_doc` 또는 `read_code_file` 원문은
추가하지 않았다. 기존 `_promote_revision_semantic_match()` 정책은 누적 원문 수와 최신 L3
의미 판정만 보며, 이번 revision이 새 원문을 추가했는지는 검사하지 않았다.

node_4는 node_3 보고문과 `Node3InputBriefFrame`으로 공급된 근거 묶음을 검사한다. 현재
프로젝트 전체 파일을 다시 읽어 최신성을 대조하는 단계는 없다. 따라서 기존 `pass`는
공급 근거 범위 안의 일관성 통과이며, 프로젝트 현재성 검증 통과가 아니다.

## 2. 구현

### L3 revision 절대정보 delta

`L3AchievementFrame` schema를 0.6으로 올리고 다음 값을 기록한다.

- 직전 achievement frame ID와 직전 상태
- 새 `read_doc` ID와 count
- 새 `read_code_file` 경로와 count
- 새 원문 합계
- 원문 근거 집합과 검색 후보 집합의 변화 여부
- achievement/semantic 상태 변화 여부
- 새 원문 없이 achievement가 바뀌었는지

직전 frame을 찾지 못하면 비교값을 추측하지 않고
`revision_evidence_delta_status=previous_frame_missing`으로 기록한다.

### node_4 검사 범위

`Node4GatekeeperFrame` schema를 0.3으로 올리고 다음 고정 절대정보를 추가했다.

- `gate_evidence_scope=supplied_evidence_bundle`
- `project_currentness_check_status=not_run`

terminal과 `run_dry_turn()` 결과에도 두 경계와 L3 delta 핵심값을 노출했다.

## 3. 유지한 정책

- 같은 원문에 대한 L3 재평가와 승격 정책은 변경하지 않았다.
- 시간·최신성 기반 문서 정렬 또는 선택 정책을 추가하지 않았다.
- node_4 의미 검사와 기존 CODE guard를 약화하거나 확장하지 않았다.
- L/R router, 검색 예산, R/Neo4j는 변경하지 않았다.

## 4. 검증

```text
python -m compileall songryeon_core main.py
PASS

python -m pytest tests/test_order_281_l_revision_evidence_delta_and_gate_scope.py -q
4 passed

python -m pytest tests/test_order_275_l_run_final_state_index.py tests/test_order_279_l_conditional_artifact_requirement.py tests/test_order_255_l_candidate_vs_original_material_status.py tests/test_schema_split_compat.py tests/test_order_119_structure_failed_honesty.py -q
20 passed

python -m pytest
521 passed, 1 skipped, 5 deselected

python main.py smoke-test
SMOKE_TEST_OK
```

## 5. 남은 결재 질문

1. 새 원문 없이 L3의 의미 재평가만으로 `partial -> achieved` 승격을 계속 허용할지.
2. 사용자가 현재·최근·최신 상태를 요구할 때 어떤 절대 시간 정보를 공급하고 어떤
   주체가 최신성 요구를 판단할지.
3. node_4보다 앞단에서 현재성 검사가 필요하다면 별도 도구와 근거 계약을 어떻게 둘지.
