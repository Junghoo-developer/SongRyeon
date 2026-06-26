# ORDER 076: Route2 Handoff Integrity

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: `1 route=2` 이후 2가 전체 장부를 직접 뒤지는 구조가 3의 입력 혼란을 만든 문제  
**목표**: 1이 2로 라우팅한 순간 0과 코드가 조건부 handoff 무결성 검사를 수행하고, 2가 읽을 입력 범위를 명확하게 제한한다.

## 배경

현재 2는 `Node2InputFrame`에 들어온 trace/data 목록을 기준으로 boundary를 만든다.  
하지만 이 방식은 “2가 읽어도 되는 장부 목록”은 만들지만, route=2 진입이 정상인지, L루프 산출물이 충분한지, 3에게 넘길 재료가 있는지까지 명확하게 보장하지 못한다.

초기 설계에서 0은 라우팅 대상마다 다른 방식으로 기억을 공급한다.  
따라서 `1 route=2`가 발생했을 때는 0의 `final_trace_for_2` 모드와 코드 무결성 검사가 함께 발동하는 편이 더 자연스럽다.

## 범위

1. `route=2` 직후 조건부 handoff 검사 단계를 만든다.
2. 검사 주체를 분리한다.
   - 0: 이번 턴 흐름과 trace를 2가 보기 좋게 압축한다.
   - 코드: 존재 여부, schema 통과 여부, 필수 data_id 연결 여부 같은 절대정보를 검사한다.
3. `Node2HandoffFrame` 또는 동등한 payload를 만든다.
4. `Node2HandoffFrame`에는 다음을 포함한다.
   - 사용자 질문 원문
   - 주요 노드 동선
   - route 결정 목록
   - L루프를 탔다면 L1/L2/L3 산출물 존재 여부
   - tool_result/read_doc 존재 여부
   - 2가 읽어야 할 source data 범위
   - 3에게 줄 브리프 생성 가능 여부
   - 누락/불충분 신호
5. `Node2InputFrame`은 유지하되, 2의 주 입력을 `Node2HandoffFrame`으로 승격한다.

## 원칙

1. 코드는 절대정보만 검사한다.
2. 코드는 LLM의 의미 판단을 대신 쓰지 않는다.
3. 0은 라우팅 대상별 맞춤형 정보 공급관이다.
4. `route=2`는 “최종 보고 가능 상태인지 검사하라”는 조건 발동 신호다.
5. 2가 전체 DataStore를 자유 탐색하는 구조는 줄인다.

## 완료 기준

1. `route=2`마다 handoff integrity frame이 생성된다.
2. 필수 data_id가 없으면 handoff status가 `blocked` 또는 `insufficient`로 기록된다.
3. L루프를 탔는데 L3 산출물이 없으면 2로 정상 진입하지 않은 것으로 표시된다.
4. read_doc 결과가 있으면 handoff에 “문서 추출 있음”이 절대정보로 기록된다.
5. pretty runtime에서 `route=2 handoff` 상태가 보인다.
