# ORDER 278 L Conditional Fallback Success Contract 감사 기록

- 실행일: 2026-07-20
- 상태: 감사 완료, 제품 코드 변경 없음
- 대상: ORDER 276 사례 B

## 1. 판정

사례 B의 최신 L3 `partial`은 L2가 대체 문서를 못 찾았기 때문이 아니다.

L2는 사용자가 허용한 ORDER 275 대체 문서를 찾아 실제 원문 1개를 읽었다. 그러나 현재
성공 계약은 `A가 없으면 B`를 구조화하지 못하고, revision L3에도 명시 문서 resolver와
새 운영 성공 판정이 함께 전달되지 않는다. 결과적으로 도구 실행은 대체 경로를 완수했지만
최종 채점은 존재하지 않는 첫 문서 A 하나만 기준으로 남았다.

## 2. 실행 순서 복원

### L1

`L1:goal_frame`은 다음 조건을 보존했다.

- 먼저 `ORDER_275_DOES_NOT_EXIST.md`를 직접 읽는다.
- 없으면 ORDER 275 final state index 발주서를 검색해 실제 원문을 읽는다.
- 최소 원문 수는 1개다.
- 성공 조건은 첫 파일의 존재 확인과 첫 파일 또는 대체 ORDER 275 원문 읽기다.

즉 L1의 의미 이해는 이번 실패의 직접 원인이 아니다. 다만 이 조건은
`macro_goal`과 `l_loop_success_condition` 자유문장 안에만 있다.

### CODE resolver와 L2

`L:explicit_artifact_reference_frame`은 두 참조를 분리했다.

- 첫 경로: `not_found`
- `ORDER_275`: `unique`
- unique 문서: `04_Orders/ORDER_275_L_RUN_FINAL_STATE_INDEX_AND_LEGACY_SCOPE_V0.md`

L2 실행은 다음과 같다.

1. 최초 `read_artifact`: 존재하지 않는 첫 경로, 원문 0개
2. revision 1 `search_docs`: ORDER 275 후보 확보
3. revision 2 `search_docs`: 후보 재확보
4. revision 3 `read_doc`: 위 ORDER 275 원문 1개, 2,552자 확보

L2는 대체 경로를 잃지 않았고 실제 읽기까지 완료했다. 중복 검색 두 번은 효율 문제지만,
조건부 대체 성공 판정 실패의 직접 원인은 아니다.

### 최신 L3와 continuation

`L3:revision_achievement:0003`은 다음 절대 상태를 기록했다.

- `actual_read_doc_count=1`
- `original_material_count=1`
- `original_material_requirement_status=satisfied`
- `semantic_goal_match_status=matched`
- `requested_doc_hint=...ORDER_275_DOES_NOT_EXIST.md`
- `goal_match_status=partial`
- `controller_decision=null`
- `achievement_status=partial`

`L:continuation:0004`는 최신 L3가 `achieved`가 아니어서
`CODE_STATUS:max_continuation_attempts_reached`로 `stop_failed_final` 처리했다.
continuation 코드는 먼저 L3 만족 여부를 검사하므로, 올바른 구조적 `achieved`가 있었다면
최대 시도 수보다 앞에서 정상 종료할 수 있었다.

## 3. 직접 원인

### 높음: revision L3 입력에서 resolver frame이 빠진다

`run_l3_revision_result_keeper()`의 입력 ID는 L1 goal, revision query, revision tool source로
새로 구성된다. 호출부도 `L:explicit_artifact_reference_frame`을 넘기지 않는다.

- `songryeon_core/nodes/l3_result_keeper.py:213`
- `songryeon_core/nodes/l3_result_keeper.py:240`
- `songryeon_core/loops/l_loop.py:1524`

따라서 revision L3의 `allowed_source_data_ids` 안에는 code가 확정한 대체 문서 좌표가 없다.
L3 목표 대조는 사용자 문장에서 첫 경로를 다시 뽑아 단일 `requested_doc_hint`로 사용한다.

### 높음: 성공 계약이 단일 문서 hint만 표현한다

`_build_goal_match_context()`는 `requested_doc_hint` 하나만 고른 뒤 그 하나와 읽은 문서를
대조한다. `all_of`, `any_of`, `ordered_fallback` 같은 요구 관계는 없다.

- `songryeon_core/nodes/l3_result_keeper.py:1378`
- `songryeon_core/nodes/l3_result_keeper.py:1391`

resolver helper도 첫 unresolved 참조의 `normalized_ref/raw_ref`를 즉시 반환할 수 있다.
따라서 resolver frame을 단순히 revision에 추가하는 것만으로는 조건부 대체 계약이 해결되지
않는다.

