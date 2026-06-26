# ORDER 058: Memory Packet Relevance Scoring

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: 0이 다음 노드에 넘길 기억 선별 능력 필요  
**목표**: 0이 memory packet에 넣을 기억 조각을 관련도 기준으로 고르게 한다.

## 배경

현재 0은 trace와 capsule을 바탕으로 memory packet을 만든다.  
하지만 LLM 노드가 들어오면 모든 기억을 넣는 방식은 context를 낭비하고, 중요한 근거를 흐리게 만들 수 있다.

## 범위

1. `MemoryRelevanceFrame` 또는 memory item의 relevance 필드를 만든다.
2. 관련도는 target node, route reason, user input, current trace를 기준으로 계산한다.
3. 초기에는 규칙 기반 scoring을 쓰고, 나중에 LLM scoring을 선택적으로 붙인다.
4. 낮은 관련도 기억은 제외하거나 summary로 낮춘다.
5. 제외한 기억도 필요하면 replay에서 확인할 수 있게 한다.

## 원칙

1. 관련도 점수는 진실성 점수가 아니다.
2. 기억 선별은 출처를 보존한 채 이루어져야 한다.
3. LLM scoring 실패 시 규칙 기반 scoring으로 fallback한다.

## 완료 기준

1. memory packet item에 relevance 정보가 들어간다.
2. target별로 선택된 memory item 수를 제한할 수 있다.
3. 제외된 후보 수가 기록된다.
4. smoke test가 relevance 필드와 source ID를 확인한다.
