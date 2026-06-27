# ORDER 116: Smoke Test Decomposition To Pytest v0

## 상태

발주서 초안.

ORDER_114 완료 후, 가능하면 ORDER_115 일부 완료 뒤 구현한다.

## 배경

현재 `songryeon_core/runtime/smoke_test.py`는 5000줄 이상이다.

이 파일은 많은 기준선을 지켜 왔지만, 다음 문제가 있다.

- 모든 smoke fixture와 검증이 한 파일에 몰려 있다.
- 작은 회귀를 빠르게 특정하기 어렵다.
- pytest가 있어도 테스트 단위를 나누지 않으면 효과가 제한된다.
- 새 기능을 추가할 때마다 smoke-test가 더 커진다.

## 목표

기존 `python main.py smoke-test` 결과를 유지하면서, 내부 smoke case를 주제별로 분해하고 pytest에서 개별 실행 가능하게 만든다.

핵심 원칙:

```text
기존 smoke-test CLI는 유지한다.
pytest는 같은 기준선을 더 잘게 실행하는 통로다.
```

## 구현 범위

### 1. smoke case module 분리

후보 구조:

```text
songryeon_core/runtime/smoke_cases/
  __init__.py
  memory_pipeline.py
  router_fallback.py
  l_loop_budget.py
  l_loop_continuation.py
  node3_grounding.py
  node4_guards.py
  runtime_view.py
  metainfo.py
```

기존 `run_smoke_tests()`는 aggregator로 남긴다.

### 2. pytest 파일 추가

후보 구조:

```text
tests/smoke/
  test_memory_pipeline.py
  test_router_fallback.py
  test_l_loop_budget.py
  test_l_loop_continuation.py
  test_node3_grounding.py
  test_node4_guards.py
  test_runtime_view.py
  test_metainfo.py
```

각 pytest는 해당 smoke case 함수를 호출한다.

### 3. 결과 key 호환 유지

현재 `run_smoke_tests()`가 반환하는 주요 key는 가능한 한 유지한다.

예:

```text
status
l_loop_control_count
recent_memory_relevance_selection_selected
node4_recent_memory_guard_pass
...
```

기존 README, 실행 기록, 사용자 테스트가 이 key를 기준으로 말해 왔기 때문이다.

### 4. 큰 이동은 작게 나눈다

한 PR/한 작업에서 모든 smoke를 완전히 분해하지 않아도 된다.

v0 최소 완료 기준:

- `smoke_test.py`에서 최소 3개 도메인을 별도 module로 이동
- pytest가 해당 도메인 테스트를 개별 실행
- 기존 `python main.py smoke-test` 결과 유지

권장 우선순위:

1. memory pipeline
2. router fallback
3. L loop budget/continuation
4. node4 guards
5. runtime view

## 금지

- smoke 기대값을 약화하지 않는다.
- 실패하는 smoke를 삭제하지 않는다.
- node_4 guard를 느슨하게 만들지 않는다.
- LLM live Qwen 테스트를 기본 pytest에 넣지 않는다.
- 리팩터링과 기능 추가를 섞지 않는다.

## 완료 조건

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

추가 확인:

- `smoke_test.py` line count가 줄어든다.
- 최소 3개 smoke case module이 생긴다.
- pytest에서 도메인별 테스트를 개별 실행할 수 있다.
- 기존 smoke-test summary key가 유지된다.

완료 보고에는 다음을 적는다.

- 분리한 smoke 도메인
- 새 smoke case module 목록
- 새 pytest 파일 목록
- 유지한 기존 summary key
- line count 변화
- pytest/smoke-test 결과
