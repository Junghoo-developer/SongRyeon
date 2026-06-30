# Execution Record: ORDER 120 Tool Use Budget Query Count Diagnostic Order Draft 2026-06-27 001

## 목적

ORDER_119 구현 후 live 테스트에서 드러난 `ToolUseBudgetFrame.query_count must not exceed max_query_attempts` 실패를 후속 발주서로 문서화했다.

## 관찰한 live 실패

사용자 입력:

```text
지금 송련의 말하기 모드 설계가 너무 빡빡한지, 아니면 적절한지 의견을 말해줘. 단, 이건 네 해석이라는 점을 밝혀줘.
```

ORDER_119 이후 출력은 더 이상 가짜 검색 fallback을 만들지 않았고, 다음 진단을 정직하게 표시했다.

```text
상태: structure_failed
trace/data: 0 / 0
structure_failure_stage: run_dry_turn
structure_failure_node: unknown
structure_failure_exception: ValueError
structure_failure_reason: ToolUseBudgetFrame.query_count must not exceed max_query_attempts
```

## 판단

ORDER_119는 실패 정직성 측면에서 작동했다.

새로 드러난 문제는 `ToolUseBudgetFrame`의 query count consistency 문제다.

이번 문제는 질문을 휴리스틱으로 분류해 우회할 문제가 아니다.

확인해야 할 핵심:

```text
1. 왜 query_count가 max_query_attempts를 초과했는가?
2. budget frame 생성 코드가 잘못된 값을 만들었는가?
3. ORDER_112 document context/search budget 변경과 충돌했는가?
4. schema validator는 유지되어야 하는가?
5. 실패 시 budget frame/source/route/L run 진단이 충분히 남는가?
```

## 문서화 변경

- `Administrative_Reform_1/04_Orders/ORDER_120_TOOL_USE_BUDGET_QUERY_COUNT_CONSISTENCY_DIAGNOSTIC_V0.md` 추가
- `Administrative_Reform_1/04_Orders/README.md`의 정식 발주서 범위를 `ORDER_120`까지 확장
- `ORDER_120` 요약과 링크 추가

## 비범위

이번 작업은 문서화만 수행했다.

코드 구현, schema 변경, runtime 변경, prompt 변경, smoke/pytest 추가는 하지 않았다.

현재 작업트리에는 ORDER_112, ORDER_118, ORDER_119 관련 구현 변경이 이미 존재하므로, 이번 기록은 ORDER_120 문서화 범위만 다룬다.
