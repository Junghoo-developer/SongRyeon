# ORDER 274: L Revision Final Status Reconciliation Audit v0

## 1. 배경

ORDER 273 live 사례 D에서 Vessel R 실패 뒤 L로 복구했다. L의 최초 `read_artifact`는
명시 문서를 찾지 못해 `stop_failed`를 기록했지만, revision은 `search_docs -> read_doc`으로
원문 1개를 확보했다. 최신 L3는 다음처럼 기록됐다.

- `achievement_status=achieved`
- `semantic_goal_match_status=matched`
- `llm_semantic_execution_status=ran`
- `llm_semantic_failure_type=none`
- 최종 continuation=`stop_achieved`

그런데 turn summary의 `l_loop_final_decision`은 `stop_failed`로 남았다.

## 2. 목표

코드를 바로 고치지 않고 다음 질문에 답한다.

1. `l_loop_final_decision`은 정확히 어느 단계의 record를 가리키는가.
2. revision 성공 뒤에도 이전 실패값이 남는 이유는 무엇인가.
3. stale 값이 node_0, node_1, node_2, node_3, node_4에 실제로 전파되는가.
4. 기존 실패 이력을 지우지 않으면서 최종 상태를 정직하게 표시하려면 어떤 구조가 필요한가.

## 3. 감사 범위

- `songryeon_core/loops/l_loop.py`
- `songryeon_core/loops/l_loop_continuation.py`
- `songryeon_core/nodes/l3_result_keeper.py`
- `songryeon_core/nodes/node_0_memory_supplier.py`
- `songryeon_core/loops/l_loop_activity_ledger.py`
- `songryeon_core/runtime/dry_run.py`
- `songryeon_core/runtime/user_turn.py`
- L revision, continuation, candidate/original-material 관련 pytest/smoke

## 4. 감사 결론

### 4.1 원인

`LLoopResult.final_control_decision`은 이름과 달리 **revision을 포함한 L run 전체의 최종 상태가
아니다.** 최초 L2 도구 실행 구간의 마지막 `LLoopControlFrame.decision`을 가리킨다.

revision 구간은 다음 값만 갱신한다.

- revision query/tool result
- revision L3 preserved/achievement
- current L3 ID
- continuation frame과 `final_continuation_status`

revision 구간은 새 `LLoopControlFrame`을 만들지 않고 `final_control_data_id`와
`final_control_decision`도 다시 쓰지 않는다. 따라서 최초 구간이 `stop_failed`였다면 revision이
성공해도 그 값은 남는다.

### 4.2 현재 downstream 영향

현재 사용자 답변 경로는 stale `final_control_decision`을 최종 판단으로 사용하지 않는다.

- node_0 return summary는 source 순서상 최신 revision L3 achievement를 선택한다.
- node_0 return summary는 최신 continuation frame을 선택한다.
- node_1은 node_0가 공급한 최신 L3/continuation/count를 받는다.
- node_2/node_3는 return summary의 최신 상태를 받는다.
- ORDER 273 사례 D의 최종 답변은 실제로 L 성공 근거를 사용했고 Neo4j 실패도 공개했다.

따라서 현재 사용자 답변 오염 위험은 낮다.

### 4.3 남은 위험

`dry_run`과 `user_turn` export에는 `l_loop_final_decision`이라는 이름으로 stale 값이 노출된다.
현재는 관측 정합성 문제지만, 향후 scheduler/router/recovery가 이 필드를 canonical final state로
사용하면 잘못된 복구나 재실행을 선택할 수 있다.

위험도:

- 현재 최종 답변: 낮음
- runtime/export 해석: 중간
- 향후 자동 복구 정책: 높음

### 4.4 테스트 공백

현재 테스트는 다음을 각각 확인한다.

- 최초 도구 구간의 `stop_success`, `stop_candidate_only`
- revision read path와 budget count
- revision L3 frame 생성
- continuation의 continue/stop 상태

하지만 다음 하나의 통합 계약은 없다.

```text
최초 control 실패 -> revision 원문 확보 -> 최신 L3 achieved -> stop_achieved
-> export가 최초 실패와 최종 상태를 서로 다른 이름과 source ID로 보존
```

## 5. 권장 구현안

기존 실패 이력을 성공으로 덮어쓰지 않는다. 또한 code가 LLM 의미 판단을 대신하지 않는다.

다음 구현 발주에서는 새 code-owned 상태 색인을 추가한다.

권장 필드:

- `pre_revision_terminal_control_data_id`
- `pre_revision_terminal_control_decision`
- `latest_l3_achievement_data_id`
- `latest_l3_achievement_status`
- `final_continuation_data_id`
- `final_continuation_status`
- `final_status_source_data_id`
- `final_status_source_kind`

원칙:

1. 최초 `stop_failed` record는 삭제하거나 성공으로 변경하지 않는다.
2. 최종 의미 상태는 최신 L3 record의 값과 생성자/info class를 그대로 참조한다.
3. code는 어느 record가 최신 canonical source인지 ID로 선택할 뿐, 새 의미 판정을 쓰지 않는다.
4. 기존 `l_loop_final_decision`은 즉시 의미를 바꾸지 않는다.
5. 호환 필드에는 `legacy_pre_revision_control` scope/deprecation 표시를 붙인다.
6. terminal/export는 `최초 도구 종료 판단`과 `revision 포함 최종 상태`를 분리해서 표시한다.

## 6. 다음 구현 발주 후보

`ORDER_275_L_RUN_FINAL_STATE_INDEX_AND_LEGACY_SCOPE_V0`

완료 조건 후보:

1. fail -> revision success 통합 fixture가 추가된다.
2. 최초 control failure ID와 최신 L3 success ID가 둘 다 보존된다.
3. canonical final source는 최신 L3/continuation을 가리킨다.
4. node_0 return summary와 export의 최신 상태가 일치한다.
5. 기존 단일 실행 success/candidate-only 동작은 깨지지 않는다.
6. `compileall`, 표적 pytest, 전체 pytest, smoke-test를 통과한다.

## 7. 금지

- 과거 `stop_failed` record 삭제
- revision 성공 시 실패 이력 payload 덮어쓰기
- L3 의미 판단을 code rule로 재생성
- validator 약화
- L/R 반복 횟수 변경
- router, node_4, Neo4j 설정을 같은 패치에 혼합

## 8. 이번 발주 결과

이번 ORDER는 감사 전용이다. 제품 코드와 테스트는 수정하지 않는다.

