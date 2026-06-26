# Runtime Metainfo Labels v2 2026-06-22 001

**상태**: 완료 기록  
**관련 발주서**: `ORDER_068_RUNTIME_METAINFO_LABELS_V2`  
**실행일**: 2026-06-22

## 수행 내용

`terminal_view.py`의 pretty runtime 출력에 메타정보 관리법의 필수 라벨을 추가했다.

각 주요 런타임 블록은 다음 정보를 표시한다.

- `generated_by`
- `info_class`
- `source_data_ids`
- `semantic_judgement_status`

문서 원문 발췌에는 추가로 다음 정보를 표시한다.

- `copied_from`
- `selection_method`
- `truncated`

## 주요 변경

1. Node0 memory packet
   - `generated_by: CODE:RULE_STUB`
   - `info_class: absolute`
   - `semantic_judgement_status: not_run`
2. Node1 routing
   - `generated_by: CODE:RULE_STUB`
   - `route_rule_id`, `matched_keywords`, `policy_flag` 표시
3. L1 goal stub
   - `generated_by: RULE_STUB`
   - `info_class: absolute_stub`
4. L2 query plan
   - Qwen 실행 시 `generated_by: LLM:qwen3:14b`
   - LLM call data id를 `source_data_ids`에 표시
5. search_docs/read_doc
   - `generated_by: TOOL:search_docs`
   - `generated_by: TOOL:read_doc`
   - read_doc은 `copied_from: tool_result:read_doc:*.payload.text` 표시
6. L3 operation check
   - `generated_by: CODE:OPERATION_CHECK`
   - `semantic_judgement_status: not_run`
7. final answer
   - `generated_by: CODE/RENDERER`
   - `semantic_judgement_status: LLM_REPORTER=not_run`

## 검증

실행한 명령:

```text
python main.py smoke-test
python main.py fake-turn "송련의 문서 메모리 인덱스가 무엇을 읽는지 알려줘" --pretty
python main.py qwen-turn "송련의 문서 메모리 인덱스가 무엇을 읽는지 알려줘" --timeout 120 --pretty
```

확인된 smoke 결과:

- `status`: `SMOKE_TEST_OK`
- `runtime_metainfo_label_count`: `12`
- `runtime_has_copied_from`: `true`

## 남은 한계

출력은 정직해졌지만 Node1, L1, L3, Node2, Node3는 아직 실제 LLM 노드가 아니다.

다음 단계는 `ORDER_069_NODE1_LLM_ROUTER`이다.

