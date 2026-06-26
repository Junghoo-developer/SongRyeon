# ORDER 098 실행 기록: run-aware terminal/final renderer v0

## 상태

구현 및 검증 완료.

## 감사 결과

`read_doc` 수량 혼동의 실제 원인은 서로 다른 기준을 같은 이름으로 표시한 데 있었다.

- `node_3 input brief`는 `tool_result:read_doc` / `tool_result:read_artifact` 중 `payload.text`가 비어 있지 않은 문서만 보고 가능한 문서로 세었다.
- 기존 `route=2 handoff` 계열 구현은 문서 extract record 자체를 넓게 세는 흐름이 있었고, 빈/실패 `read_artifact`도 같은 숫자로 섞일 수 있었다.
- ORDER_098 스키마에는 `reportable_document_count`, `raw_document_extract_record_count`, `empty_document_extract_record_count`가 이미 준비돼 있었지만, builder와 renderer가 run-aware 기준으로 충분히 묶이지 않은 상태였다.

## 구현 내용

- `node_2_handoff.py`
  - 최신/현재 L run namespace에 속한 search/read/revision record를 기준으로 downstream count를 계산하게 했다.
  - `reportable_document_count`, `raw_document_extract_record_count`, `empty_document_extract_record_count`를 분리했다.
  - 호환 필드 `read_doc_count`는 `reportable_document_count`만 mirror하게 했다.
  - 실제 L run 수, 차단된 same-turn top-level L reroute 요청 수, L 내부 revision record 수를 별도 절대정보로 기록했다.
  - `route_path`에서 실제 실행된 L run과 controller가 차단한 추가 L 요청을 분리해 표시하게 했다.
  - node_3 brief와 LLM payload에 최종 보고자 정체성 경계를 추가했다.

- `terminal_view.py`
  - L1/L2/L3/downstream/report/gatekeeper 표시에서 최신 run-scoped record를 우선 사용한다.
  - terminal handoff 표시에서 `read_doc=...` 대신 `reportable_documents`, `raw_extract_records`, `empty_extract_records`를 분리해 보여준다.
  - terminal에 `actual_l_runs`, `blocked_top_level_l_requests`, `l_internal_revision_records`를 분리해 보여준다.
  - fallback final answer에서 `source_data_ids`, `copied_from`, `L:run:*` 같은 raw internal ID 노출을 제거했다.

- `node_3_reporter_v0.md`
  - node_3 최종 응답자가 자신을 `node_0/node_1/node_2/node_3` 같은 내부 노드명으로 정의하지 말라는 경계를 보강했다.

## 검증

통과:

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
```

smoke-test 결과 중 ORDER_098 관련 확인값:

- `runtime_count_reportable_documents`: 2
- `runtime_count_raw_extract_records`: 3
- `runtime_count_empty_extract_records`: 1
- `same_turn_l_reroute_policy_run_count`: 2
- `same_turn_l_reroute_third_run_blocked`: true

추가 수동 확인:

- policy-enabled same-turn L reroute 샘플에서 terminal은 `L:run:0002` L1/L2 자료를 우선 표시했다.
- 같은 샘플에서 route path는 실제 `run=1`, 실제 `run=2`, 차단된 추가 `route=L` 요청을 분리해 표시했다.
- final answer 영역에는 `L:run:` 및 `source_data_ids:`가 노출되지 않았다.
