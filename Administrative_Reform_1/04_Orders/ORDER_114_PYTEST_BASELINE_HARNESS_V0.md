# ORDER 114: Pytest Baseline Harness v0

## 상태

발주서 초안.

ORDER_113 완료 후 구현한다.

## 배경

현재 SongRyeon Core의 자동 검증은 `python main.py smoke-test`에 집중되어 있다.

이 smoke-test는 유용하지만 다음 한계가 있다.

- 모든 검사가 한 파일과 한 함수 계열에 몰려 있다.
- 실패 지점이 커질수록 진단 비용이 커진다.
- pytest test discovery, fixture, marker, 개별 테스트 실행이 없다.
- 새 리팩터링에서 작은 단위 안전망으로 쓰기 어렵다.

따라서 먼저 pytest 골격을 만든다.

## 목표

pytest 기반 테스트 체계를 "기존 smoke-test를 감싸는 방식"으로 도입한다.

핵심 원칙:

```text
처음 pytest 도입은 동작 변경이 아니라 테스트 진입점 추가다.
```

## 구현 범위

### 1. 테스트 폴더 생성

후보 구조:

```text
tests/
  test_smoke_baseline.py
  test_import_baseline.py
```

### 2. pytest 설정 추가

후보 파일:

```text
pyproject.toml
```

또는 작게:

```text
pytest.ini
```

권장:

```text
pyproject.toml
```

이유:

- 나중에 ruff/mypy 같은 도구 설정도 한곳에 둘 수 있다.
- 현재 프로젝트에는 아직 패키지 설정 파일이 없다.

### 3. 최소 pytest 테스트

`tests/test_import_baseline.py`

검증 후보:

- `songryeon_core` import 가능
- 핵심 module import 가능
- `main.py` import 가능

`tests/test_smoke_baseline.py`

검증 후보:

- `from songryeon_core.runtime.smoke_test import run_smoke_tests`
- `run_smoke_tests()["status"] == "SMOKE_TEST_OK"`

### 4. pytest dependency 처리

현재 runtime은 표준 라이브러리 중심이다.

pytest는 runtime dependency가 아니라 dev/test dependency로 취급한다.

선택지:

```text
requirements-dev.txt
```

또는 `pyproject.toml`의 optional dependency.

v0 권장:

```text
requirements-dev.txt
pytest
```

CI에서는 pytest 설치 후 실행한다.

### 5. 기존 CLI 유지

다음 명령은 계속 유지한다.

```powershell
python main.py smoke-test
```

pytest 도입은 기존 smoke-test CLI를 대체하지 않는다.
처음에는 pytest가 smoke-test를 호출하는 얇은 껍데기여도 된다.

## 금지

- smoke-test 내용을 이 발주에서 대량 이동하지 않는다.
- schema 분해를 동시에 하지 않는다.
- Qwen live test를 pytest 기본 실행에 넣지 않는다.
- 외부 DB, W/R loop, scheduler를 건드리지 않는다.
- 테스트 통과를 위해 guard를 약화하지 않는다.

## 완료 조건

다음이 모두 통과해야 한다.

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

완료 보고에는 다음을 적는다.

- pytest 설정 파일 위치
- 추가된 tests 파일
- pytest 실행 결과
- smoke-test CLI 유지 여부
- runtime dependency와 dev/test dependency 구분
