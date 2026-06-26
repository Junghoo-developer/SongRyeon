# l1 internal macro goal 2026-06-24 001

## 배경

사용자는 L1의 거시목표가 사용자의 목표를 그대로 나타내는 것이 아니라,
에이전트 내부의 자체 운영 목표여야 한다고 정정했다.

장기적으로 L루프의 거시목표는 "사용자가 원하는 것"이 아니라,
SongRyeon이 내부적으로 지켜야 하는 근거 경계, 문서 접근 규율, 메타정보 무결성 방향을 표현해야 한다.

## 구현

`l1_goal_setter_v0.md`를 수정했다.

- `macro_goal`은 SongRyeon의 내부 운영 목표로 정의한다.
- `micro_goal`은 그 내부 목표 아래에서 다음에 수행할 구체적인 L루프 단계를 나타낸다.
- 사용자 요청 조건은 주로 `micro_goal`과 `micro_goal_reason`에 반영한다.
- 여러 문서, 무작위 열람, 비교, 연관성 분석, 특정 문서명 같은 조건은 미시 목표의 운영 조건으로 다룬다.

`run_l1_goal_setter` 입력 payload에는 `user_query`를 추가했다.
이전에는 L1이 trace ID 목록만 받아서 사용자의 실제 요청 조건을 알기 어려웠다.

## 기본 목표명

규칙 기반 fallback과 fake adapter의 기본 L1 목표를 다음처럼 바꿨다.

```text
macro_goal = maintain_l_loop_evidence_boundary
micro_goal = prepare_request_conditioned_document_lookup
```

## 의미

이 변경은 L1이 사용자 목표를 무시한다는 뜻이 아니다.

L1은 사용자 요청을 보고,
그 요청을 L루프가 내부적으로 안전하게 처리하기 위한 운영 목표로 번역한다.

거시목표는 내부 원칙을 잡고,
미시목표는 이번 요청에서 다음 도구 단계가 무엇을 만족해야 하는지 좁힌다.

## 검증

- `python -m compileall songryeon_core`
- `python main.py smoke-test`

두 검증을 통과했다.

