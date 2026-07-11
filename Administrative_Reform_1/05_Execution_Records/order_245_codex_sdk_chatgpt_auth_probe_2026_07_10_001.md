# ORDER 245 실행 기록

- 날짜: 2026-07-10
- 결과: ChatGPT Pro 인증 기반 Codex SDK probe 성공
- 발주서: `ORDER_245_CODEX_SDK_CHATGPT_AUTH_PROBE_V0.md`

## 환경

- Python SDK: `openai-codex 0.1.0b3`
- pinned CLI: `openai-codex-cli-bin 0.137.0a4`
- auth file: 존재 여부만 확인, 내용 미열람
- account response: `auth_type=chatgpt`, `plan_type=pro`
- API key forwarding: false

## 구현

- `CodexSDKAdapter` 기초와 `codex-sdk-ping` 명령을 추가했다.
- SDK 자식 app-server를 띄울 때 API key/token/password/secret/credential 환경변수와
  현재 Codex 앱 내부 환경표지를 제거하고, 부모 환경은 직후 복구한다.
- 빈 임시 폴더, ephemeral thread, read-only sandbox, deny-all approval을 강제했다.
- node 출력은 `payload_json` transport wrapper schema로 받아 기존 JSON object로 복원한다.
- command/file/MCP/web/image 등 tool item이 하나라도 기록되면 결과를 채택하지 않는다.

## 실제 probe

- 기본 모델 시도: `gpt-5.6-sol`, pinned CLI 버전 부족으로 실패
- 명시 모델: `gpt-5.4`
- status: ok
- response: `ping=pong`, `auth_surface=chatgpt_subscription`
- tool activity: 0
- input tokens: 12,804
- cached input tokens: 2,432
- output tokens: 40
- reasoning output tokens: 9
- total tokens: 12,844

## 자동 검증

- `python -m compileall songryeon_core main.py`: 통과
- ORDER 245 pytest: `3 passed`
- `git diff --check`: 통과

## 판단

API 잔액 없이 ChatGPT 구독 인증으로 송련이 공식 Codex SDK를 호출할 수 있음이
확인됐다. 그러나 agent 기본 문맥의 token overhead가 크므로 all-node 연결은
비교용 짧은 수동 한 턴으로 제한하고 자동 기본 경로로 열지 않는다.
