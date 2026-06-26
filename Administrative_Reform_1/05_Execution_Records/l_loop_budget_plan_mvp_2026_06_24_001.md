# L Loop Budget Plan MVP 2026-06-24 001

## 목적

`ORDER_090_L_LOOP_BUDGET_PLAN_V0.md`의 1차 구현을 반영했다.

이번 구현의 핵심은 다음 선을 분리하는 것이다.

```text
L1 = 이번 L루프에 필요한 예산을 요청한다.
CODE:BUDGET_POLICY = 정책 한도 안에서 승인 예산을 확정한다.
L runtime = 승인 예산을 실제 tool budget으로 사용한다.
L3 = 승인 예산과 실제 산출물을 함께 보고 달성 여부를 판단한다.
```

## 구현 범위

### 스키마

- `L1GoalFrame`에 예산 요청 필드를 추가했다.
- `LLoopBudgetPlanFrame`을 추가했다.
- 예산 요청값, 승인값, 정책 상한, 승인 이유를 한 프레임에 함께 기록한다.

### L1

- `l1_goal_setter_v0.md`가 예산 요청 필드를 JSON으로 출력하게 했다.
- L1의 예산 요청은 최종 권한이 아니라 요청으로만 취급한다.

### Budget Policy

- `songryeon_core/loops/l_loop_budget.py`를 추가했다.
- `CODE:BUDGET_POLICY`가 `L:budget_plan_frame`을 만든다.
- 현재 1차 정책은 기본 예산과 L1 요청 중 큰 값을 쓰되, MVP 정책 상한을 넘기지 않는다.

현재 정책 상한은 다음과 같다.

```text
search_top_k <= 6
max_tool_calls <= 6
max_read_doc_calls <= 3
max_query_attempts <= 3
```

### L Loop

- L1 직후 budget plan을 기록한다.
- 이후 L루프는 승인된 예산값을 `search_top_k`, `max_tool_calls`, `max_read_doc_calls`, `max_query_attempts`로 사용한다.
- 모든 tool budget frame이 `L:budget_plan_frame`을 출처로 갖게 했다.
- L3 입력에도 `L:budget_plan_frame`이 들어가게 했다.

### Runtime 출력

- pretty runtime에 `L budget plan` 블록을 추가했다.
- 요청값, 승인값, 정책 상한, 승인 이유, L1 요청 이유를 볼 수 있다.

## 검증

다음을 통과했다.

```text
python -m compileall songryeon_core main.py
python main.py dry-run
python main.py smoke-test
```

추가 fake turn 검증에서 다음 흐름을 확인했다.

```text
L1 requested:
  search_top_k=5
  max_tool_calls=4
  max_read_doc_calls=2
  max_query_attempts=2

CODE approved:
  search_top_k=5
  max_tool_calls=4
  max_read_doc_calls=2
  max_query_attempts=3

tool budget:
  search_top_k=5
  max_tool_calls=4
  max_read_doc_calls=2
  max_query_attempts=3
```

`max_query_attempts`가 3으로 남은 이유는 현재 정책이 기본 예산보다 낮은 L1 요청으로 예산을 줄이지 않기 때문이다.

## 아직 하지 않은 것

이번 패치는 예산 결재선을 만든 것이다.

아직 실제로 여러 후보 문서를 순차적으로 `read_doc`하는 그래프 실행 변경은 넣지 않았다.

다음 단계는 승인된 `max_read_doc_calls`와 `search_top_k`를 바탕으로 L루프가 후보 문서를 여러 개 읽을 수 있게 만드는 것이다.

