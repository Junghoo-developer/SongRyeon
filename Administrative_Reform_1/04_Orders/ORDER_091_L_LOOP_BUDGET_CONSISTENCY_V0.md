# ORDER 091: L Loop Budget Consistency v0

## 목적

`ORDER_090_L_LOOP_BUDGET_PLAN_V0.md` 구현 이후 발견된 예산 정합성 문제를 고친다.

## 발견된 문제

L1이 여러 문서의 관계 분석을 위해 `read_doc=2`를 요청했고,
CODE:BUDGET_POLICY도 `read_doc=2`를 승인했다.

그러나 총 도구 호출 예산은 `tool_calls=2`로 남았다.

L루프에서 기본적으로 필요한 도구 호출은 다음과 같다.

```text
search_docs 1회
read_doc N회
```

따라서 `read_doc=2`를 실제로 실행하려면 최소 도구 호출 수는 다음과 같다.

```text
minimum_tool_calls = 1 + approved_max_read_doc_calls
```

기존 정책은 각 예산 항목을 따로 승인했기 때문에 아래와 같은 모순을 만들 수 있었다.

```text
approved_max_read_doc_calls = 2
approved_max_tool_calls = 2
```

이 경우 실제 실행은 `search_docs` 1회와 `read_doc` 1회에서 멈춘다.

## 정책

L1이 기본값보다 많은 `read_doc` 예산을 요청하여 승인된 경우,
CODE:BUDGET_POLICY는 총 tool call 예산을 다음 조건에 맞게 보정한다.

```text
approved_max_tool_calls >= 1 + approved_max_read_doc_calls
```

단, 정책 상한은 넘기지 않는다.

```text
approved_max_tool_calls <= max_tool_calls_ceiling
```

## 주의

이 보정은 L1이 `read_doc` 예산을 기본값보다 늘려달라고 요청한 경우에만 적용한다.

이유는 `max_tool_calls=1` 같은 명시적 제한 테스트나 개발자 제한 실행을 실수로 풀어버리지 않기 위해서다.

## Runtime 표시

보정이 일어난 경우 `L:budget_plan_frame.approval_reason`에 다음 라벨을 포함한다.

```text
CODE_STATUS:tool_calls_aligned_with_read_doc_budget
```

## 검증 기준

다음 조건을 smoke-test로 확인한다.

```text
requested_max_tool_calls = 2
requested_max_read_doc_calls = 2
approved_max_tool_calls = 3
approved_max_read_doc_calls = 2
```

또한 첫 번째 `tool_budget` frame도 보정된 값을 실제 실행 예산으로 사용해야 한다.

