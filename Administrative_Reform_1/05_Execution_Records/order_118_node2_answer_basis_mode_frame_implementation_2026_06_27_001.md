# Execution Record: ORDER 118 Node2 Answer Basis Mode Frame Implementation 2026-06-27 001

## 목적

`ORDER_118_NODE2_ANSWER_BASIS_MODE_FRAME_V0.md`에 따라 node_2가 node_3에게 최종 답변의 근거 말하기 모드(`answer_basis_mode`)를 명시적으로 전달하도록 MVP를 구현했다.

## 구현 요약

- `Node2AnswerBasisFrame`을 추가했다.
- `answer_basis_mode` enum은 아래 3개로 고정했다.

```text
absolute_first
relative_allowed
mixed_or_uncertain
```

- node_2 answer-basis selector prompt를 추가했다.
- node_2가 LLM 선택에 성공하면 `generated_by=LLM:*`, `semantic_judgement_status=ran`으로 frame을 기록한다.
- node_2 LLM 선택이 실패하거나 adapter가 없으면 code가 의미 판단을 대신하지 않고 안전 fallback frame을 기록한다.
- node_3 input brief와 node_3 LLM payload에 answer-basis 정보를 연결했다.
- node_3 reporter prompt와 grounding block에 answer-basis 경계를 반영했다.
- node_4 gatekeeper prompt와 checks에 answer-basis 모드 검사를 추가했다.
- terminal/runtime view와 JSON summary에 answer-basis 상태를 표시했다.

## 주요 위치

- `Node2AnswerBasisFrame`: `songryeon_core/core/schemas.py`
- `answer_basis_mode` enum: `songryeon_core/core/schemas.py`의 `ANSWER_BASIS_MODES`
- node_2 mode 선택: `songryeon_core/nodes/node_2_metainfo_boundary.py`의 `run_node2_answer_basis_selection`
- node_2 prompt: `songryeon_core/prompts/node_2_answer_basis_selector_v0.md`
- node_3 brief 연결: `songryeon_core/nodes/node_2_handoff.py`의 `record_node3_input_brief`, `node3_brief_llm_payload`
- node_3 reporter 연결: `songryeon_core/nodes/node_3_reporter.py`
- node_4 guard prompt/check 연결: `songryeon_core/prompts/node_4_gatekeeper_v0.md`, `songryeon_core/nodes/node_4_gatekeeper.py`
- terminal/runtime 표시: `songryeon_core/runtime/terminal_view.py`, `songryeon_core/runtime/dry_run.py`, `main.py`, `songryeon_core/runtime/user_turn.py`

## code fallback 정책

LLM selection 실패 또는 adapter 미공급 시:

```text
answer_basis_mode = mixed_or_uncertain
basis_reason_codes = ["llm_mode_selection_failed"]
mode_selection_reason = "CODE_STATUS:node2_answer_basis_mode_selection_failed"
generated_by = CODE:FALLBACK
info_class = absolute_status
semantic_judgement_status = failed
evidence_roles = []
```

이 fallback은 의미상 mixed가 맞다는 판단이 아니라, 판단 실패를 불확실성 모드로 닫는 안전 상태다.

## node_2 prompt 교육 요약

새 prompt는 다음 경계를 교육한다.

- 절대정보: 코드/파일/trace/data/schema/tool result처럼 시스템이 값과 존재를 확인할 수 있는 정보
- 상대정보: 특정 하나의 절대정보 record/field에 대응하는 해석/판단/요약
- 혼합정보: 여러 절대정보 묶음 또는 하나로 고정하기 부적절한 source bundle에 근거한 해석/판단/요약
- answer-basis 선택은 보통 상대정보 또는 혼합정보이며, 절대정보 자체가 아님
- 불확실하면 `mixed_or_uncertain`을 선택

## node_3 brief 연결 방식

`Node3InputBriefFrame`에 다음 필드를 추가했다.

```text
answer_basis_frame_id
answer_basis_mode
basis_reason_codes
mode_selection_reason
mode_selection_reason_info_class
evidence_roles
answer_basis_generated_by
answer_basis_info_class
answer_basis_semantic_judgement_status
```

node_3 LLM payload에는 `answer_basis` object로 전달한다.
`evidence_roles`의 source는 raw internal ID 대신 안전한 source label로 바꿔 전달한다.

## node_4 변경 여부

node_4 guard를 제거하거나 약화하지 않았다.

추가한 것은 작다.

- prompt에 answer-basis별 검사 기준 추가
- node_4 입력 checks에 answer-basis 자세 확인 항목 추가

자동 재작성 루프는 열지 않았다.

## 추가 테스트

추가한 pytest:

- `tests/test_order_118_answer_basis.py::test_node2_answer_basis_absolute_first_fixture`
- `tests/test_order_118_answer_basis.py::test_node2_answer_basis_relative_allowed_fixture`
- `tests/test_order_118_answer_basis.py::test_node2_answer_basis_mixed_or_uncertain_fixture`
- `tests/test_order_118_answer_basis.py::test_node2_answer_basis_llm_failure_uses_code_fallback`
- `tests/test_order_118_answer_basis.py::test_node3_brief_receives_answer_basis_without_raw_id_leak_in_llm_payload`
- `tests/test_order_118_answer_basis.py::test_runtime_view_displays_answer_basis_fallback`

확장한 smoke:

- `run_smoke_tests()` 필수 data id에 `node_2:answer_basis_frame` 추가
- `_check_route2_handoff_and_brief()`에서 answer-basis frame과 node_3 brief 보존 검사 추가
- same-turn L 2회차 downstream scope smoke에 scoped answer-basis frame 검사 추가
- smoke-test 결과 JSON에 answer-basis 표시 추가

## 검증 결과

```powershell
python -m compileall songryeon_core main.py
```

결과: 통과.

```powershell
python -m pytest
```

결과: 20 passed in 247.35s.

```powershell
python main.py smoke-test
```

결과: `SMOKE_TEST_OK`.

확인된 smoke answer-basis 표시:

```text
node2_answer_basis_mode = mixed_or_uncertain
node2_answer_basis_reason_codes = ["llm_mode_selection_failed"]
node2_answer_basis_generated_by = CODE:FALLBACK
node2_answer_basis_semantic = failed
```

## 일부러 하지 않은 것

- `answer_basis_mode`를 3개보다 늘리지 않았다.
- `document_primary`, `recent_conversation_primary` 같은 세부 모드를 만들지 않았다.
- code가 의미적으로 모드를 고르도록 만들지 않았다.
- scheduler, 외부 DB, vector DB, 장기기억 DB를 건드리지 않았다.
- W/R loop를 열지 않았다.
- same-turn L reroute 횟수를 늘리지 않았다.
- node_4 자동 재작성 루프를 열지 않았다.
- node_4 기존 guard를 약화하지 않았다.
