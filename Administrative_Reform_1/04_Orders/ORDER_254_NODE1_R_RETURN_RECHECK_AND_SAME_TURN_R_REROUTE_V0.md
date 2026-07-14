# ORDER 254: Node1 R Return Recheck And Same-Turn R Reroute v0

## 상태

구현 및 검증 완료.

## 목표

Vessel R 1회차가 끝난 뒤 코드가 곧바로 route 2로 닫지 않고, node_0이 R 활동을
정리해 node_1에게 공급한다. node_1은 원 질문과 R 결과를 보고 L/R/2 중 다음 길을
한 번 재판정할 수 있다. 정책을 켠 경우 R 전체 실행은 한 턴에 최대 2회까지 허용한다.

## 목표 동선

```text
node_1 -> R run 1
R run 1 -> node_0 top-level R run memory -> node_1 recheck

node_1 recheck -> 2
node_1 recheck -> L
node_1 recheck -> R run 2 (정책 활성화 + 상한 미도달)

R run 2 -> node_0 top-level R run memory -> node_1 final recheck
node_1 final recheck -> L 또는 2
```

R run 2 뒤에는 R을 allowed route에서 제거한다. 3회차 R은 열지 않는다.

## 정책

```text
same_turn_r_reroute_enabled = false
max_r_runs_per_turn = 2
effective ceiling = 2
```

기본값은 닫힘이다. 실험 flag를 켠 경우만 두 번째 R이 가능하다.

## node_0 상위 R 기억

각 R 전체 실행이 끝날 때 node_0은 다음 절대정보를 별도 frame에 기록한다.

- run index
- R return packet / activity ledger / traverse result 좌표
- traverse status / R task status / failure stage/type/reason
- R1 required material level/count
- 실제 evidence contract observed count/status
- 선택/검사한 graph node IDs
- terminal/raw original count
- 이전 top-level R run memory frame 좌표

이 frame은 node_1의 R 복귀 재판정과 다음 R run의 R1/R2/R3 입력 근거가 된다.

## 이전 R 경로 표시

코드는 후보의 의미 적합성을 판단하거나 후보를 강제로 제거하지 않는다.

대신 현재 R2 공식 후보표에 다음 절대 표지를 추가할 수 있다.

```text
seen_in_prior_top_level_r_run
prior_run_seen_role
```

같은 TimeAxis/묶음 같은 길목을 다시 통과할 수 있으므로 단순 ID 중복 차단은 하지 않는다.
R2는 이전 최종 재료 반복 여부와 새 가지 필요성을 의미적으로 판단한다.

## run namespace

- top-level run frame: `R:run:0001:run_frame`, `R:run:0002:run_frame`
- top-level memory: `R:run:0001:node_0:return_memory_frame`
- controller: `R:run:0001:reroute_controller_frame`
- 내부 Vessel batch/frame label에도 run index를 넣어 DataStore 충돌을 막는다.
- R 재선택 route는 run-scoped route ID로 기록한다.

## node_1 재판정

- 원 질문을 그대로 본다.
- code-copied R return context를 본다.
- 선택 가능한 route capability card를 다시 본다.
- L/R/2 의미 선택은 node_1 LLM 책임이다.
- 정책 비활성 또는 2회차 종료 뒤에는 R을 allowed route에서 제거한다.
- Qwen strict에서 node_1 재판정 실패를 silent semantic fallback으로 감추지 않는다.

## 금지

- 3회차 R 금지
- 사용자 문장 키워드로 R 재실행 여부를 코드가 결정하는 것 금지
- 이전 graph node ID를 전부 강제 제외하는 것 금지
- node_2 차단/재라우팅 권한 추가 금지
- L 성공 판정 변경 금지
- capsule skeleton 반복 실행 금지
- R1/R2/R3 자체 의미 역할 변경 금지

## 검증

1. 기본 정책에서는 Vessel R 한 번만 실행한다.
2. 정책 활성 상태에서 node_1이 R을 다시 고르면 R run 2가 실행된다.
3. R run 2 뒤 node_1 allowed routes에는 R이 없다.
4. R run별 핵심 ID가 충돌하지 않는다.
5. node_0 top-level R memory에 1회차 활동과 근거 계약이 보존된다.
6. R2 후보표가 이전 run에서 본 후보를 절대정보 표지로 구분한다.
7. node_1이 L을 고르면 기존 L 경로로 이어진다.
8. node_1이 2를 고르면 기존 node_2/3/4 경로로 이어진다.
9. compileall, pytest, smoke-test를 통과한다.
