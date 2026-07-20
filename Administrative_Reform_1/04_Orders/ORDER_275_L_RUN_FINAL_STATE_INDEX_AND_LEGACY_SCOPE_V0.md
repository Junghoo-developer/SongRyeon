# ORDER 275: L Run Final State Index And Legacy Scope v0

- 상태: 구현 및 검증 완료
- 완료일: 2026-07-20

## 1. 배경

ORDER 274 감사에서 `LLoopResult.final_control_decision`은 revision 포함 최종 결과가 아니라
최초 L2 도구 구간의 마지막 control decision임을 확인했다. 초기 실패 뒤 revision이 성공하면
최신 L3/continuation은 성공인데 export의 `l_loop_final_decision`만 실패로 남을 수 있다.

## 2. 목표

과거 실패 기록을 지우지 않고 다음 세 좌표를 분리한다.

1. revision 전 마지막 tool-controller 판단
2. revision을 포함한 최신 L3 achievement
3. 루프의 최종 continuation 상태

code는 어느 record가 최신인지 ID로 지정하고 값을 복사할 뿐, 새 의미 성공 판단을 생성하지 않는다.

## 3. 구현 범위

### 3.1 LLoopFinalStateIndexFrame

새 code-owned 절대정보 색인을 기록한다.

- `pre_revision_terminal_control_data_id`
- `pre_revision_terminal_control_decision`
- `pre_revision_terminal_control_scope`
- `latest_l3_achievement_data_id`
- `latest_l3_achievement_status`
- `latest_l3_achievement_generation_source`
- `final_continuation_data_id`
- `final_continuation_status`
- `final_status_source_data_id`
- `final_status_source_kind`
- source trace/data IDs

`final_status_source_data_id`는 최신 L3 achievement record를 가리킨다.

### 3.2 호환 필드

기존 `l_loop_final_decision`의 값을 즉시 바꾸지 않는다. 대신 다음 scope를 함께 공개한다.

```text
l_loop_final_decision_scope=legacy_pre_revision_terminal_control
```

신규 consumer는 `l_loop_final_status`와 `l_loop_final_status_source_data_id`를 사용한다.

### 3.3 장부와 화면

- LLoopResult output에 final-state index를 포함한다.
- L activity ledger에 final-state index stage를 추가한다.
- dry-run/user-turn export에 분리 필드를 추가한다.
- terminal은 `최초 도구 종료 판단`과 `revision 포함 최신 상태`를 따로 표시한다.

## 4. 정보 경계

- index frame 자체: `info_class=absolute`
- 생성자: `CODE:L_LOOP_FINAL_STATE_INDEXER`
- 의미 판단 실행: `not_run`
- `latest_l3_achievement_status`: L3 record에서 복사한 값
- code는 `achieved/partial/failed`를 새로 추론하지 않음

## 5. 테스트

1. schema가 source ID와 복사값 불일치를 거부한다.
2. 최초 control 실패와 최신 L3 성공이 동시에 보존된다.
3. canonical source가 최신 revision L3를 가리킨다.
4. final continuation이 `stop_achieved`로 보존된다.
5. legacy `l_loop_final_decision=stop_failed`에는 scope가 붙는다.
6. 신규 `l_loop_final_status=achieved`는 최신 L3 source ID와 함께 보인다.
7. 기존 단일 실행 success/candidate-only 회귀 테스트를 유지한다.

## 6. 검증 명령

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_275_l_run_final_state_index.py
python -m pytest
python main.py smoke-test
git diff --check
```

## 7. 금지

- 기존 `stop_failed` record 삭제 또는 payload 수정
- legacy 필드의 의미를 조용히 변경
- L3 의미 판정을 code로 재생성
- validator 약화
- L/R 반복 횟수 변경
- router, node_4, Neo4j 설정 변경

## 8. 완료 조건

- 시도 이력과 canonical latest source가 동시에 추적 가능하다.
- runtime에서 초기 실패와 revision 성공을 모순처럼 한 칸에 표시하지 않는다.
- 전체 검증이 통과한다.
