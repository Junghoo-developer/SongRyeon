# ORDER 090: L Loop Budget Plan v0

**계층**: 발주서  
**상태**: 설계 확정 전 문서화  
**출처**: L1/L3 목표 판단은 정상화되었지만, L루프가 목표에 맞는 도구 예산을 스스로 운영하지 못하는 문제  
**목표**: L1이 이번 L루프 목표에 필요한 예산을 요청하고, 코드는 정책 상한 안에서 승인하는 예산 운영 체계를 만든다.

## 문제

현재 L1은 이번 L루프의 최종 운영 목표와 다음 중간 목표를 비교적 잘 설정한다.

L3도 검색 후보와 실제 읽은 문서를 구분하고,
여러 문서 열람이나 연관성 분석이 부족하면 `partial`로 판정할 수 있게 되었다.

하지만 L루프 실행 예산은 아직 고정값에 가깝다.

예를 들어 사용자가 여러 문서 열람과 문서 간 연관성 분석을 요청해도,
기본 예산이 다음과 같으면 실제로는 문서 1개만 읽고 멈춘다.

```text
max_tool_calls = 2
max_read_doc_calls = 1
search_top_k = 3
```

따라서 시스템은 목표를 알고도 실행 예산 때문에 목표를 달성하지 못한다.

## 핵심 원칙

예산은 LLM이 마음대로 확정하지 않는다.

L1은 예산을 요청한다.
코드는 정책 상한 안에서 승인한다.

```text
L1 = 예산 필요성 제안
CODE:BUDGET_POLICY = 예산 승인/축소/거절
L runtime = 승인된 예산으로 실행
L3 = 승인 예산과 실제 산출을 기준으로 달성 여부 판단
```

이 원칙은 메타정보 관리법과 맞닿아 있다.

- L1의 예산 요청은 혼합 정보다.
- 코드의 승인 예산은 정책에 의해 확정된 운영 정보다.
- 실제 사용량은 절대 정보다.

## L1의 역할

L1은 목표 설정과 함께 이번 L루프에 필요한 예산 힌트를 요청한다.

요청 대상은 다음과 같다.

```text
requested_search_top_k
requested_max_tool_calls
requested_max_read_doc_calls
requested_max_query_attempts
budget_request_reason
```

L1은 예산을 늘리는 이유를 목표와 연결해 설명해야 한다.

예:

```text
사용자가 여러 문서의 연관성 분석을 요구했으므로,
최소 2개 이상의 문서 원문 열람이 필요하다.
따라서 read_doc 예산 3개와 search_top_k 5개를 요청한다.
```

L1은 다음을 하면 안 된다.

- 예산을 최종 승인한 것처럼 말하기
- 후보 문서를 읽은 문서처럼 계산하기
- 무제한 도구 사용을 요구하기
- 사용자 목표를 핑계로 정책 상한을 우회하기

## 코드 예산 정책의 역할

코드는 L1 요청을 그대로 믿지 않는다.

코드는 다음을 기준으로 승인 예산을 만든다.

```text
기본 예산
MVP 상한
사용자 CLI 인자
L1 요청 예산
현재 런타임 정책
```

예:

```text
default max_read_doc_calls = 1
policy ceiling max_read_doc_calls = 3
L1 requested max_read_doc_calls = 5
approved max_read_doc_calls = 3
```

코드는 승인 이유와 축소 이유를 남긴다.

## BudgetPlanFrame 초안

추후 스키마는 다음 형태를 목표로 한다.

```json
{
  "frame_id": "L:budget_plan_frame",
  "turn_id": "turn_dry_001",
  "target_loop": "L",
  "requested_by": "L1",
  "approved_by": "CODE:BUDGET_POLICY",
  "goal_data_id": "L1:goal_frame",
  "requested_budget": {
    "search_top_k": 5,
    "max_tool_calls": 5,
    "max_read_doc_calls": 3,
    "max_query_attempts": 2
  },
  "approved_budget": {
    "search_top_k": 5,
    "max_tool_calls": 4,
    "max_read_doc_calls": 3,
    "max_query_attempts": 2
  },
  "budget_request_reason": "여러 문서 연관성 분석에는 최소 2개 이상의 문서 원문이 필요하다.",
  "approval_reason": "요청은 타당하지만 MVP 정책 상한 안에서 read_doc 3개까지만 승인한다.",
  "policy_limits": {
    "max_search_top_k_ceiling": 8,
    "max_tool_calls_ceiling": 6,
    "max_read_doc_calls_ceiling": 3,
    "max_query_attempts_ceiling": 3
  },
  "source_data_ids": [
    "L1:goal_frame"
  ]
}
```

## Runtime 적용 방향

초기 구현은 다음 순서를 따른다.

1. L1이 목표와 함께 예산 요청을 만든다.
2. 코드가 `BudgetPlanFrame`을 만든다.
3. L루프는 CLI 인자와 정책 상한을 함께 고려해 승인 예산을 확정한다.
4. 승인 예산이 기존 기본 예산보다 크면 L루프 실행에 반영한다.
5. runtime pretty 출력에 요청/승인/실제 사용량을 표시한다.
6. L3는 승인 예산과 실제 산출을 함께 보고 달성 여부를 판단한다.

## MVP 정책 상한 후보

초기 상한은 보수적으로 둔다.

```text
max_search_top_k_ceiling = 6
max_tool_calls_ceiling = 6
max_read_doc_calls_ceiling = 3
max_query_attempts_ceiling = 3
```

이 값은 확정이 아니다.
실제 테스트에서 Qwen 입력 길이, 실행 시간, node_3 brief 크기, node_4 검사 안정성을 보고 조정한다.

## 기대 효과

여러 문서 연관성 분석 요청에서 다음 흐름을 기대한다.

```text
L1:
  여러 문서 원문 비교가 필요하므로 read_doc 2~3개 요청

CODE:
  정책 상한 안에서 read_doc 3개 승인

L runtime:
  search_docs 후 상위 후보 여러 개를 순차적으로 read_doc

L3:
  읽은 문서 수와 후보 수를 구분해 achieved/partial 판단

node_3:
  실제 읽은 문서 N개를 바탕으로 연관성 분석 또는 한계 보고
```

## 미해결 질문

1. 예산 요청을 L1GoalFrame에 직접 넣을지, 별도의 L1BudgetRequestFrame으로 분리할지 결정해야 한다.
2. L2가 예산을 재요청할 권한을 가질지 결정해야 한다.
3. continuation 중 예산을 추가 승인할 수 있는지 결정해야 한다.
4. 여러 문서 읽기에서 어떤 후보를 우선 읽을지 L2가 정할지 코드가 정할지 결정해야 한다.
5. 무작위 열람은 진짜 random 도구가 필요할지, 탐색적 의미 검색으로 충분한지 결정해야 한다.

## 구현 순서 후보

1. L1 예산 요청 필드 스키마 초안 작성
2. CODE BudgetPolicy 승인 함수 작성
3. BudgetPlanFrame 기록
4. L루프에서 승인 예산 적용
5. 여러 read_doc 실행 경로 추가
6. runtime pretty 출력 보강
7. smoke-test 추가
8. Qwen 실테스트

