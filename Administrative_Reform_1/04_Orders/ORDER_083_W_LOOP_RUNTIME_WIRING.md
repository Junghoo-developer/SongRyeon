# ORDER 083: W Loop Runtime Wiring

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: W1이 있어도 1의 라우팅 권한과 0의 공급 권한을 보존해야 한다는 설계  
**목표**: `1 -> 0 -> W1 -> 0 -> 1` 경로를 추가하고, W1 추천을 1이 받아 최종 라우팅하게 만든다.

## 목표 경로

기본 W 경로:

```text
user -> 0(pre_route_report) -> 1(route=W)
1 -> 0(targeted_memory_supply_for_W)
0 -> W1(problem_triage)
W1 -> 0(loop_return_summary_for_1)
0 -> 1(route=2/L/R/ask_user/hold/stop)
```

W1은 1에게 돌아온다.

W1은 2나 3으로 직접 가지 않는다.

## 1의 라우팅 변경

`node_1`이 선택할 수 있는 route에 `W`를 추가한다.

route 후보:

```text
2
L
W
```

미래 후보:

```text
R
C
M
```

MVP에서 R/C/M은 아직 live route가 아니다.

## W 호출 조건

1은 다음 상황에서 W를 고려한다.

1. 바로 `2`로 보내기에는 설계/권한/문서화 위험이 있다.
2. 하지만 `L`로 보낼 만큼 문서 검색 필요가 확실하지 않다.
3. 사용자의 말이 이후 루프 정의나 발주서에 영향을 줄 수 있다.
4. node_4가 이전 턴에서 needs_revision을 냈고, 단순 재답변보다 문제 진단이 필요하다.
5. 사용자가 "왜 이렇게 됨", "이상한 점", "다음 수"처럼 구조 판단을 요구한다.

## W 추천 처리

W1의 `recommended_next_route`는 다음처럼 처리한다.

```text
2 -> 1이 route=2를 새로 기록한다.
L -> 1이 route=L을 새로 기록한다.
R -> R 미구현이면 hold_for_definition 또는 safe uncertainty로 낮춘다.
ask_user -> 1이 route=2로 보내되 Node3Brief를 질문형으로 제한하거나 별도 ask_user path로 보낸다.
hold_for_definition -> 코딩하지 말고 문서/발주 보존 경로로 닫는다.
stop_safe_failure -> 2/3에 safe limitation brief를 준다.
W_retry -> 0이 한 번만 추가 context를 공급하고 W1을 재호출한다.
```

## 반복 제한

W는 한 턴에서 기본 1회만 허용한다.

`W_retry`는 최대 1회만 허용한다.

같은 턴에서 W가 두 번 `unclear`를 반환하면 1은 W를 다시 호출하지 않는다.

## 상태/trace 요구

W 경로는 다음을 기록해야 한다.

1. `route:W`
2. `memory_packet:W:targeted_memory_supply`
3. `W1:problem_triage_frame`
4. `memory_packet:node_1:W_loop_return_summary`
5. W 이후 1의 새 route

## 완료 기준

1. `run_dry_turn`에서 W 경로를 force 또는 fake 조건으로 실행할 수 있다.
2. pretty runtime에 W1 진단이 보인다.
3. W1 추천 후에도 실제 최종 route는 node_1 route record로 남는다.
4. W가 직접 node_2/node_3로 이동하지 않는다.
5. W 반복 제한이 smoke로 검증된다.
