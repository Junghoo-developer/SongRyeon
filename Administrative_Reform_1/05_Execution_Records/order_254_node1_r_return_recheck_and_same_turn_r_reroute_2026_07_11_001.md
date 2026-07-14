# ORDER 254 실행 기록: node_1 R 복귀 재판정과 같은 턴 R 최대 2회

## 결과

구현 및 검증 완료.

## 구현 동선

Vessel live R이 끝난 뒤 더 이상 코드가 곧바로 route 2를 만들지 않는다.

```text
node_1 -> R run 1
R run 1 -> node_0 R top-level run memory -> node_1 recheck

node_1 recheck -> L 또는 2
node_1 recheck -> R run 2 (명시 정책 활성 + 상한 미도달)

R run 2 -> node_0 R top-level run memory -> node_1 final recheck
node_1 final recheck -> L 또는 2
```

capsule skeleton R은 이번 반복 배선에 포함하지 않았다.

## 코드 정책

```text
same_turn_r_reroute_enabled = false
max_r_runs_per_turn = 2
effective ceiling = 2
```

기본값은 한 번이다. `--same-turn-r-reroute`를 명시한 현장 Vessel R만
두 번째 전체 실행을 열 수 있다. 사용자가 2보다 큰 값을 넣어도 v0 코드 상한은 2다.

코드는 R 재실행의 의미 적합성을 판단하지 않는다. node_1 LLM이 원 질문과
code-supplied R return context를 보고 L/R/2를 고르고, controller는 횟수와 ID 충돌만 검사한다.

## node_0 상위 R 기억

`songryeon_core/runtime/same_turn_r_reroute.py`의
`record_r_top_level_run_memory()`가 각 R 전체 실행 뒤 다음 절대정보를 기록한다.

- return packet / activity ledger / traverse result 좌표
- run index와 prior run memory 좌표
- traverse/task/failure 상태
- R1 근거 계약 요구량과 실제 관측량
- 선택/검사 graph node IDs
- terminal/raw original 관측 횟수

주요 ID:

```text
R:run:0001:run_frame
R:run:0001:node_0:return_memory_frame
R:run:0001:reroute_controller_frame
R:run:0001:return:route:R
```

## 다음 R에 공급한 정보

2회차 R의 R1/R2/R3 입력에는 1회차 top-level run memory의 코드 복사 뷰가 들어간다.
R2 공식 후보표에는 다음 절대 표지를 붙인다.

```text
seen_in_prior_top_level_r_run
prior_run_seen_role
```

길목 node 재방문이 필요할 수 있으므로 이전 ID를 코드가 강제 제외하지 않았다.
후보의 의미 적합성과 다른 가지 필요성 판단은 R2/R3 LLM 책임으로 유지했다.

## 충돌 방지

- Vessel batch ID에 `run_0001`, `run_0002`를 넣었다.
- R 복귀 route와 controller, run memory를 run-scoped ID로 기록했다.
- live R 실행 중간의 turn activity graph link도 batch별 ID로 분리했다.
- 턴 종료의 통합 activity link는 두 R activity ledger를 모두 집계한다.

## CLI

현장 turn/chat 공통 옵션에 다음을 연결했다.

```text
--same-turn-r-reroute
--max-r-runs-per-turn 2
```

## 테스트 확인값

전용 테스트에서 확인한 값:

```text
vessel_r_run_count = 2
effective_max_r_runs_per_turn = 2
run frames = R:run:0001:run_frame, R:run:0002:run_frame
first controller = rerun_R / allowed=true
second controller = close_route_2 / allowed=false
final route = R:run:0002:return:route:2
turn activity R Vessel ledger count = 2
```

또한 2회차 R1/R2 입력에 prior run memory가 들어가고, R2 공식 후보표에서
1회차에 본 후보가 `seen_in_prior_top_level_r_run=true`로 표시되는 것을 확인했다.

## 검증

```text
python -m compileall songryeon_core main.py
passed

R 관련 집중 회귀시험
55 passed in 17.64s

ORDER 254 + 기존 Vessel live 통합시험
7 passed in 11.70s

python -m pytest
432 passed, 5 deselected in 80.12s

python main.py smoke-test
SMOKE_TEST_OK

git diff --check
passed
```

## 일부러 하지 않은 것

- R 3회차 실행
- capsule skeleton R 반복
- node_1 실패를 감춘 의미 fallback
- 이전 graph node 강제 제외
- node_2 차단/재라우팅 권한 추가
- L 성공 판정 변경
- R1/R2/R3의 의미 역할 변경
- 키워드 휴리스틱 추가

## 남은 위험

- 실제 Qwen이 1회차 R 결과를 보고 R/L/2를 얼마나 잘 고르는지는 live 품질 시험 대상이다.
- 두 번째 R이 같은 길을 다시 볼 수는 있다. 이는 코드 오류가 아니라 재방문을 허용한 정책이며,
  R2/R3가 prior-run 표지를 활용하는 품질을 별도로 관찰해야 한다.
- 이번 구현은 자동 복구 정책이 아니다. node_1이 실패한 경우 strict runtime은 실패를 드러낸다.
