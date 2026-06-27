# ORDER_114 pytest baseline harness 실행 기록

## 목적

기존 `python main.py smoke-test`를 유지하면서 pytest 기반 테스트 진입점을 추가했다.

이번 작업은 동작 변경이 아니라 테스트 실행 경로 추가다. smoke-test 내부 분해, schema 분해, CI 변경, ORDER_112 기능 구현은 하지 않았다.

## 변경 파일

- `pyproject.toml`
- `requirements-dev.txt`
- `tests/test_import_baseline.py`
- `tests/test_smoke_baseline.py`
- `Administrative_Reform_1/05_Execution_Records/order_114_pytest_baseline_harness_2026_06_27_001.md`
- `Administrative_Reform_1/05_Execution_Records/README.md`

## 구현 내용

`pyproject.toml`에 pytest 설정을 추가했다.

```text
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-ra -p no:cacheprovider"
```

Windows/OneDrive 한글 경로에서 pytest 기본 cache provider가 cache write warning을 만들었기 때문에, 이 저장소의 기본 pytest 실행에서는 cache provider를 끈다. 테스트 결과 자체에는 영향이 없다.

`requirements-dev.txt`를 추가하고 `pytest`를 dev/test dependency로 분리했다.

`tests/test_import_baseline.py`는 다음 import 기준선을 확인한다.

- `songryeon_core`
- `songryeon_core.core.schemas`
- `songryeon_core.core.trace_store`
- `songryeon_core.runtime.dry_run`
- `songryeon_core.runtime.smoke_test`
- `main`

`tests/test_smoke_baseline.py`는 기존 smoke-test 함수를 pytest에서 감싼다.

```text
run_smoke_tests()["status"] == "SMOKE_TEST_OK"
```

## 경계

이번 작업에서 하지 않은 것:

- smoke-test 내용 이동 또는 분해
- schema module split
- Qwen live test를 pytest 기본 실행에 포함
- CI workflow 변경
- ORDER_112 구현
- guard 완화

기존 CLI는 그대로 유지된다.

```powershell
python main.py smoke-test
```

## 검증

실행:

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

결과:

```text
compileall passed
pytest: 2 passed in 127.26s
smoke-test passed: SMOKE_TEST_OK
```

pytest 실행 환경:

```text
Python 3.10.11
pytest 9.0.3
collected 2 items
tests/test_import_baseline.py passed
tests/test_smoke_baseline.py passed
```

추가 확인:

```powershell
python -m pytest tests/test_import_baseline.py
```

결과:

```text
1 passed in 0.07s
```

## 후속

다음 권장 발주는 ORDER_115 또는 ORDER_116이다.

구조 안정성 순서만 보면 ORDER_115에서 `schemas.py` compatibility layer 분해를 먼저 시작하고, ORDER_116에서 smoke-test를 도메인별 pytest로 나누는 흐름이 좋다.

ORDER_117은 pytest와 smoke-test가 더 자리 잡은 뒤 CI와 개발 루틴을 잠그는 작업으로 둔다.
