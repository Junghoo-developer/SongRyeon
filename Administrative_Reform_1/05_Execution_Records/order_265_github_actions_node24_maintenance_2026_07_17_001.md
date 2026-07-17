# ORDER 265 GitHub Actions Node 24 Maintenance 실행 기록

## 1. 실행 일자

- 2026-07-17

## 2. 발견 사실

- ORDER 264 GitHub Actions run `29561437912`는 1분 8초 만에 성공했다.
- 해당 run에는 Node.js 20 기반 action이 deprecated됐고 Node.js 24로 강제
  실행됐다는 경고가 1개 남았다.
- 경고 대상은 `actions/checkout@v4`, `actions/setup-python@v5`였다.

## 3. 근거

- `actions/checkout` 공식 README는 v5부터 Node.js 24 runtime을 사용하며 현재
  v6 사용법을 제공한다.
- `actions/setup-python` 공식 README는 v6에서 Node.js 24로 전환했음을 명시한다.
- 현재 workflow는 GitHub-hosted `ubuntu-latest`를 사용하므로 최신 runner 요구사항에
  맞는다.

## 4. 변경 내용

1. `actions/checkout@v4`를 `actions/checkout@v6`으로 갱신했다.
2. `actions/setup-python@v5`를 `actions/setup-python@v6`으로 갱신했다.
3. workflow 권한을 `contents: read`로 명시했다.
4. Python 3.12와 compileall, pytest, smoke-test 검증 순서는 유지했다.

## 5. 검증 기준선

변경 직전 동일 제품 코드의 검증 결과는 다음과 같다.

```text
clean pytest-only environment: 476 passed, 5 deselected
normal environment: 476 passed, 5 deselected
python main.py smoke-test: SMOKE_TEST_OK
GitHub Actions run 29561437912: Success
```

ORDER 265의 최종 완료 여부는 변경 후 새 GitHub Actions main run의 성공과
Node.js 20 deprecation 경고 제거로 판정한다.

## 6. 중단 판정

새 원격 CI가 경고 없이 통과하면 대회 전 코드 기능 확장을 멈춘다.
