# ORDER_111 node_1 recent memory router visibility 실행 기록

## 목적

node_1 router가 라우팅 전에 이미 생성된 최근 기억 선택 결과와 selected recent memory context를 볼 수 있게 했다.

이 작업은 장기기억 확장이나 요약 기억 구현이 아니다.

## 변경 파일

- `Administrative_Reform_1/04_Orders/ORDER_111_NODE1_RECENT_MEMORY_ROUTER_VISIBILITY_V0.md`
- `songryeon_core/runtime/dry_run.py`
- `songryeon_core/nodes/node_1_router.py`
- `songryeon_core/prompts/node_1_router_v0.md`
- `songryeon_core/llm/fake.py`
- `songryeon_core/runtime/smoke_test.py`
- `Administrative_Reform_1/00_Philosophy/Answer_Basis_Mode_And_Evidence_Role_Philosophy_2026_06_26.md`
- `Administrative_Reform_1/05_Execution_Records/answer_basis_mode_philosophy_and_learning_2026_06_26_001.md`

## 구현 내용

첫 node_1 라우팅의 `source_data_ids`에 다음 record를 포함했다.

- `memory_packet:node_1:pre_route_report`
- `memory_packet:node_1:pre_route_report:memory_relevance_selection`
- `memory_packet:node_1:pre_route_report:memory_relevance_selection:selected_recent_memory_context`

`node_1_router.py`는 이 source record들에서 다음 payload를 만들어 LLM router 입력에 넣는다.

```text
recent_memory_router_context
```

그 안에는 다음이 들어간다.

- memory relevance selection records
- selected recent memory context records
- selected recent memory context count
- selection statuses

## 경계

코드가 최근 기억 관련성을 새로 판단하지 않는다.

관련성 판단은 기존 memory relevance selector의 LLM output으로 남고, node_1은 supplied context를 보고 라우팅 이유를 쓰는 LLM router 책임으로 둔다.

키워드 기반으로 "암구호", "방금", "기억" 같은 단어를 보고 code가 route=2를 강제하지 않았다.

## smoke 확인

추가 smoke:

```text
node1_recent_memory_router_visibility_route=2
node1_recent_memory_router_visibility_context_seen=True
node1_recent_memory_router_visibility_source_ids=True
```

검증:

```powershell
python -m compileall .\songryeon_core .\main.py
python .\main.py smoke-test
```

결과:

```text
compileall passed
SMOKE_TEST_OK
```

첫 smoke-test 실행은 120초 제한에서 timeout이 났고, 300초 제한으로 재실행해 통과했다.

## 후속

기존 철학 문서의 answer basis mode 후보 번호는 `ORDER_112_NODE2_ANSWER_BASIS_MODE_FOR_NODE3_V0`로 밀었다.

다음 병목은 여전히 node_2/node_3가 답변 근거 우선순위를 명확히 받는 answer basis mode다.
