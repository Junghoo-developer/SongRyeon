# ORDER 246: Codex SDK All-Nodes Comparison Adapter v0

## 상태

- Status: implemented and verified
- Date: 2026-07-10
- Scope: ChatGPT-auth Codex SDK / all-node injection / one-turn comparison

## 배경

ORDER 245에서 API key를 전달하지 않고 ChatGPT Pro 인증으로 `gpt-5.4` SDK ping이
성공했다. 같은 모델 adapter를 송련의 기존 노드 경계에 주입해 Qwen과 구조 효과를
비교할 수 있다. 단, 빈 ping도 12K 이상의 입력 token을 사용했으므로 자동 기본
경로나 반복 대화가 아니라 명시 수동 실험으로만 연다.

## 목표

- `codex-sdk-turn`으로 한 턴 전체 LLM node 경로를 실행한다.
- 필요할 때만 `codex-sdk-chat`을 명시 실행하되 기본 명령으로 만들지 않는다.
- node_1, memory selector, L1/L2/L3, node_2/3/4와 선택된 R adapter가 동일한
  `CodexSDKAdapter` 인스턴스를 공유한다.
- 각 node 호출은 서로 다른 ephemeral Codex thread를 사용한다.
- app-server 프로세스는 한 턴 동안 공유하고 종료 시 반드시 닫는다.
- runtime에 ChatGPT auth type, plan type, attempted/completed/accepted turn count와
  token usage, tool activity count를 표시한다.

## 안전 경계

- API key fallback 없음
- ChatGPT가 아닌 auth type이면 실행 중단
- empty temporary cwd / read-only / deny-all
- tool activity가 있으면 해당 node response 반려
- Qwen/OpenAI 기존 명령과 완전 분리
- 자동 retry, background loop, default route 교체 없음

## 완료 조건

- fake SDK all-node injection pytest 통과
- key/password가 SDK child 환경으로 넘어가지 않음
- 짧은 실제 `codex-sdk-turn` 한 번 실행
- 실제 node call count와 token usage 보고
- compileall, 전체 pytest, smoke-test 통과

## 2026-07-10 결과

- 실제 `codex-sdk-turn`이 ChatGPT Pro 인증으로 완료됐다.
- route는 `L -> 2`, Codex turn은 10회 모두 completed/accepted였다.
- node_4는 pass, SDK tool activity는 0이었다.
- 실행 시간은 약 138.5초, total token은 206,074였다.
- 따라서 기능은 검증됐지만 기본 runtime이 아니라 수동 대형 모델 비교/검수
  경로로 유지한다.
