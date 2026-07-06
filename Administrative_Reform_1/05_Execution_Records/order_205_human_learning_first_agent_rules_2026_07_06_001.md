# ORDER_205 Human Learning First Agent Rules - Execution Record

## 실행 일시

2026-07-06

## 목적

R route와 Vessel 그래프 기억이 live 실험 수준까지 올라온 뒤, SongRyeon Core의 다음 운영 기준을 기능 확장 중심에서 인간 학습 중심으로 조정했다.

## 변경 파일

- `AGENTS.md`
- `Administrative_Reform_1/01_Maintenance_System/AGENT_WORKING_RULES_FROM_MAIN_PROJECT.md`
- `Administrative_Reform_1/04_Orders/ORDER_205_HUMAN_LEARNING_FIRST_AGENT_RULES_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`
- `Administrative_Reform_1/05_Execution_Records/README.md`

## 반영한 규칙

- 큰 변경 전에는 쉬운 설명, 목표 좁히기, 위험 설명을 먼저 한다.
- 새 루프, 새 DB, 새 장기기억, 새 자동화는 느린 확장 대상으로 본다.
- 사용자가 현재 구조를 설명할 수 있는지, 테스트가 있는지, 메타정보 경계가 유지되는지, 실패가 정직하게 드러나는지 확인한다.
- 구현 후에는 사용자가 배워야 할 핵심 개념을 3개 이하로 정리한다.
- 사용자가 이해하지 못한 코드는 완료된 작업으로 과장하지 않는다.
- 학습 모드에서는 코드 읽기, 한글 주석, 작은 실험, 회고 문서화를 우선한다.

## 하지 않은 것

- L/R/W loop 변경 없음.
- scheduler, 외부 DB, Vessel schema 변경 없음.
- node prompt 변경 없음.
- 런타임 코드 변경 없음.
- 기존 사용자 변경 revert 없음.

## 검증

문서/운영 규칙 변경만 수행했다.

- `git diff --check`
