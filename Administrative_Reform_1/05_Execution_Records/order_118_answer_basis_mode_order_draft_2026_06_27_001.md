# Execution Record: ORDER 118 Answer Basis Mode Order Draft 2026-06-27 001

## 목적

node_2가 node_3에게 답변 근거 말하기 모드를 전달하는 후속 발주서를 문서화했다.

## 배경

최근 대화에서 사용자는 node_2의 말하기 모드를 7개 세부 모드가 아니라 3개 상위 모드로 제한하겠다고 결재했다.

결재된 3개 모드:

```text
absolute_first
relative_allowed
mixed_or_uncertain
```

이 구조는 송련의 행동 방식을 절대정보, 상대정보, 혼합정보 분류 원칙과 맞추기 위한 것이다.

## 변경

- `Administrative_Reform_1/04_Orders/ORDER_118_NODE2_ANSWER_BASIS_MODE_FRAME_V0.md` 추가
- `Administrative_Reform_1/04_Orders/README.md`의 정식 발주서 범위를 `ORDER_118`까지 확장
- `ORDER_118` 요약과 링크 추가

## 비고

이번 작업은 문서화만 수행했다.
코드 구현, schema 변경, prompt 변경, smoke/pytest 추가는 하지 않았다.

현재 작업트리에는 별도 진행 중인 ORDER_112 구현 변경이 존재하므로, 이번 기록은 ORDER_118 문서화 범위만 다룬다.
