# ORDER_125 L3 Per-Document Summary Frame v0

## 목표

L3가 실제로 읽은 문서에 대해 문서별 요약 frame을 만들고, 그 요약을 node_3에게 원문과 구분되는 의미 재료로 전달한다.

이번 구현은 node_3에게 원문을 바로 제거하고 요약만 주는 작업이 아니다.
원문 context와 별도로 L3 요약 frame을 추가하여, 이후 answer_basis_mode별 context/summary 선택 정책을 열 수 있게 한다.

## 배경

ORDER_124는 node_0이 L 이후 문서 장부를 절대정보로 정리하는 방향이다.
그 다음 단계로 L3가 읽은 문서 내용을 짧게 요약하면 node_3가 문서 폭탄을 덜 받게 될 수 있다.

하지만 요약은 의미 생성이다.
따라서 code가 만드는 절대정보 장부와 달리, L3 요약은 정보 등급과 검증 경계가 필요하다.

## 정보 분류 원칙

문서 1개에 대응하는 담백 요약:

- `info_class=relative`
- `source_mode=direct_record`
- `claim_alignment=one_document_to_one_summary`
- source는 특정 `tool_result:read_doc` 또는 `tool_result:read_artifact` record 하나여야 한다.

현재 질문/L1 목표/문서 원문을 함께 보고 만든 상황 요약:

- `info_class=mixed`
- `source_mode=source_bundle`
- `claim_alignment=one_document_plus_task_context`
- source bundle 안에는 최소한 source document record와 L3/L1 계열 task context record가 함께 있어야 한다.

여러 문서를 묶은 종합 요약은 이번 구현에서 열지 않는다.

## 제안 구조

```text
L3PerDocumentSummaryFrame
- frame_id
- turn_id
- source_document_data_id
- source_doc_id
- source_document_name
- source_char_count
- summary_status
- plain_document_summary
- plain_summary_info_class=relative
- plain_summary_source_mode=direct_record
- plain_summary_claim_alignment=one_document_to_one_summary
- plain_summary_source_data_id
- task_relevant_summary
- task_relevant_summary_info_class=mixed
- task_relevant_summary_source_mode=source_bundle
- task_relevant_summary_claim_alignment=one_document_plus_task_context
- task_relevant_summary_source_data_ids
- summary_limit_note
- generated_by=LLM:*
- semantic_judgement_status=ran|failed
- llm_call_data_id
- source_trace_ids
- source_data_ids
```

요약 실패 frame도 명시한다.

```text
summary_status=failed
summary_failure_type=parse_failed|schema_failed|adapter_failed|timeout
plain_document_summary=""
task_relevant_summary=""
```

## 구현 범위

- L3 result keeper가 실제 document extract record마다 LLM summary call을 실행한다.
- code는 요약 문장을 생성하지 않는다.
- code는 LLM payload/schema 검증, 정보 등급 필드 고정, source ID 연결만 담당한다.
- node_2는 L3 summary frame을 node_3 brief에 안전한 material로 복사한다.
- node_3 payload에는 raw internal ID 대신 문서명, summary status, 두 요약 본문, 정보 등급 경계만 들어간다.

## node_4 검토 후보

node_4는 다음을 검사할 수 있다.

- 요약이 source document 하나에만 붙어 있는지
- source_data_ids에 원문 record가 포함되어 있는지
- user-facing 답변에서 요약이 원문 사실처럼 과장되지 않는지
- 문서별 요약을 여러 문서 종합 결론처럼 말하지 않는지

## 제외 범위

- node_0이 요약하지 않는다.
- code가 문서 의미를 요약하지 않는다.
- 여러 문서 종합 요약은 이번 설계의 기본 구현 후보가 아니다.
- L3 요약으로 node_3 원문 context를 대체하지 않는다.
- answer_basis_mode에 따라 원문/요약 공급량을 자동 조절하는 정책은 열지 않는다.
- 장기기억 DB, vector DB, scheduler, W/R loop, node_5 기억 압축은 열지 않는다.

## 선행 조건

- ORDER_124의 node_0 document material packet이 구현되어야 한다.
- 실제 `read_doc` 문서와 supplied context 문서의 경계가 계속 유지되어야 한다.
- L3 요약 결과가 node_3 답변에 들어가기 전 node_4 검토 경계를 설계해야 한다.

## 완료 조건

- `python -m compileall songryeon_core main.py`
- `python -m pytest`
- `python main.py smoke-test`
- L3 요약 frame schema 검증
- 담백 요약은 `relative/direct_record/one_document_to_one_summary`로 고정
- 상황 요약은 `mixed/source_bundle/one_document_plus_task_context`로 고정
- node_3 brief/payload가 L3 요약 material을 받되 raw internal ID를 LLM payload 본문 재료로 노출하지 않음
