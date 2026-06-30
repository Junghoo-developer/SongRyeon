# ORDER_122 L Revision Unread Candidate Read Path Implementation 2026-06-28 001

## 작업 요약

L revision 흐름에서 `search_docs` 후보를 이미 확보했지만 `query` 예산이 소진된 경우, unread candidate를 `read_doc`으로 읽을 수 있는 경로를 열었다.

이번 변경은 예산을 늘리지 않았다. `read_doc`은 `query_count`를 증가시키지 않고, `read_doc_ids/read_doc_count`만 증가하도록 분리했다.

## 핵심 변경

- `L2RevisionInputFrame`에 `unread_candidate_doc_ids`를 추가해 revision L2가 읽을 수 있는 후보 ID를 절대정보로 받게 했다.
- 일반 L2는 기존처럼 `search_docs` / `read_artifact`만 허용하고, revision L2에서만 `read_doc` target을 허용했다.
- revision `read_doc` 후보는 `unread_candidate_doc_ids` 안의 정확한 `doc_id`일 때만 통과한다.
- `remaining_query_attempts=0`이면 revision plan은 `read_doc` 후보만 통과한다.
- continuation controller는 query 예산이 0이어도 unread candidate와 read budget이 있으면 `continue`로 열어 둔다.
- revision tool attempt는 `read_doc`을 실제 실행하고, `search_docs`만 `executed_queries/query_count`에 기록한다.

## 검증

- `python -m compileall songryeon_core main.py` 통과
- `python -m pytest tests/test_order_122_l_revision_read_doc_path.py -q` 통과: 4 passed
- `python -m pytest tests/test_order_120_tool_budget_diagnostics.py tests/test_order_121_answer_basis_and_l3_attitude.py -q` 통과: 11 passed
- `python -m pytest -q` 통과: 40 passed
- `python main.py smoke-test` 통과: `SMOKE_TEST_OK`
- `python main.py qwen-turn "...ORDER_100...ORDER_110..." --timeout 180 --pretty` 통과: `status=ok`
  - 이 live 입력은 explicit artifact/context pack 경로로 L3가 바로 `achieved` 처리되어 ORDER_122 revision read path 자체를 직접 밟지는 않았다.

## 남은 위험

- 실제 Qwen live에서는 revision L2가 unread candidate 중 어떤 문서를 읽을지 여전히 LLM 판단에 달려 있다.
- 이번 작업은 `node_3`가 많이 받은 문서를 정리/압축하는 문제를 해결하지 않는다.
- query novelty 판단, 검색 반복 억제, 문서 context pack 정리는 다음 발주 후보로 남긴다.
