# ORDER 085: W Loop Smoke And Runtime View

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: W루프는 문제를 줄이기 위한 장치이므로, 런타임에서 판단 근거와 반복 제한이 보여야 한다는 필요  
**목표**: W루프의 성공/보류/포기/반복제한 경로를 smoke와 pretty runtime으로 검증한다.

## Smoke Cases

### Case 1: No Problem Direct Close

입력:

```text
안녕?
```

예상:

- W를 호출하지 않거나, 호출해도 `problem_status=no_problem`.
- 최종 route는 `2`.
- L 검색 없음.
- 최종 답변은 간단한 인사.

### Case 2: Structural Risk

입력:

```text
R루프를 모든 비도구 대화 루프로 만들까?
```

예상:

- W 호출.
- `problem_status=problem_detected`.
- `loop_damage_risk=high`.
- `recommended_next_route=hold_for_definition` 또는 `ask_user`.
- 바로 코딩 경로로 가지 않음.

### Case 3: Solvable By L

입력:

```text
문서 메모리 인덱스가 무엇을 읽는지 알려줘
```

예상:

- W를 거치지 않고 L로 가도 됨.
- W를 거친다면 `solvability=solvable_with_current_structure`, `recommended_next_route=L`.
- L 검색 결과가 brief로 이어짐.

### Case 4: Future R Dependency

입력:

```text
너는 누구니?
```

예상:

- 현재 MVP에서는 L 또는 safe uncertainty.
- W가 호출되면 `problem_type=future_loop_dependency` 또는 `current_structure_gap`.
- `solvability=needs_new_loop_or_tool` 가능.
- R 미구현 사실을 숨기지 않음.

### Case 5: W Retry Limit

fake W1이 계속 `unclear`를 반환하게 한다.

예상:

- W 호출 최대 2회.
- 이후 `ask_user`, `hold_for_definition`, `stop_safe_failure` 중 하나로 닫힘.
- 무한 루프 없음.

### Case 6: Node4 Remand Blocking

fake node_3가 내부 ID/코드 식별자를 답변에 노출한다.

예상:

- node_4가 `needs_revision`.
- 최종 answer는 반려 원문이 아니라 safe blocking answer.

## Runtime View

pretty runtime에 W가 있으면 다음을 표시한다.

```text
- W1 problem triage:
  - problem_status:
  - blur_risk:
  - loop_damage_risk:
  - solvability:
  - give_up_recommended:
  - so_what:
  - recommended_next_route:
  - LLM/source:
```

route 기록에는 다음이 보여야 한다.

```text
route=W
route_after_W=...
```

## 완료 기준

1. `python main.py smoke-test`에 W 관련 smoke가 포함된다.
2. fake adapter로 W 경로를 재현할 수 있다.
3. Qwen adapter로 최소 1개 W 경로를 실행할 수 있다.
4. W가 없던 단순 턴의 성능이 악화되지 않는다.
5. node_4 remand blocking smoke가 통과한다.
