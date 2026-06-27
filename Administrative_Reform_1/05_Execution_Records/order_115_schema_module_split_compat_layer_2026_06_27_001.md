# ORDER_115 schema module split compatibility layer 실행 기록

## 목적

`songryeon_core/core/schemas.py`를 기존 import 호환성을 유지한 채 단계적으로 분해하기 시작했다.

이번 작업은 파일 위치를 나누는 리팩터링이다. ORDER_112 기능 구현, schema field 추가, validator 조건 변경, smoke-test 분해는 하지 않았다.

## 변경 파일

- `songryeon_core/core/schemas.py`
- `songryeon_core/core/schema_parts/__init__.py`
- `songryeon_core/core/schema_parts/base.py`
- `songryeon_core/core/schema_parts/task_ledger.py`
- `songryeon_core/core/schema_parts/trace_data.py`
- `tests/test_import_baseline.py`
- `tests/test_schema_split_compat.py`
- `Administrative_Reform_1/05_Execution_Records/order_115_schema_module_split_compat_layer_2026_06_27_001.md`
- `Administrative_Reform_1/05_Execution_Records/README.md`

## 새 schema module 구조

추가한 구조:

```text
songryeon_core/core/schema_parts/
  __init__.py
  base.py
  task_ledger.py
  trace_data.py
```

분리 내용:

- `base.py`: `DataRef`, `SchemaBinding`, `NodeMovement`, `_validate_string_list`, `_validate_no_duplicates`
- `task_ledger.py`: `TaskFrame`, `TaskResultFrame`, task frame constants, task validators
- `trace_data.py`: `TraceEvent`, `UnifiedState`, `TurnStateCapsule`, `ZeroState`, `MemoryPacketFrom0`, `RoutingDecision`
- `__init__.py`: 위 공개 schema 이름의 새 module 경로 re-export

## compatibility layer

기존 compatibility layer 위치:

```text
songryeon_core/core/schemas.py
```

기존 import 경로는 유지된다.

```python
from songryeon_core.core.schemas import TaskFrame, TraceEvent, ZeroState
```

새 module 경로도 열린다.

```python
from songryeon_core.core.schema_parts.task_ledger import TaskFrame
from songryeon_core.core.schema_parts.trace_data import TraceEvent
```

## line count

PowerShell `Get-Content -Encoding UTF8 ... | Measure-Object -Line` 기준:

```text
songryeon_core/core/schemas.py: 3539 -> 3278
songryeon_core/core/schema_parts/base.py: 71
songryeon_core/core/schema_parts/task_ledger.py: 130
songryeon_core/core/schema_parts/trace_data.py: 118
songryeon_core/core/schema_parts/__init__.py: 43
```

`schemas.py`에서 첫 분리 대상인 공통/base, task ledger, trace/state 계열을 덜어냈다.

## pytest 보강

`tests/test_import_baseline.py`에 새 module import 기준선을 추가했다.

추가한 테스트 파일:

```text
tests/test_schema_split_compat.py
```

확인 내용:

- 기존 `songryeon_core.core.schemas` 경로에서 주요 schema import 가능
- 새 `songryeon_core.core.schema_parts.*` 경로에서 주요 schema import 가능
- compatibility layer가 새 module의 class object를 re-export함
- `TaskFrame`, `TraceEvent`의 `dataclasses.asdict()` payload shape 유지
- `validate_task_frame()`이 기존 경로와 새 경로에서 모두 동작

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
pytest: 4 passed in 131.03s
smoke-test passed: SMOKE_TEST_OK
```

추가로 `python -m compileall songryeon_core main.py tests`도 통과했다.

## 경계

이번 작업에서 하지 않은 것:

- ORDER_112 구현
- `schemas.py` 전체 분해
- field 이름 변경
- schema version 변경
- validator 조건 완화 또는 강화
- info_class/generated_by/source_data_ids 의미 변경
- smoke-test 분해
- CI 변경

## 후속

다음 단계 후보:

```text
1. ORDER_115 후속: tool 계열 또는 memory 계열 schema 추가 분리
2. ORDER_116: smoke_test.py를 도메인별 smoke case와 pytest로 분해 시작
```

현재 재정립 흐름에서는 smoke-test 파일 비대도가 더 큰 병목이므로, 다음 발주는 ORDER_116으로 넘어가는 것이 실용적이다.
