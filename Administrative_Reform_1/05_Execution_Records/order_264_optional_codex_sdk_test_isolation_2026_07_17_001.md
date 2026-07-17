# ORDER 264 Optional Codex SDK Test Isolation 실행 기록

## 1. 실행 일자

- 2026-07-17

## 2. 발견 경로

- ORDER 263을 공개 `main`에 반영한 뒤 GitHub Actions run `29560487013`의
  `Run pytest` 단계가 실패했다.
- 로컬 기본 환경의 전체 pytest는 통과했으므로, `requirements-dev.txt`만 설치한
  임시 가상환경을 만들어 CI 조건을 재현했다.
- 재현 결과 `test_order_245_codex_sdk_chatgpt_auth_probe.py`가 주입된 가짜 Codex
  transport를 검사하면서도 선택 패키지 `openai_codex`의 symbol을 먼저 import했다.
- 로컬에는 해당 선택 패키지가 설치돼 있어 의존성 누수가 가려져 있었다.

## 3. 원인 판정

이 실패는 SongRyeon Core의 L/R/runtime 동작 실패가 아니라 테스트 격리 실패다.
Codex SDK 경로는 선택 기능인데, 그 계약을 검사하는 단위 테스트가 선택 패키지가
없는 기본 CI에서도 실행 가능하도록 완전히 격리되지 않았다.

## 4. 구현 내용

1. `CodexSDKAdapter`에 테스트용 SDK symbol 주입 경계를 추가했다.
2. override가 없으면 기존처럼 실제 `openai_codex` symbol을 import한다.
3. override에는 필요한 symbol 다섯 개가 모두 있어야 하며, 누락 시 명시적으로
   실패한다.
4. ORDER 245 테스트는 가짜 factory와 가짜 symbol을 함께 주입한다.
5. `requirements-dev.txt`에 선택 SDK를 강제로 추가하지 않았다.
6. 실제 ChatGPT 인증 확인, read-only sandbox, deny-all approval, tool 차단 규칙은
   변경하지 않았다.

## 5. 검증 결과

```text
pytest만 설치한 임시 가상환경:
python -m pytest tests/test_order_245_codex_sdk_chatgpt_auth_probe.py -q
3 passed

pytest만 설치한 임시 가상환경:
python -m pytest -x -q
476 passed, 5 deselected in 150.92s

일반 개발 환경:
python -m compileall songryeon_core main.py
passed

일반 개발 환경:
python -m pytest tests/test_order_245_codex_sdk_chatgpt_auth_probe.py -q
3 passed

일반 개발 환경:
python -m pytest -q
476 passed, 5 deselected in 146.67s

python main.py smoke-test
SMOKE_TEST_OK

git diff --check
passed
```

## 6. 남은 확인

- 이 기록 작성 시점에는 수정 commit을 공개 `main`에 push하기 전이다.
- push 뒤 새 GitHub Actions run이 실제로 통과하는지 별도로 확인한다.
- 원격 CI 통과 전에는 ORDER 264의 원격 검증이 끝났다고 간주하지 않는다.

## 7. 중단 판정

원격 CI가 통과하면 대회 전 기능 확장을 멈춘다. 이후 우선순위는 새 기능이 아니라
2026-07-23 세부 평가 기준 확인, 결과보고서 작성, 3분 시연영상 구성이다.
