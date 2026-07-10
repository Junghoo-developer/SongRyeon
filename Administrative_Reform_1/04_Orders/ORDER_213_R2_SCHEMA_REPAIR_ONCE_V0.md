# ORDER_213_R2_SCHEMA_REPAIR_ONCE_V0

## 상태

즉시 구현 승인.

## 배경

ORDER_210 이후 live R route 테스트에서 node_1은 R을 잘 선택했지만,
Vessel R traversal이 R2 단계에서 자주 닫혔다.

확인된 실패 예시는 다음과 같다.

```text
failure_stage: R2:step_0004
failure_type: schema_failed
failure_reason: R2 selected_surface_ref must be in available_surface_refs
```

별도 단독 traverse 테스트에서는 다음 실패도 확인됐다.

```text
failure_reason: R2 expected_information_granularity is invalid
```

감사 결론은 Neo4j read 실패가 아니라,
R2가 의미 선택과 임시 번호표 복사를 동시에 하다가
`surface_###`, `node_###`, granularity enum 복사 계약에서 미끄러진다는 것이다.

## 목표

R2 schema copy-contract 실패에 한해서 LLM repair를 최대 1회 허용한다.

## 구현 범위

1. R2 최초 호출이 `schema_failed`이고 실패 이유가 copy-contract 계열이면 repair 입력을 만든다.
   - `selected_surface_ref`
   - `selected_node_ref`
   - `selected_surface_id`
   - `selected_graph_node_id`
   - `expected_information_granularity`

2. repair 입력에는 다음을 포함한다.
   - 실패 reason
   - 실패 output의 핵심 field
   - 허용된 surface ref 목록
   - surface별 허용 node ref 목록
   - 허용된 granularity enum 목록

3. repair 호출은 최대 1회만 한다.
   - 최초 R2 호출 1회
   - repair R2 호출 최대 1회
   - 총 R2 호출 최대 2회

4. repair 후에도 실패하면 기존처럼 `R2:step_N schema_failed`로 닫는다.

## 금지

- validator를 약화하지 않는다.
- code가 대신 graph node를 선택하지 않는다.
- 유사도, 키워드, 이름 매칭 휴리스틱 fallback을 넣지 않는다.
- R traversal 예산, route 정책, node_3 답변 정책을 바꾸지 않는다.
- R2 schema 실패를 성공처럼 감추지 않는다.

## 완료 조건

1. one-step R2 copy-contract 실패가 repair 1회 후 통과하는 테스트가 있다.
2. multi-step traverse R2 copy-contract 실패가 repair 1회 후 계속 진행되는 테스트가 있다.
3. 기존 R2 validator 실패 테스트는 여전히 실패한다.
4. compileall / 관련 pytest / git diff check가 통과한다.
