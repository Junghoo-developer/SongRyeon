# order_137_source_code_context_summary_coverage_guard_2026_06_30_001

## 1. 작업 요약

ORDER_137을 구현했다.

`read_code_file`로 source-code 원문을 읽은 뒤 node_3가 공개 함수/상수 coverage를 빠뜨리지 않도록, code가 문법적으로 확인 가능한 source-code outline을 만들어 `Node3InputBriefFrame`과 node_3 LLM payload에 공급한다.

## 2. 변경 파일

- `Administrative_Reform_1/04_Orders/ORDER_137_SOURCE_CODE_CONTEXT_SUMMARY_COVERAGE_GUARD_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`
- `songryeon_core/core/schemas.py`
- `songryeon_core/nodes/node_2_handoff.py`
- `songryeon_core/nodes/node_3_reporter.py`
- `songryeon_core/prompts/node_3_reporter_v0.md`
- `songryeon_core/runtime/terminal_view.py`
- `tests/test_order_135_code_evidence_accounting.py`

## 3. 핵심 구현

- `Node3SourceCodeSymbol`과 `Node3SourceCodeOutline`을 추가했다.
- `read_code_file` result payload가 source-code context로 공급되면 Python `ast.parse`로 top-level outline을 생성한다.
- outline에는 함수, async 함수, class, 대문자 상수 assign의 이름/종류/line number/public 여부/docstring 존재 여부만 기록한다.
- code는 함수 의미를 요약하지 않는다. 의미 설명은 node_3가 supplied source text와 outline을 함께 보고 작성한다.
- node_3 LLM payload에는 `source_code_outlines`를 safe payload로 넣고 raw internal data id는 노출하지 않는다.
- grounding block과 terminal runtime view에 source-code outline count를 표시한다.
- node_3 prompt에 source-code outline을 coverage checklist로 쓰되, 함수명만 보고 동작을 단정하지 말라는 경계를 추가했다.

## 4. 검증

- `python -m compileall songryeon_core main.py`
  - 통과
- `python -m pytest tests/test_order_135_code_evidence_accounting.py`
  - `1 passed`
- `python -m pytest`
  - `77 passed`
- `python main.py smoke-test`
  - `SMOKE_TEST_OK`

## 5. 확인한 값

- `songryeon_core/tools/code_tools.py`를 `read_code_file`로 읽는 테스트에서 source-code outline이 1개 생성됐다.
- public function checklist에 다음 이름이 포함됐다.
  - `list_code_files`
  - `search_code`
  - `read_code_file`
- top-level symbol 목록에 다음 상수가 포함됐다.
  - `DEFAULT_CODE_FILE_EXTENSIONS`
  - `DEFAULT_IGNORED_DIR_NAMES`
- node_3 LLM payload의 outline item에는 `source_data_id`를 넣지 않았다.
- grounding block에 `source-code 구조 목록: 1개`가 표시된다.

## 6. 일부러 하지 않은 것

- 질문 문자열 기반 휴리스틱을 추가하지 않았다.
- code가 source-code 기능 의미를 대신 요약하지 않았다.
- read_code_file count를 read_doc count와 섞지 않았다.
- L loop budget, W/R loop, scheduler, 외부 DB, 장기기억 DB는 건드리지 않았다.