- `songryeon_core/nodes/l3_result_keeper.py:1662`
- `songryeon_core/nodes/l3_result_keeper.py:1683`

### 높음: revision 원문 확보에 대응하는 운영 성공 판정이 없다

L3 code 판정은 controller가 `stop_success`이고 원문이 있을 때만 `achieved`다.
revision L3는 `final_control_data_id=null`로 호출되므로 대체 원문을 읽어도
`original_material_acquired_without_controller_stop_success`로 `partial`에 머문다.

- `songryeon_core/nodes/l3_result_keeper.py:661`
- `songryeon_core/nodes/l3_result_keeper.py:676`

## 4. 구조적 원인

`L1GoalFrame`에는 자유문장 성공 조건만 있고, 명시 문서 사이의 요구 관계를 나타내는
구조 필드가 없다.

- `songryeon_core/core/schemas.py:3701`
- `songryeon_core/core/schemas.py:3733`

현재 스키마는 다음을 구별할 수 없다.

- A만 반드시 읽어야 한다.
- A와 B를 모두 읽어야 한다.
- A 또는 B 중 하나면 된다.
- A를 먼저 시도하고, 없을 때만 B가 허용된다.

code가 L1 자유문장을 키워드로 해석해 이 관계를 만들면 숨은 휴리스틱이 된다. 따라서
구조화 필드 없이 code만 작게 고치는 방식은 부적합하다.

## 5. 모델과 prompt 판정

L3 prompt는 단일 `requested_doc_hint`가 있으면 그 문서를 직접 읽지 않은 상태에서
`matched`를 내지 말라고 한다.

- `songryeon_core/prompts/l3_result_keeper_v0.md:66`

그런데 revision 3의 L3 LLM은 대체 ORDER 275 원문을 보고 `matched`를 냈다. 이는 현재
prompt 계약과 어긋난 모델 출력이다. 다만 code의 goal-match guard가 최종 상태를
`partial`로 유지했으므로 거짓 `achieved`로 승격되지는 않았다.

정리하면 모델은 오히려 낙관적으로 판단했고, 이번 `partial`의 주원인은 모델 성능 부족이
아니라 조건부 대체를 표현하지 못하는 schema/code 계약이다.

## 6. downstream 판정

node_3는 첫 파일이 없다는 점과 대체 ORDER 275 문서를 근거로 답했다. node_4는 그 제한을
숨기지 않은 보고를 `pass` 처리했다. 따라서 이번 사례에서 node_3/node_4가 L 성공을
거짓으로 과장한 증거는 없다.

다만 L return은 `partial/l2_retryable`, 최신 continuation은 `stop_failed_final`이므로,
downstream이 이를 완전한 L 성공으로 재분류해서는 안 된다.

## 7. 후속 발주 후보

후속 후보명:

```text
ORDER_279_L_CONDITIONAL_ARTIFACT_REQUIREMENT_CONTRACT_V0
```

권장 설계 범위:

1. L1이 명시 문서 요구 관계를 `exact_one/all_of/any_of/ordered_fallback` 중 하나로
   구조화한다.
2. 참조 문자열과 실제 resolved ID는 CODE resolver가 소유한다.
3. LLM은 어떤 참조 관계가 사용자 요청에 맞는지 판단하되 ID를 발명하지 않는다.
4. revision L3에 resolver frame과 구조화 요구 계약을 전달한다.
5. revision read 성공을 나타내는 code-owned 운영 상태를 별도로 기록한다.
6. 구조화 요구 관계, 원문 최소 수, semantic match가 모두 충족될 때만 `achieved`로 닫는다.

설계 시 `resolver에서 unique인 아무 문서나 읽으면 성공` 같은 단축 패치는 금지한다.
그 방식은 A와 B를 모두 요구한 질문을 하나만 읽고 성공으로 오판할 수 있다.

## 8. 수정 위험도

- resolver frame을 revision에 전달: 중간. 출처 복원에는 필요하지만 단독으로는 불충분하다.
- 단일 hint를 다중 요구 계약으로 변경: 높음. exact lookup 전체의 성공 의미가 바뀐다.
- revision 운영 성공 상태 추가: 중간. continuation 종료 조건과 return summary에 영향을 준다.
- prompt만 강화: 낮은 구현 비용이지만 해결 효과가 부족하다.

따라서 다음 작업은 즉석 패치가 아니라 별도 발주와 결정론적 테스트가 필요한 작은 설계
변경으로 다룬다.

## 9. 검증

이번 작업은 기존 export와 정적 코드를 감사한 문서 작업이다. 제품 코드·prompt·schema는
수정하지 않았으며 compileall, pytest, smoke-test는 재실행하지 않았다.
