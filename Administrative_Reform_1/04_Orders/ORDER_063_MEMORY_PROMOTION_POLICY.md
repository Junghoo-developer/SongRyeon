# ORDER 063: Memory Promotion Policy

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: 임시 trace와 문서 검색 결과를 장기기억으로 승격할 기준 필요  
**목표**: 어떤 정보를 임시 기록에서 장기기억 후보로 올릴지 결정하는 승격 정책을 만든다.

## 배경

모든 trace를 저장하는 것은 좋지만, 모든 trace를 같은 무게의 기억으로 다루면 0이 읽어야 할 양이 폭발한다.  
따라서 반복 사용, 사용자 확인, 공식 문서, 성공한 턴의 근거처럼 가치가 높은 정보만 장기기억 후보로 승격해야 한다.

## 범위

1. `MemoryPromotionCandidate`와 `MemoryPromotionDecision` 또는 동등한 구조를 만든다.
2. 승격 후보의 출처는 trace, data, document chunk, execution record를 우선 지원한다.
3. 승격 판단 상태는 `accepted`, `deferred`, `rejected`를 둔다.
4. 승격 이유에는 source ID, 판단 기준, 위험 요소를 기록한다.
5. LLM 단독 판단만으로는 승격 확정이 되지 않게 한다.

## 원칙

1. 장기기억 승격은 편의가 아니라 통제 대상이다.
2. 출처 없는 자연어 요약은 승격할 수 없다.
3. 잘못 승격된 기억은 나중에 보류 또는 폐기될 수 있어야 한다.

## 완료 기준

1. accepted/deferred/rejected 예시가 각각 저장된다.
2. 사용자 확인 정보와 tool result 정보가 서로 다른 기준으로 평가된다.
3. 승격된 기억 후보에서 원본 trace/data/doc으로 이동할 수 있다.
4. `python main.py smoke-test`가 통과한다.
