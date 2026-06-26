# ORDER 069: Node1 LLM Router

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: Node1의 라우팅 이유를 코드가 대신 쓰는 문제  
**목표**: Node1을 실제 LLM 라우터로 배선하고, 코드는 route 검증과 fallback만 담당하게 한다.

## 배경

기획상 Node1은 최근 대화, 사용자 입력, 0의 보고를 보고 다음 route를 판단하는 LLM 노드다.  
현재 구현은 키워드와 정책 플래그로 `L` 또는 `2`를 고르는 코드 스텁이다.

이 상태는 정직하게 표시되어 있지만, MVP가 대화형 에이전트가 되려면 Node1의 의미 판단은 LLM이 수행해야 한다.

## 범위

1. `RoutingDecisionFrame`을 LLM router용으로 정리한다.
2. Node1 prompt를 새 메타정보 관리법에 맞게 확장한다.
3. 입력에는 다음을 포함한다.
   - 사용자 입력 원문
   - Node0 memory packet
   - 최근 trace/data 요약
   - 사용 가능한 route 목록
   - 각 route의 의미와 한계
4. LLM 출력에는 최소한 다음을 둔다.
   - `route`
   - `route_reason`
   - `route_confidence`
   - `source_data_ids`
   - `needs_more_memory`
5. 코드는 route enum, source id 존재 여부, schema만 검증한다.
6. LLM 실패 시 코드 fallback을 쓰되 `route_source=CODE:FALLBACK`으로 표시한다.

## 원칙

1. LLM이 쓴 라우팅 이유는 상대정보 또는 혼합정보다.
2. 코드는 라우팅 이유를 새로 쓰지 않는다.
3. 강제 L 라우팅은 사용자 입력으로 위장하지 않고 정책 플래그로만 기록한다.
4. Node1은 자신이 모르면 0에게 기억 부족을 요청할 수 있어야 한다.

## 완료 기준

1. qwen-turn에서 Node1 LLM call이 trace/data에 기록된다.
2. LLM router가 `L` 또는 `2`를 선택한다.
3. route reason은 `llm_call:node_1:*`와 연결된다.
4. fallback 발생 시 사용자에게 fallback이 보인다.
5. smoke test가 LLM route와 fallback route를 모두 검증한다.

