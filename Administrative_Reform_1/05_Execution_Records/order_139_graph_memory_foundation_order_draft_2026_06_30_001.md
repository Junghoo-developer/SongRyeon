# order_139_graph_memory_foundation_order_draft_2026_06_30_001

## 1. 작업 요약

심야정부 graph memory와 R루프 graph guide 구상을 ORDER_139 발주서로 문서화했다.

이번 기록은 구현 기록이 아니다.

## 2. 작성한 발주서

- `Administrative_Reform_1/04_Orders/ORDER_139_GRAPH_MEMORY_FOUNDATION_AND_RLOOP_GUIDE_PACKET_V0.md`

## 3. 발주서 핵심

- 기존 TurnStateCapsule/TraceStore/DataStore를 우선 사용한다.
- raw capsule graph node와 CoreEgo 시간축 연결을 만든다.
- summary depth/source count 계산 인프라를 둔다.
- RLoopGraphGuidePacket을 code-generated absolute/status 중심으로 생성한다.
- LLM traversal hint, 의미축 CoreEgo, 실제 R루프 route, 외부 DB 연결은 열지 않는다.

## 4. 검증

문서 작성만 수행했다.

`git diff --check`만 확인한다.
