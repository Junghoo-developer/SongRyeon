# ORDER 126 Runtime All Document Extract Display 실행 기록

일시: 2026-06-28

## 배경

ORDER_124 live qwen 테스트에서 `node_0 document material packet`과 `node_3 input brief`는 실제 원문 읽기 수를 `actual_read=2`로 보여줬다.

그러나 terminal top-level `read_doc [TOOL_RESULT:DOCUMENT_EXTRACT]` 표시가 최신 document extract record 1개만 보여, 사람이 runtime 화면만 볼 때 실제 읽은 문서 수를 헷갈릴 수 있었다.

## 변경

- `songryeon_core/runtime/terminal_view.py`
  - `_latest_document_extract_record()` 1개 표시 대신 `_document_extract_records_for_display()` 목록 표시를 추가했다.
  - `tool_result:read_doc`과 `tool_result:read_artifact` record를 모두 runtime view에 표시한다.
  - 최신 L run-scoped document extract record가 있으면 최신 run record를 우선 표시한다.
  - run-scoped `read_artifact`도 도구명을 `read_artifact`로 표시하도록 `_document_extract_tool_name()`을 추가했다.

- `tests/test_order_126_runtime_document_extract_display.py`
  - 여러 document extract record가 모두 표시되는지 확인한다.
  - 최신 L run-scoped document extract가 있으면 과거 run record가 대표 표시에서 제외되는지 확인한다.

## 하지 않은 것

- L 검색 전략은 바꾸지 않았다.
- `read_doc` 예산은 바꾸지 않았다.
- node_3 문서 요약은 추가하지 않았다.
- node_4 guard는 약화하지 않았다.
- W/R loop, scheduler, 외부 DB, 장기기억 DB는 건드리지 않았다.

## 검증

- `python -m compileall songryeon_core main.py`
  - 통과
- `python -m pytest tests/test_order_126_runtime_document_extract_display.py`
  - 2 passed
- `python -m pytest`
  - 50 passed
- `python main.py smoke-test`
  - `SMOKE_TEST_OK`
