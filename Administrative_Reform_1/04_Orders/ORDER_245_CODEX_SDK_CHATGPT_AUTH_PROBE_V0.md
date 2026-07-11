# ORDER 245: Codex SDK ChatGPT Auth Probe v0

## 상태

- Status: implemented and verified
- Date: 2026-07-10
- Scope: official Codex Python SDK / ChatGPT subscription auth / read-only probe

## 배경

ORDER 244의 OpenAI Responses API adapter는 구현과 회귀 검증을 통과했지만,
실제 API 계정은 `insufficient_quota`로 모델 응답을 만들지 못했다. OpenAI 공식
Codex SDK와 `codex exec`는 저장된 Codex CLI 인증을 재사용할 수 있고, Codex는
ChatGPT 로그인 기반 subscription access와 API-key 기반 usage access를 구분한다.

## 목표

- 공식 Python `openai-codex` SDK를 별도 optional dependency로 설치한다.
- API 키 환경 변수를 probe 자식 실행에서 제거한다.
- ChatGPT/Codex 저장 인증만 사용해 모델 호출 1회를 시도한다.
- 빈 임시 작업 폴더와 read-only sandbox를 사용한다.
- 인증 문자열이나 `auth.json` 내용을 읽거나 trace/data에 저장하지 않는다.
- 성공/실패, 모델 응답 존재 여부, usage count만 절대정보로 보고한다.

## probe 명령

- `codex-sdk-ping`

## 완료 조건

- `OPENAI_API_KEY`와 `CODEX_API_KEY`가 probe에 전달되지 않는다.
- workspace write/full access를 사용하지 않는다.
- 응답은 JSON object로 제한하고 schema/parse 결과를 표시한다.
- ChatGPT 인증이 없으면 실패를 API quota 문제로 위장하지 않는다.
- 실제 probe 결과를 실행 기록에 남긴다.
- 좁은 pytest와 기존 회귀 기준선을 통과한다.

## 하지 않는 것

- Codex 앱 토큰, `auth.json`, OS credential 원문 열람/복사
- API key fallback
- 현재 Codex 앱 채팅이나 현재 thread 재사용
- workspace 파일 쓰기, shell 명령 권한, full-access sandbox
- probe 성공 전 송련 전체 LLM node 연결
- 기존 OpenAI/Qwen adapter 제거

## 후속 조건

probe가 ChatGPT subscription auth로 성공한 경우에만
`ORDER_246_CODEX_SDK_ALL_NODES_COMPARISON_ADAPTER_V0`를 작성하고 구현한다.

## 2026-07-10 결과

- `openai-codex==0.1.0b3`와 pinned CLI `0.137.0a4`를 설치했다.
- API key를 제거한 account probe에서 `auth_type=chatgpt`, `plan_type=pro`를 확인했다.
- SDK 기본 모델은 최신 앱 모델 `gpt-5.6-sol`을 고르려 했지만 pinned CLI가
  더 오래되어 거절됐다.
- 공식 SDK 예시 모델 `gpt-5.4`를 명시한 `codex-sdk-ping`은 성공했다.
- read-only, deny-all, tool activity 0, API key forwarding false를 확인했다.
- ping usage는 input 12,804 / cached input 2,432 / output 40 / total 12,844였다.
