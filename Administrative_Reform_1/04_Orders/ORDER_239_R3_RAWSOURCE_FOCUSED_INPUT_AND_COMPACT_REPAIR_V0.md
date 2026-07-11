# ORDER 239: R3 RawSource Focused Input And Compact Repair v0

## 상태

- Status: implemented and regression verified; follow-up completed through ORDER_242
- Date: 2026-07-10
- Scope: R3 RawSource LLM view / repair payload size / exact-question sufficiency

## 배경

ORDER 238 재시험에서 R3 input은 10,117자였다. 원문은 3,722자였고,
나머지 약 6,400자는 R1/R2 장부, 정책 설명, 이전 단계 좌표였다.
Qwen3 14B는 좁은 상태표를 받았는데도 RawSource를 `low_summary`로 오인했다.
이는 규칙 부족보다 작은 모델의 context 안에서 원문과 부가 장부가 경쟁하는
입력 집중도 문제로 판단한다.

## 목표

- 자식이 없는 원문 보유 RawSource 단계에서는 R3에게 원문과 최소 계약만 준다.
- full R1/R2/step provenance는 DataStore와 TraceStore에 그대로 보존한다.
- repair는 failed status, 구조 사실, R1 목표, 좁은 enum table만 받는다.
- R3는 사용자 질문을 더 강한 구현 증명 요구로 바꾸지 않고 정확한 질문 기준으로 판단한다.

## 구현 경계

- code는 어떤 문장이 중요한지 요약하지 않는다.
- 원문 text는 자르지 않는다.
- code는 의미상 충분/불충분을 정하지 않는다.
- R3 LLM view에서 생략된 provenance는 삭제된 것이 아니다.
- 이전 단계 기억은 경로 상태와 남은 예산만 짧게 유지한다.

## 하지 않는 것

- 키워드 기반 문서 성공 판정을 추가하지 않는다.
- raw를 읽었다는 이유로 `sufficient`를 강제하지 않는다.
- validator나 node_4 guard를 약화하지 않는다.
- Neo4j 원본, trace, data record를 삭제하지 않는다.

## 완료 조건

- RawSource R3 payload에 원문 전문이 유지된다.
- RawSource R3 payload에서 full R2 provenance와 긴 step ID 목록이 빠진다.
- payload가 기존 10,117자보다 실질적으로 작아진다.
- repair payload가 원문과 전체 provenance를 재복사하지 않는다.
- pytest, quick-smoke, 완전 통합 qwen-turn을 실행한다.
