# ORDER_212_RUNTIME_VESSEL_R_FAILURE_DIAGNOSTICS_DISPLAY_V0

## 상태

즉시 구현 승인.

## 배경

ORDER_210 live 테스트에서 runtime 상단 감사판은 다음 사실을 보여줬다.

- node_1이 R을 선택했다.
- R vessel ledger가 생겼다.
- node_3 Vessel R material은 `failed / 0개`였다.

하지만 pretty runtime 출력만 보면 R이 왜 실패했는지 바로 보이지 않았다.
별도 `vessel-r-traverse` 단독 명령을 돌려야 다음 원인을 확인할 수 있었다.

```text
failure_stage: R2:step_0001
failure_type: schema_failed
failure_reason: R2 expected_information_granularity is invalid
```

## 목표

qwen-turn / fake-turn runtime 결과에 Vessel R 실패 진단을 더 잘 드러낸다.

## 구현 범위

1. `run_dry_turn()` 결과 dict에 다음 필드를 추가한다.
   - `vessel_r_failure_stage`
   - `vessel_r_failure_type`
   - `vessel_r_failure_reason`
   - `vessel_r_final_sufficiency_status`
   - `vessel_r_final_continuation_status`

2. `terminal_view.py`
   - 학습용 절대정보 감사판의 R/Vessel 줄에 실패 stage/type/reason을 제한 길이로 표시한다.
   - node_3 brief의 Vessel R material 줄에도 failure type/reason을 표시한다.

## 원칙

1. 실패 원인을 숨기지 않는다.
2. R traversal 의미 판단이나 route 정책은 바꾸지 않는다.
3. 긴 raw payload 전체는 출력하지 않는다.
4. 실패 reason은 사람이 읽을 수 있을 정도로만 짧게 표시한다.

## 완료 조건

1. runtime 감사판에서 R 실패 stage/type/reason을 바로 볼 수 있다.
2. 기존 ORDER_209 감사판 표시가 깨지지 않는다.
3. 관련 pytest가 통과한다.
