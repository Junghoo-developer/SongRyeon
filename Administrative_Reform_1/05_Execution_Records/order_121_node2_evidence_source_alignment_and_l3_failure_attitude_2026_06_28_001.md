# ORDER_121 실행 기록 - node_2 evidence source 정렬과 L3 실패 태도 전달

## 작업 일시

2026-06-28

## 변경 요약

- `node_2 answer_basis` LLM 입력에 `available_evidence_sources` 표를 추가했다.
- `evidence_roles.source_data_id` 검증 기준을 `available_evidence_sources`와 같은 ID 목록으로 맞췄다.
- `Node2AnswerBasisFrame` validator는 약화하지 않았다.
- `Node3InputBriefFrame`에 L loop 반환 요약 필드를 추가했다.
- `node_3` grounding block과 LLM payload에 L 검색 목표 상태/실패/예산소진 신호를 전달했다.
- `node_4` prompt와 검사 목록에 L loop 실패/예산소진 신호를 검색 성공처럼 말하는지 확인하는 항목을 추가했다.

## 의도적으로 하지 않은 것

- L revision 검색 전략을 바꾸지 않았다.
- search 반복 억제, query novelty 판단, unread candidate direct read_doc 경로를 열지 않았다.
- W/R loop, scheduler, 외부 DB, 장기기억 DB, same-turn L reroute 횟수를 건드리지 않았다.

## 검증

- `python -m compileall songryeon_core main.py` 통과.
- `python -m pytest tests/test_order_121_answer_basis_and_l3_attitude.py` 통과: 4 passed.
- `python -m pytest tests/test_order_118_answer_basis.py tests/test_order_119_structure_failed_honesty.py tests/test_order_120_tool_budget_diagnostics.py` 통과: 17 passed.
- `python -m pytest tests/test_smoke_baseline.py -q` 통과: 1 passed.
- `python -m pytest -q` 통과: 35 passed.
- `python main.py smoke-test` 통과: `SMOKE_TEST_OK`.
- `git diff --check` 통과.

## 남은 위험

- L 검색 뺑뺑이 자체는 아직 해결하지 않았다.
- 이번 작업은 L3 실패/예산소진 신호가 downstream 답변 태도에 숨지 않게 하는 잠금이다.
- 실제 Qwen live에서 `node_2 answer_basis`가 새 `available_evidence_sources`를 안정적으로 따르는지는 별도 live 테스트가 필요하다.
