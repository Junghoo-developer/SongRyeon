# Tool Result Distillation 2026-06-22 001

**대상 발주서**: `ORDER_048_TOOL_RESULT_DISTILLATION.md`  
**성격**: 코드 구현 기록  
**결과**: dry-run과 smoke-test 통과

## 구현 요약

도구 결과 원본을 L3가 직접 우선 읽는 구조에서, 원본 추적성을 유지한 작은 `ToolResultDistillationFrame`을 먼저 읽는 구조로 바꿨다.

기본 dry-run의 도구 결과 흐름은 다음과 같다.

```text
search_docs
-> tool_result:search_docs:...
-> tool_distillation:search_docs:...
-> L3 preserved candidates

read_doc
-> tool_result:read_doc:...
-> tool_distillation:read_doc:...
-> L3 source data
```

## 코드 변경

1. `schemas.py`
   - `ToolResultDistilledItem`을 추가했다.
   - `ToolResultDistillationFrame`을 추가했다.
   - `validate_tool_result_distillation_frame()`을 추가했다.

2. `tool_result_distiller.py`
   - `record_tool_result_distillation()`을 추가했다.
   - `search_docs` 결과는 `doc_id`, `chunk_id`, `score`, `embedding_model_id`, `text_preview` 중심으로 압축한다.
   - `read_doc` 결과는 `doc_id`, `char_count`, 짧은 원문 preview 중심으로 압축한다.
   - distillation frame은 항상 `original_tool_result_data_id`를 가진다.

3. `l_loop.py`
   - `search_docs`와 `read_doc` 실행 직후 distillation frame을 만든다.
   - L3 입력에는 원본 tool result 대신 distillation data_id를 우선 넣는다.
   - L루프 output에는 원본 tool result와 distillation frame을 모두 남긴다.

4. `l3_result_keeper.py`
   - L3가 `ToolResultDistillationFrame.items`에서 `search_result` 후보를 추출할 수 있게 했다.
   - L3 preserved candidate의 `source_data_id`가 search_docs 원본이 아니라 distillation frame을 가리킬 수 있게 했다.

5. `smoke_test.py`
   - search/read distillation record 존재를 검증한다.
   - distillation이 원본 tool result 링크를 유지하는지 검증한다.
   - L3가 원본 search result보다 distillation을 우선 source로 받는지 검증한다.

## 검증

```text
python -m py_compile songryeon_core\core\schemas.py songryeon_core\tools\tool_result_distiller.py songryeon_core\loops\l_loop.py songryeon_core\nodes\l3_result_keeper.py songryeon_core\runtime\smoke_test.py
python main.py dry-run
python main.py smoke-test
```

smoke-test 핵심 결과:

```text
status=SMOKE_TEST_OK
trace_count=24
data_record_count=24
tool_distillation_count=2
tool_distillation_sources_l3=True
l_loop_control_count=3
l_loop_final_decision=stop_success
l_loop_read_doc_used=True
```

## 현재 한계

이번 단계의 distillation은 규칙 기반 preview 압축이다.  
도구 사용의 중복 방지, query/doc 반복 억제, 결과 품질 대비 비용 판단은 `ORDER_049_TOOL_EFFICIENCY_POLICY.md`에서 이어서 다룬다.
