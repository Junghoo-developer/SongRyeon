# l_loop budget plan documentation 2026-06-24 001

## 배경

L1은 이번 L루프의 목표를 더 구체적으로 세우기 시작했다.
L3도 검색 후보와 실제 읽은 문서를 구분해 partial 판정을 내릴 수 있게 되었다.

따라서 다음 병목은 목표 판단이 아니라 예산 운영이다.

여러 문서 연관성 분석처럼 최소 2개 이상의 문서 원문이 필요한 요청도,
기본 예산이 `max_read_doc_calls=1`이면 구조적으로 달성할 수 없다.

## 결정

코드 구현 전에 `ORDER_090_L_LOOP_BUDGET_PLAN_V0.md`를 작성했다.

핵심 원칙은 다음과 같다.

```text
L1 = 예산 필요성 요청
CODE:BUDGET_POLICY = 정책 상한 안에서 승인/축소
L runtime = 승인된 예산으로 실행
L3 = 승인 예산과 실제 산출을 보고 달성 여부 판단
```

사용자는 예산 요청 주체를 L1로 두는 방향에 동의했다.

## 구현 전 주의

예산 요청은 LLM이 만든 혼합 정보다.
승인 예산과 실제 사용량은 코드/런타임이 만든 운영 정보다.

따라서 이후 구현에서는 요청 예산과 승인 예산을 분리해야 한다.

## 다음 구현 후보

1. L1 예산 요청 필드 또는 별도 budget request frame 설계
2. BudgetPlanFrame 스키마 작성
3. 코드 BudgetPolicy 승인 함수 작성
4. L루프에 승인 예산 적용
5. runtime pretty 출력 보강
6. 여러 문서 read_doc 실행 경로 추가
7. smoke-test와 Qwen 실테스트

