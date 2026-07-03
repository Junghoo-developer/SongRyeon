# Execution Record: Order Documentation Rule 2026-06-27 001

## 목적

사용자가 "다음부터 모든 발주서는 전부 문서화를 해서 송련이나 외부 에이전트가 추적 가능하게 할 수 있도록 해"라고 지시했다.

이에 따라 발주서가 대화창에만 남지 않도록 유지 규칙을 갱신했다.

## 변경

- `AGENTS.md`의 안전한 작업 규칙에 발주서 문서화 의무를 추가했다.
- `Administrative_Reform_1/01_Maintenance_System/DEVELOPMENT_CYCLE_POLICY_v0.md`의 목표 지정 단계에 발주서 문서화 절차를 추가했다.

## 새 규칙 요약

새 발주서를 제안하거나 확정하면 다음을 수행한다.

```text
1. Administrative_Reform_1/04_Orders/ 에 ORDER 문서로 저장한다.
2. 04_Orders/README.md의 범위, 요약, 링크를 갱신한다.
3. 배경이나 live 테스트 관찰이 중요하면 05_Execution_Records/ 에 실행 기록도 남긴다.
```

## 비고

이번 작업은 운영 규칙 문서화만 수행했다.
코드 변경, schema 변경, runtime 변경, 테스트 실행은 하지 않았다.
