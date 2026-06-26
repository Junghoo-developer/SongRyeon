# ORDER 074: Node4 Gatekeeper And Return Loop

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: Node3 뒤에 집중 검사를 수행하고 반려 루프를 돌리려는 설계  
**목표**: Node4를 최종 출력 전 gatekeeper로 만들고, 문제 유형에 따라 0, 1, L, 2, 3으로 되돌리는 루프를 구현한다.

## 배경

Node2와 Node3가 LLM화되면 좋은 발화가 가능해지지만, 동시에 출처 누락, 과장, 정보 등급 오염, boundary 밖 claim이 생길 수 있다.

Node4는 전지적 진실 판정자가 아니다.  
Node4는 출력 직전의 메타정보 위반을 잡고 반려하는 검문소다.

## 범위

1. `Node4GateFrame` 또는 동등한 구조를 만든다.
2. Node4 입력에는 다음을 포함한다.
   - Node3 report draft
   - Node2 boundary
   - used info ids
   - source data ids
   - runtime labels
3. Node4 출력에는 다음을 둔다.
   - `decision`: `approve`, `reject`
   - `reject_reason`
   - `return_target`: `0`, `1`, `L`, `2`, `3`
   - `required_fix`
   - `source_data_ids`
4. 반려 규칙은 다음을 포함한다.
   - 출처 없는 claim
   - 절대/상대/혼합 정보 오염
   - 코드 산출물을 LLM 산출물처럼 표시
   - 도구 점수를 진실 판단처럼 표시
   - 문서 발췌를 요약처럼 표시
   - Node2 boundary 밖 claim
   - 불확실성 누락
5. Node4가 reject하면 return target에 맞춰 한 번 재시도한다.
6. MVP에서는 무한 루프를 금지하고 최대 재시도 횟수를 둔다.

## 원칙

1. Node4는 최종 출력 전 검문소다.
2. Node4의 판단도 LLM을 쓰면 상대/혼합 정보다.
3. 반려 이유는 source id를 가져야 한다.
4. 통과 실패 시 정직하게 실패를 보고한다.

## 완료 기준

1. Node4 approve/reject가 trace/data에 기록된다.
2. reject 시 return target이 기록된다.
3. 최소한 Node3 재작성 루프가 한 번 동작한다.
4. 실패 시 사용자에게 어떤 기준에서 막혔는지 보인다.
5. smoke test가 approve와 reject 케이스를 모두 검증한다.

