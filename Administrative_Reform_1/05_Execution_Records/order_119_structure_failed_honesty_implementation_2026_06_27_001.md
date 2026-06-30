# Execution Record: ORDER 119 Structure Failed Honesty Implementation 2026-06-27 001

## 목적

`structure_failed` 상태에서 검색/문서 근거를 가진 것처럼 말하는 fallback 답변을 막고, node_2 answer-basis selector 실패 원인을 runtime과 test에서 확인 가능하게 했다.

## 변경 요약

- `structure_failed` fallback 답변을 별도 렌더링 경로로 분리했다.
- 검색 또는 read_doc payload가 실제로 있을 때만 해당 payload를 언급하도록 했다.
- node_2 answer-basis fallback frame에 실패 진단 필드를 추가했다.
- runtime/CLI 요약에 answer-basis 실패 진단을 표시하도록 했다.
- selected recent memory context가 실행기록 문서나 read_document가 아니라는 경계를 node_3 prompt와 brief payload에 추가했다.
- `**근거 기준:**` 형태의 중복 grounding block도 code assembly에서 제거하도록 했다.

## 추가한 진단 필드

### structure_failed

- `structure_failure_stage`
- `structure_failure_reason`
- `structure_failure_exception_type`
- `structure_failure_llm_call_data_id`
- `structure_failure_trace_event_id`
- `structure_failure_node`
- `structure_failure_prompt_ref`

### node_2 answer basis

- `answer_basis_failure_type`
- `answer_basis_llm_call_data_id`
- `answer_basis_trace_event_id`
- `answer_basis_validation_error`
- `answer_basis_raw_text_present`
- `answer_basis_prompt_ref`
- `answer_basis_payload_parse_status`

## 추가한 테스트

- `tests/test_order_119_structure_failed_honesty.py::test_structure_failed_fallback_no_fake_search`
- `tests/test_order_119_structure_failed_honesty.py::test_structure_failed_mentions_actual_search_payload_only_when_present`
- `tests/test_order_119_structure_failed_honesty.py::test_answer_basis_failure_diagnostics_are_recorded_and_rendered`
- `tests/test_order_119_structure_failed_honesty.py::test_selected_recent_memory_payload_boundary_is_not_document`
- `tests/test_order_119_structure_failed_honesty.py::test_bold_duplicate_grounding_block_is_stripped`

## 검증

```powershell
python -m compileall songryeon_core main.py
```

결과: 통과.

```powershell
python -m pytest
```

1차 결과: 124초 제한에서 timeout. 출력 없이 종료되어 테스트 실패라기보다 실행 시간 제한 문제로 판단했다.

재실행:

```powershell
python -m pytest
```

결과: 25 passed in 260.85s.

```powershell
python main.py smoke-test
```

결과: `SMOKE_TEST_OK`.

추가 확인:

```powershell
python -m pytest tests/test_order_119_structure_failed_honesty.py
```

결과: 5 passed in 0.07s.

## 비범위

- 사용자 질문을 휴리스틱으로 분류해 fallback 의미 답변을 만들지 않았다.
- answer_basis_mode를 code가 의미적으로 대신 고르지 않았다.
- node_4 guard를 약화하지 않았다.
- W/R loop, scheduler, 외부 DB, vector DB, 장기기억 DB를 건드리지 않았다.
- same-turn L reroute 횟수나 node_4 자동 재작성 루프를 늘리지 않았다.
