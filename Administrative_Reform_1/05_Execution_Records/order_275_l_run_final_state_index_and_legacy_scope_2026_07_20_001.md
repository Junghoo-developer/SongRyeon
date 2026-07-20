# ORDER 275 L Run Final State Index And Legacy Scope 실행 기록

- 실행일: 2026-07-20
- 상태: 구현 및 검증 완료
- 대상 발주서: `ORDER_275_L_RUN_FINAL_STATE_INDEX_AND_LEGACY_SCOPE_V0.md`

## 1. 문제

기존 `l_loop_final_decision`은 revision을 포함한 최종 결과가 아니라 최초 도구 구간의
마지막 control 판단이었다. 따라서 최초 구간 실패 뒤 revision L3가 성공한 경우에도
옛 필드만 보면 전체 L 실행이 실패한 것처럼 보일 수 있었다.

## 2. 구현

- `LLoopFinalStateIndexFrame`을 추가했다.
- 최초 control 판단, 최신 L3 achievement, 최종 continuation의 ID와 복사값을 분리했다.
- canonical 최종 상태의 출처는 항상 최신 L3 achievement record로 검증한다.
- 기존 `l_loop_final_decision` 값은 유지하고 scope를
  `legacy_pre_revision_terminal_control`로 공개했다.
- L activity ledger에 `final_state_index` 단계를 추가했다.
- dry-run/user-turn export에 최신 상태와 source ID를 추가했다.
- terminal에서 `최초 도구 종료 판단`과 `revision 포함 최신 상태`를 따로 표시한다.

## 3. 정보 경계

- 색인은 `generated_by=CODE:L_LOOP_FINAL_STATE_INDEXER`다.
- 색인은 `info_class=absolute`, `semantic_judgement_status=not_run`이다.
- code는 성공/실패를 새로 판단하지 않는다.
- `latest_l3_achievement_status`는 최신 L3 payload의 구조화 값을 복사한다.
- 기존 실패·부분성공 record는 삭제하거나 수정하지 않는다.

## 4. 회귀 검사

다음 반례를 고정했다.

1. 최초 control은 `stop_failed`다.
2. revision L3는 `achieved`다.
3. 최종 continuation은 `stop_achieved`다.
4. 세 값이 동시에 남고 canonical source는 revision L3 ID를 가리킨다.

기존 후보/원문 구분과 최신 revision 반환 요약 테스트도 함께 통과했다.

## 5. 검증 결과

```text
python -m compileall songryeon_core main.py
PASS

python -m pytest tests/test_order_275_l_run_final_state_index.py -q
4 passed

python -m pytest tests/test_order_275_l_run_final_state_index.py tests/test_order_255_l_candidate_vs_original_material_status.py tests/test_order_262_l3_trust_boundary_and_count_consistency.py -q
13 passed

python -m pytest
507 passed, 1 skipped, 5 deselected

python main.py smoke-test
SMOKE_TEST_OK
```

Windows host에서 symbolic link 생성이 불가능한 기존 테스트 1개는 조건부 skip되었다.

## 6. 남은 경계

- 기존 consumer 호환을 위해 `l_loop_final_decision` 이름 자체는 남아 있다.
- 신규 consumer는 `l_loop_final_status`와 `l_loop_final_status_source_data_id`를 사용해야 한다.
- 이번 작업은 L 의미 판단, 반복 횟수, router, node_4, R/Neo4j 동작을 변경하지 않았다.
