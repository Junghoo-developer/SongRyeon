# L Loop Budget Consistency MVP 2026-06-24 001

## 목적

`ORDER_091_L_LOOP_BUDGET_CONSISTENCY_V0.md`를 구현했다.

## 구현 내용

`songryeon_core/loops/l_loop_budget.py`에 다음 파생 제약을 추가했다.

```text
approved_max_tool_calls >= 1 + approved_max_read_doc_calls
```

이 제약은 L1이 기본값보다 많은 `read_doc` 예산을 요청한 경우에만 적용한다.

## 이유

`read_doc=2`를 승인하면서 `tool_calls=2`를 유지하면 실제 실행은 다음에서 멈춘다.

```text
1. search_docs
2. read_doc 첫 번째 문서
```

두 번째 문서를 읽으려면 최소 3회의 tool call 예산이 필요하다.

## Runtime 라벨

보정이 발생하면 `approval_reason`에 다음 라벨이 들어간다.

```text
CODE_STATUS:tool_calls_aligned_with_read_doc_budget
```

## 추가 smoke-test

`LowToolCallBudgetFakeAdapter`를 추가했다.

이 adapter는 일부러 다음 예산을 요청한다.

```text
requested_max_tool_calls = 2
requested_max_read_doc_calls = 2
```

검증 기대값은 다음과 같다.

```text
approved_max_tool_calls = 3
approved_max_read_doc_calls = 2
```

첫 번째 `tool_budget` frame도 같은 보정값을 실제 실행 예산으로 사용해야 한다.

## 함께 문서화한 것

송련 본점 `AGENTS.md` 지침을 Core 연습판에도 이식했다.

추가 파일:

- `AGENTS.md`
- `AGENTS.en.md`
- `Administrative_Reform_1/01_Maintenance_System/AGENT_WORKING_RULES_FROM_MAIN_PROJECT.md`

핵심 이유는 PowerShell 한글 모지바케와 메타정보 책임 경계 혼동을 반복하지 않기 위해서다.

