# ORDER_117 CI and development routine lock 실행 기록

## 목적

ORDER_114~116에서 추가한 pytest 기준선을 CI와 개발 문서에 고정했다.

이번 작업은 검증 루틴 잠금이다. ORDER_112 기능 구현, Qwen live test CI 편입, smoke-test 제거는 하지 않았다.

## 갱신한 CI 파일

```text
.github/workflows/smoke-test.yml
```

GitHub Actions 실행 순서:

```yaml
- Install test dependencies
- Compile Python files
- Run pytest
- Run smoke tests
```

test dependency 설치 방식:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

`pytest`는 runtime dependency가 아니라 `requirements-dev.txt`의 dev/test dependency로 유지한다.

## 갱신한 문서

- `README.md`
- `README.ko.md`
- `PUBLICATION_CHECKLIST.md`
- `Administrative_Reform_1/01_Maintenance_System/DEVELOPMENT_CYCLE_POLICY_v0.md`
- `Administrative_Reform_1/05_Execution_Records/order_117_ci_and_development_routine_lock_2026_06_27_001.md`
- `Administrative_Reform_1/05_Execution_Records/README.md`

문서에 고정한 기본 기준선:

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

테스트 계층 이름:

```text
compileall: 문법/임포트 최소 검사
pytest: 단위/도메인 회귀 검사
smoke-test: 통합 런타임 기준선 검사
qwen-turn/qwen-chat: 수동 live LLM 검사
```

Qwen/Ollama live test는 CI 필수 조건이 아니라 수동 live LLM 검사로 분리했다.

## 로컬 검증

실행:

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

결과:

```text
compileall passed
pytest: 8 passed in 135.92s
smoke-test passed: SMOKE_TEST_OK
```

## CI 결과

원격 GitHub Actions는 이 로컬 작업 중 직접 실행하지 않았다.

확인 가능한 현재 상태:

```text
.github/workflows/smoke-test.yml 갱신 완료
CI workflow now installs requirements-dev.txt
CI workflow now runs compileall, pytest, smoke-test
```

GitHub에 push 또는 PR이 생기면 Actions에서 실제 CI 결과를 확인해야 한다.

## ORDER_112 재개 가능 여부

ORDER_117 기준으로 ORDER_112 재개 조건은 로컬/문서/CI 설정 관점에서 충족됐다.

충족된 조건:

- pytest baseline 존재
- schema split 계획 및 1차 compatibility split 완료
- smoke decomposition 시작
- CI workflow가 pytest와 smoke-test를 모두 실행하도록 갱신됨

남은 확인:

- 원격 GitHub Actions 실제 통과 여부는 push/PR 이후 확인 필요

따라서 다음 기능 발주로 ORDER_112를 재개할 수 있다. 단, ORDER_112 구현은 재정립 변경과 별도 작업 묶음으로 진행한다.

## 경계

이번 작업에서 하지 않은 것:

- ORDER_112 구현
- smoke-test 제거
- pytest만 통과하면 충분하다고 문서화
- Qwen/Ollama live test를 CI 필수 단계로 추가
- 기능 확장과 CI 잠금을 섞음
