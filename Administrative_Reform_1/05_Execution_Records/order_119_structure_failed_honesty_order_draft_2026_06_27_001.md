# Execution Record: ORDER 119 Structure Failed Honesty Order Draft 2026-06-27 001

## 목적

ORDER_118 live 테스트 중 발견된 `structure_failed` fallback 정직성 문제와 node_2 answer-basis selector 실패 진단 부족 문제를 후속 발주서로 문서화했다.

## 관찰한 문제

### node_2 answer-basis selector live 실패

다음 질문들은 node_2 answer-basis selector가 의미 있는 모드를 고르는지 보기 위한 live 테스트였다.

```text
지금 smoke 결과 기준으로 뭐가 통과했어?
방금 smoke-test를 실제로 다시 돌린 거야? 아니면 과거 실행기록을 읽은 거야? 둘을 구분해서 답해줘.
```

두 경우 모두 최종 답변은 생성됐지만, answer-basis frame은 다음 fallback 상태였다.

```text
answer_basis_mode = mixed_or_uncertain
generated_by = CODE:FALLBACK
semantic_judgement_status = failed
basis_reason_codes = ["llm_mode_selection_failed"]
```

따라서 ORDER_118의 live 성공 여부를 판단하려면 failure type, llm call id, validation error 등 진단 정보가 더 필요하다.

### structure_failed fallback 오표현

다음 질문은 상대/해석 허용 모드 테스트였다.

```text
지금 송련의 말하기 모드 설계가 너무 빡빡한지, 아니면 적절한지 의견을 말해줘. 단, 이건 네 해석이라는 점을 밝혀줘.
```

결과는 `structure_failed`, `trace/data: 0 / 0`, `LLM_REPORTER=not_run`이었다.

그런데 fallback answer는 내부 문서를 찾은 것처럼 표현했다.

```text
내부 문서를 찾았어.
검색 결과 payload를 찾지 못해서 근거 문서 요약은 만들지 못했어.
```

검색 payload가 없고 trace/data가 0인 상태에서 이 표현은 정직하지 않다.

## 문서화 변경

- `Administrative_Reform_1/04_Orders/ORDER_119_STRUCTURE_FAILED_HONESTY_AND_ANSWER_BASIS_FAILURE_DIAGNOSTICS_V0.md` 추가
- `Administrative_Reform_1/04_Orders/README.md`의 정식 발주서 범위를 `ORDER_119`까지 확장
- `ORDER_119` 요약과 링크 추가

## 비범위

이번 작업은 문서화만 수행했다.

코드 구현, schema 변경, prompt 변경, smoke/pytest 추가는 하지 않았다.

현재 작업트리에는 ORDER_112와 ORDER_118 관련 구현 변경이 이미 존재하므로, 이번 기록은 ORDER_119 문서화 범위만 다룬다.
