# ORDER 115: Schema Module Split With Compatibility Layer v0

## 상태

발주서 초안.

ORDER_114 완료 후 구현한다.

## 배경

현재 `songryeon_core/core/schemas.py`는 3500줄 이상이며, 다음 책임이 한 파일에 섞여 있다.

- trace/data/task schema
- LLM call schema
- memory packet schema
- recent memory schema
- node_2/node_3/node_4 handoff/brief/report schema
- L1/L2/L3 schema
- L loop budget/continuation/control schema
- tool result distillation/budget schema
- document memory index schema
- validator helpers

이 파일이 계속 커지면 새 기능이 들어갈 때마다 충돌 위험이 커진다.

## 목표

`schemas.py`를 동작 변경 없이 여러 schema module로 분해한다.

핵심 원칙:

```text
기존 import 경로는 깨지지 않는다.
```

즉, 기존 코드의 다음 import는 계속 동작해야 한다.

```python
from songryeon_core.core.schemas import SomeFrame
```

## 구현 전략

### 1. compatibility layer 유지

기존 파일:

```text
songryeon_core/core/schemas.py
```

는 당분간 public re-export 관문으로 남긴다.

새 모듈 후보:

```text
songryeon_core/core/schema_parts/
  __init__.py
  base.py
  trace_data.py
  llm.py
  memory.py
  routing.py
  node_brief.py
  l_loop.py
  tooling.py
  task_ledger.py
  document_memory.py
```

`schemas.py`는 새 모듈에서 import한 이름을 다시 export한다.

### 2. 단계적 이동

한 번에 전부 옮기지 않는다.

권장 순서:

1. 순수 helper/공통 validator
2. trace/data/task 계열
3. tool 계열
4. memory 계열
5. L loop 계열
6. node brief/report/gatekeeper 계열
7. 남은 compatibility 정리

각 단계는 compileall/pytest/smoke-test를 통과해야 한다.

### 3. public import test 추가

pytest에 다음 검사를 추가한다.

- 기존 import 경로에서 주요 schema import 가능
- 새 module 경로에서 주요 schema import 가능
- dataclass `asdict` payload가 기존과 동일한 shape 유지

### 4. 행동 변경 금지

다음은 하지 않는다.

- field 이름 변경
- schema version 변경
- validator 조건 완화
- validator 조건 강화
- info_class 정책 변경
- generated_by/source_data_ids 의미 변경

이 발주는 파일 위치만 바꾸는 리팩터링이다.

## 금지

- ORDER_112 기능 구현과 섞지 않는다.
- smoke-test 분해와 동시에 대량 이동하지 않는다.
- import 오류를 숨기기 위해 broad except를 넣지 않는다.
- 기존 schema validate 함수를 삭제하지 않는다.

## 완료 조건

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

추가 확인:

- 기존 `from songryeon_core.core.schemas import ...` 경로가 유지된다.
- `schemas.py` line count가 의미 있게 줄어든다.
- 새 schema module 구조가 README 또는 실행 기록에 기록된다.

완료 보고에는 다음을 적는다.

- 새 schema module 목록
- compatibility layer 위치
- 기존 import 유지 여부
- line count 변화
- pytest/smoke-test 결과
