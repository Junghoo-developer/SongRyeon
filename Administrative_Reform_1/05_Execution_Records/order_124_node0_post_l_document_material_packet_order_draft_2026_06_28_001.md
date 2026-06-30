# ORDER_124 Node0 Post-L Document Material Packet 발주서 초안 기록 2026-06-28 001

## 작성 이유

ORDER_123 이후 실제 `read_doc` 수와 node_3 공급 context 수는 분리되었다.
다음 병목은 문서 재료가 여러 frame에 흩어져 있어 node_2/node_3가 문서별 역할을 한눈에 보기 어렵다는 점이다.

사용자와 논의한 결론은 L 이후 node_0이 문서 장부를 정리하는 방향이다.
단, node_0은 의미 요약이나 중요도 판단을 하지 않고 절대정보 좌표와 역할만 정리한다.

## 생성 문서

- `Administrative_Reform_1/04_Orders/ORDER_124_NODE0_POST_L_DOCUMENT_MATERIAL_PACKET_V0.md`

## 상태

- 상태: 발주서 초안 작성
- 구현: 아직 하지 않음
- 테스트: 아직 하지 않음

## 핵심 경계

- node_0은 문서 사서/장부 담당이다.
- node_0은 문서 내용을 요약하지 않는다.
- node_0은 관련성/중요도 의미 판단을 하지 않는다.
- L3 문서 요약은 ORDER_125 후보로 분리한다.
