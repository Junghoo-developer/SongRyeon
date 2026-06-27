# ORDER_116 smoke-test decomposition to pytest 실행 기록

## 목적

기존 `python main.py smoke-test` 통합 기준선을 유지하면서, `smoke_test.py` 안에 몰려 있던 일부 smoke case를 도메인별 module과 pytest로 분리했다.

이번 작업은 smoke 구조 분해다. ORDER_112 기능 구현, schema 추가, guard 완화, Qwen live test 기본 pytest 편입은 하지 않았다.

## 분리한 smoke 도메인

v0에서 분리한 도메인:

- runtime view / live trace
- router fallback honesty
- document memory index

## 새 smoke case module

추가한 module:

```text
songryeon_core/runtime/smoke_cases/__init__.py
songryeon_core/runtime/smoke_cases/runtime_view.py
songryeon_core/runtime/smoke_cases/router_fallback.py
songryeon_core/runtime/smoke_cases/document_memory.py
```

이동한 함수:

```text
runtime_view.py
- run_live_trace_progress_stream_smoke
- run_runtime_count_consistency_smoke

router_fallback.py
- run_router_fallback_honesty_smoke

document_memory.py
- check_document_memory_index
```

`songryeon_core/runtime/smoke_test.py`의 `run_smoke_tests()`는 aggregator로 유지했다. 기존 summary key를 만들 때는 새 module 함수를 import해서 호출한다.

## 새 pytest 파일

추가한 pytest:

```text
tests/smoke/test_runtime_view.py
tests/smoke/test_router_fallback.py
tests/smoke/test_document_memory.py
```

`tests/test_import_baseline.py`에는 새 `smoke_cases` module import 기준선을 추가했다.

## 유지한 기존 summary key

기존 `python main.py smoke-test`의 주요 key는 유지했다.

이번 분리와 직접 관련된 key:

```text
status
runtime_count_reportable_documents
runtime_count_raw_extract_records
runtime_count_empty_extract_records
node1_router_fallback_policy
node1_router_fallback_failure_type
node1_router_fallback_terminal_distinct
node1_router_strict_blocked
document_memory_index_docs
document_memory_index_has_order
document_memory_index_l3_metadata
live_trace_line_count
live_trace_matches_trace_count
live_trace_no_report_body
```

## line count 변화

PowerShell `Get-Content -Encoding UTF8 ... | Measure-Object -Line` 기준:

```text
songryeon_core/runtime/smoke_test.py: 5492 -> 5197
songryeon_core/runtime/smoke_cases/runtime_view.py: 136
songryeon_core/runtime/smoke_cases/router_fallback.py: 88
songryeon_core/runtime/smoke_cases/document_memory.py: 92
songryeon_core/runtime/smoke_cases/__init__.py: 1
```

## 검증

실행:

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/smoke
python -m pytest
python main.py smoke-test
```

결과:

```text
compileall passed
tests/smoke: 4 passed in 5.96s
pytest: 8 passed in 134.83s
smoke-test passed: SMOKE_TEST_OK
```

기존 CLI smoke-test는 별도로 통과했다.

## 경계

이번 작업에서 하지 않은 것:

- ORDER_112 구현
- smoke 기대값 약화
- 실패하는 smoke 삭제
- node_4 guard 완화
- LLM live Qwen 테스트를 기본 pytest에 포함
- schema 추가 또는 schema version 변경
- CI 변경

## 후속

다음 발주 후보는 ORDER_117이다.

ORDER_117에서는 다음 명령을 개발 루틴과 CI에 고정한다.

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

ORDER_112 기능 구현은 ORDER_117로 CI/개발 루틴이 잠긴 뒤 재개하는 것이 안전하다.
