# ORDER 264: Optional Codex SDK Test Isolation v0

## 1. 배경

ORDER 263 공개 `main` CI에서 pytest가 실패했다. 깨끗한 `requirements-dev.txt` 환경으로
재현한 결과, 주입된 가짜 Codex transport를 검사하는 단위 테스트가 선택 패키지
`openai_codex`를 먼저 import하고 있었다. 로컬 개발 환경에는 패키지가 설치돼 있어
이 의존성 누수가 가려졌다.

## 2. 목표

Codex SDK 실사용 경로는 기존 선택 의존성을 유지하되, 가짜 transport를 주입한 단위
테스트는 `openai_codex` 설치 없이 격리 실행되게 한다.

## 3. 구현 범위

1. `CodexSDKAdapter`에 테스트용 SDK symbol 주입 경계를 추가한다.
2. override가 없으면 기존처럼 실제 `openai_codex` symbol만 불러온다.
3. override에 필수 symbol이 빠지면 명시적으로 실패한다.
4. ORDER 245 테스트가 가짜 symbol과 가짜 factory를 함께 주입하게 한다.

## 4. 금지

- `requirements-dev.txt`에 선택 Codex SDK를 강제로 추가
- 실사용 Codex 인증, sandbox, approval 정책 변경
- import 실패를 조용히 fake 성공으로 바꾸는 fallback
- L/R/노드 실행 의미 변경

## 5. 완료 조건

1. pytest만 설치된 임시 가상환경에서 ORDER 245 테스트가 통과한다.
2. 실제 SDK가 없는 기본 실사용 호출은 기존처럼 설치 안내와 함께 실패한다.
3. 전체 pytest와 smoke-test가 통과한다.
4. GitHub Actions 재실행 결과를 별도로 확인한다.
