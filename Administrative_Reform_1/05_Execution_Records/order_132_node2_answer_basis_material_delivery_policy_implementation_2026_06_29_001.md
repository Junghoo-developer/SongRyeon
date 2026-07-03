# ORDER_132 Node2 Answer Basis Material Delivery Policy Implementation 2026-06-29 001

## 작업 범위

- ORDER_132를 `요약 보조`가 아니라 `비-절대정보 모드에서 L3 요약이 node_3 LLM 입력의 원문 text를 대체`하는 정책으로 수정했다.
- 원문 document extract record는 DataStore에 그대로 보존하고, node_3 LLM payload에서만 raw text를 생략한다.
- `Node3MaterialDeliveryPolicyFrame`을 추가했다.
- `Node3InputBriefFrame`에 material delivery policy 요약 필드와 LLM payload 기준 count를 추가했다.
- node_2 handoff에서 policy frame을 별도 DataStore record로 저장한 뒤 node_3 brief에 연결했다.

## 정책 mapping

- `absolute_first` -> `raw_document_primary`
  - 원문 text를 node_3 LLM payload에 유지한다.
  - L3 요약은 보조 재료다.
- `relative_allowed` + L3 summary 있음 -> `l3_summary_replaces_raw_context`
  - 원문 text를 node_3 LLM payload에서 생략한다.
  - L3 요약을 labeled summary material로 사용한다.
- `mixed_or_uncertain` + L3 summary 있음 -> `l3_summary_replaces_raw_context_with_uncertainty`
  - 원문 text를 node_3 LLM payload에서 생략한다.
  - source-bundle/summary limit를 더 드러내게 한다.
- 비-절대정보 모드 + L3 summary 없음 -> `raw_document_fallback_no_l3_summary`
  - code가 요약을 대신 만들지 않고 원문 text를 유지한다.

## 주요 변경 파일

- `Administrative_Reform_1/04_Orders/ORDER_132_NODE2_ANSWER_BASIS_MATERIAL_DELIVERY_POLICY_V0.md`
- `songryeon_core/core/schemas.py`
- `songryeon_core/nodes/node_2_handoff.py`
- `songryeon_core/nodes/node_3_reporter.py`
- `songryeon_core/prompts/node_3_reporter_v0.md`
- `songryeon_core/runtime/terminal_view.py`
- `tests/test_order_132_material_delivery_policy.py`

## 검증한 경계

- 비-절대정보 모드에서 L3 summary가 있으면 `supplied_document_contexts`와 legacy `read_documents` payload에 raw `text`가 들어가지 않는다.
- raw document text가 payload에서 빠져도 DataStore의 원문 `tool_result:read_doc` payload는 유지된다.
- `absolute_first`에서는 L3 summary가 있어도 raw text가 유지된다.
- L3 summary가 없으면 비-절대정보 모드라도 raw fallback으로 닫힌다.
- grounding block에 `node_3 LLM 원문 text`와 `L3 문서별 요약 재료` count가 표시된다.
- terminal view에 material delivery policy가 표시된다.

## 검증 명령

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
git diff --check
```

## 결과

- `python -m compileall songryeon_core main.py`: 통과
- `python -m pytest`: `67 passed`
- `python main.py smoke-test`: `SMOKE_TEST_OK`

## 제외한 것

- 원문 DataStore record를 삭제하거나 변형하지 않았다.
- code가 문서 중요도나 관련성을 판단하지 않았다.
- node_0 요약, node_5 기억 압축, 장기기억 DB, vector DB, scheduler는 열지 않았다.
- W/R loop와 same-turn L reroute 횟수는 건드리지 않았다.
- node_4 자동 재작성 루프는 열지 않았다.
