# TMP ORDER 011: Failure Signal

**상태**: 임시 발주서  
**목표**: 기억 부족, 스키마 실패, 도구 실패 같은 실패 신호 구조를 정의한다.  
**실행 권한**: 없음.

## 배경

0이 접근할 수 없는 기억이 생기면 지어내면 안 된다. 0은 부족 신호를 낼 수 있어야 하고, 1은 그 신호를 라우팅 이유로 사용할 수 있어야 한다.

## 만들 것

```text
FailureSignal
- raised_by
- type
- severity
- reason
- evidence_trace_ids
- recommended_route
```

## type 후보

- `memory_insufficient`
- `schema_failed`
- `tool_failed`
- `route_failed`
- `metainfo_boundary_failed`
- `unknown_state`

## 역할 분담

```text
Trace 통합 추적기:
스키마 위반, 도구 오류, 노드 입출력 누락 같은 기계적 실패를 잡는다.

0:
기억 부족, 맥락 손실, 이전 턴 연결 실패를 보고한다.

2:
출처 없는 상대/혼합 정보와 환각 위험 정보를 걸러낸다.

1:
실패 신호를 보고 다음 라우팅을 결정한다.
```

## 완료 기준

- 실패 신호의 기본 형식이 있다.
- 0의 기억 부족 신호가 포함되어 있다.
- 1이 실패 신호를 라우팅에 쓸 수 있다.

## 제외

- C루프 구현.
- 자동 복구 정책.
