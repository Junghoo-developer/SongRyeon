# ORDER 154: Fast Test Gate v0

## 1. Goal

전체 pytest와 smoke-test가 오래 걸리는 상황에서, 개발 중 빠르게 빨간불을 볼 수 있는 CLI test gate를 추가한다.

이번 발주는 전체 검증을 약화하지 않는다. `python -m pytest`와 `python main.py smoke-test`는 최종 검증으로 유지한다.

## 2. Problem

최근 기준:

```text
python -m pytest -q -> 147 passed, 약 14분 33초
python main.py smoke-test -> 수 분 단위
```

이 속도는 큰 변경을 잠글 때는 괜찮지만, 작은 수정 직후 매번 돌리기에는 느리다.

## 3. Scope

추가한다.

- `python main.py fast-test`
- `python main.py fast-test --profile core`
- `python main.py fast-test --profile graph`
- `python main.py fast-test --dry-run`

프로필:

- `core`: compileall + import/schema compatibility pytest
- `graph`: compileall + current graph/R/L activity ledger boundary pytest

## 4. Non-goals

이번 발주는 다음을 하지 않는다.

- 전체 pytest 기본 동작 변경
- smoke-test 삭제/약화
- slow marker로 기존 테스트를 숨김
- CI 기준선 변경
- 테스트 의미를 느슨하게 바꿈

## 5. Test Plan

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_154_fast_test_gate.py tests/test_import_baseline.py -q
python main.py fast-test --dry-run
python main.py fast-test --profile core
git diff --check
```

큰 발주 완료 시에는 여전히 다음을 돌린다.

```powershell
python -m pytest
python main.py smoke-test
```
