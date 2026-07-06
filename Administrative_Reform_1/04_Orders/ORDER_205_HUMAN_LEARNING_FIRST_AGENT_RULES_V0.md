# ORDER_205_HUMAN_LEARNING_FIRST_AGENT_RULES_V0

## 상태

구현 완료.

## 배경

SongRyeon Core는 R route, Vessel/Neo4j 그래프 기억, L/R/2 선택 경계까지 빠르게 확장되었다.
이제 다음 위험은 기능 부족보다 사용자가 구조를 이해하지 못한 채 확장 속도에 끌려가는 것이다.

외부 에이전트 운용 사례를 참고하면, 좋은 에이전트 지침은 작업 규칙을 프로젝트 안에 명시하고, 계획과 검증을 남기며, 사용자의 이해 가능성을 유지해야 한다.
이번 발주서는 그 방향을 SongRyeon Core의 운영 규칙으로 고정한다.

참고한 외부 지침 계열:

- OpenAI Codex `AGENTS.md` guide: https://developers.openai.com/codex/guides/agents-md
- AGENTS.md project: https://agents.md/
- Claude Code memory / instruction docs: https://code.claude.com/docs/en/memory
- Cursor agent best practices: https://cursor.com/blog/agent-best-practices
- Nx effective AI coding guide: https://nx.dev/blog/practical-guide-effective-ai-coding
- Google Colab Learn Mode announcement: https://blog.google/innovation-and-ai/technology/developers-tools/colab-updates/
- VS Code custom instructions: https://code.visualstudio.com/docs/agent-customization/custom-instructions

## 목표

루트 `AGENTS.md`와 유지 체계 문서에 인간 중심 학습 루프를 추가한다.
앞으로 Codex와 외부 협업자는 기능 확장보다 사용자의 이해, 검수 가능성, 느린 확장 게이트를 우선해야 한다.

## 구현 범위

1. `AGENTS.md`에 `인간 중심 학습 루프` 항목을 추가한다.
2. `Administrative_Reform_1/01_Maintenance_System/AGENT_WORKING_RULES_FROM_MAIN_PROJECT.md`에도 같은 취지의 유지 규칙을 보존한다.
3. `04_Orders/README.md`와 `05_Execution_Records/README.md`에 추적 가능한 항목을 추가한다.
4. 실행 기록을 작성한다.

## 원칙

- 사용자가 이해하지 못한 코드는 완료된 작업으로 과장하지 않는다.
- 테스트 통과는 필요조건이지 충분조건이 아니다.
- 새 루프, 새 DB, 새 장기기억, 새 자동화는 느린 확장 대상으로 본다.
- 큰 변경 전에는 초등학생도 이해할 수 있는 수준의 설명, 목표 좁히기, 위험 설명을 먼저 한다.
- 구현 후에는 사용자가 배워야 할 핵심 개념을 3개 이하로 정리한다.
- 학습 모드에서는 새 기능보다 코드 읽기, 한글 주석, 작은 실험, 회고 문서화를 우선한다.

## 금지

- 기능 확장을 이번 발주에 끼워 넣지 않는다.
- L/R/W loop, scheduler, 외부 DB, Vessel schema, node prompt를 변경하지 않는다.
- 사용자의 기존 작업 변경을 되돌리지 않는다.

## 완료 조건

- `AGENTS.md`에 인간 중심 학습 루프가 들어간다.
- 유지 체계 문서에도 같은 운영 원칙이 보존된다.
- README와 실행 기록으로 추적 가능하다.
- 문서 변경이므로 코드 테스트 대신 `git diff --check`로 공백/패치 오류를 확인한다.
