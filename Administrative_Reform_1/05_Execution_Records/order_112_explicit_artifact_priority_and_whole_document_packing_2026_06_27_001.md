# ORDER_112 explicit artifact priority and whole-document packing 실행 기록

## 목적

사용자 입력에 `ORDER_100` 같은 명시 문서 reference가 있을 때 embedding search 후보보다 먼저 원문 ORDER 문서를 direct resolve하고, node_3에 공급되는 문서 context를 whole-document char budget 기준으로 packing했다.

## 구현 위치

새 파일:

```text
songryeon_core/tools/document_context_pack.py
tests/test_order_112_document_context_pack.py
```

주요 변경:

```text
songryeon_core/core/schemas.py
songryeon_core/tools/document_tools.py
songryeon_core/loops/l_loop.py
songryeon_core/nodes/node_2_handoff.py
songryeon_core/runtime/terminal_view.py
songryeon_core/runtime/defaults.py
songryeon_core/runtime/dry_run.py
songryeon_core/runtime/user_turn.py
main.py
songryeon_core/prompts/node_3_reporter_v0.md
```

## 동작

추출:

```text
extract_explicit_artifact_references(user_text)
```

direct resolve:

```text
read_artifact(root, artifact_ref)
ExplicitArtifactReferenceFrame
```

`ORDER_###` bare reference는 `04_Orders/` 아래 원문 ORDER 파일명의 prefix로만 매칭한다.
실행기록, README, digest, summary는 bare ORDER 원문 대체 후보로 쓰지 않는다.

context packing:

```text
DocumentContextPackFrame
max_document_context_chars
budget_unit=chars
whole_document_only=true
strict_rank_order=true
```

rank order:

```text
explicit unique references in user order
-> embedding search preserved unique doc_id candidates
```

budget 초과 문서는 `excluded_due_to_context_budget`가 되고, strict rank order 때문에 그 뒤 후보는 `excluded_after_strict_rank_cutoff`가 된다.

## node_3 연결

`node_2_handoff.record_node3_input_brief()`는 `DocumentContextPackFrame`이 있으면 included document만 `read_documents`에 넣는다.

excluded document는 `excluded_document_contexts`로만 전달한다.
이 목록은 읽은 문서 count에 들어가지 않는다.

## runtime 표시

pretty runtime에 다음을 표시한다.

```text
explicit_artifact_refs
document_context_pack included/excluded/budget/cutoff
route=2 handoff document_context_pack counts
node_3 input brief excluded_contexts
```

## 테스트

추가 pytest:

```text
tests/test_order_112_document_context_pack.py
```

검증한 내용:

```text
explicit ORDER reference extraction
unique ORDER direct resolve and rank priority
ambiguous ORDER reference no arbitrary selection
whole-document packing without mid-document cut
excluded_due_to_context_budget
excluded_after_strict_rank_cutoff
node_3 read_documents count == included count
excluded document not counted as read
terminal view displays explicit resolve and context pack
```

## 검증 결과

실행:

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

결과:

```text
compileall passed
pytest: 14 passed in 243.25s
smoke-test passed: SMOKE_TEST_OK
```

중간 실패:

```text
pytest first full run failed with NameError: query_data_ids is not defined
```

원인:

```text
DocumentContextPackFrame source_data_ids 조립에서 존재하지 않는 로컬 이름을 사용했다.
```

조치:

```text
l2_query_data_id와 revision_query_data_ids를 명시적으로 사용하도록 수정했다.
```

## 일부러 하지 않은 것

이번 작업에서 하지 않은 것:

- W loop 열기
- R loop 열기
- scheduler 변경
- 외부 DB/vector DB/장기기억 DB 변경
- same-turn L reroute 횟수 확대
- node_4 자동 재작성 루프
- tokenizer 기반 정확 토큰 계산
- 동적 document context budget 자동 증액
- 코드가 의미적으로 중요한 문서를 고르는 정책
- excluded 문서를 node_3 read document count에 포함
- 문서 중간을 잘라 넣고 전체 문서처럼 표시
