# ORDER 250 실행 기록

- 날짜: 2026-07-11
- 결과: node_2 evidence ref schema repair 1회 경계 구현 및 검증 완료
- 발주서: `ORDER_250_NODE2_EVIDENCE_REF_SCHEMA_REPAIR_ONCE_V0.md`

## 1. 구현 배경

ORDER 249의 중단됐던 실제 Qwen 검증을 같은 짧은 입력으로 재개했다.

`안녕. 지금 송련이 어떤 방식으로 답하는지 한 문장으로 말해줘`

턴은 `status=ok`로 끝났고 L3의 운영 count는 code-owned 값으로 유지됐다.
그러나 node_2 Qwen payload의 일부 evidence role 항목에서 `evidence_ref` 또는
`evidence_role`이 누락돼 다음 schema failure가 발생했다.

`Node2 evidence role requires evidence_ref and evidence_role`

## 2. 구현

- 최초 node_2 answer-basis 호출과 validator는 그대로 유지했다.
- parse된 JSON의 schema 계약만 실패하면 동일 LLM에 repair 입력을 한 번 보낸다.
- repair 입력에는 실패 payload, validation error, 공식 evidence ref 표를 넣는다.
- code는 repair 결과의 ref membership과 실제 source data ID 복원만 담당한다.
- repair도 실패하면 기존 safe fallback으로 닫는다.

## 3. 회귀 테스트

새 파일:

- `tests/test_order_250_node2_evidence_ref_schema_repair.py`

확인한 것:

- 필수 evidence role 필드 누락은 LLM repair 1회 후 통과한다.
- repair가 선택한 `E004`는 `source:sample_boundary_record`로 복원된다.
- `E999`를 두 번 반환하면 계속 schema_failed fallback으로 닫힌다.
- 최초 payload가 유효하면 LLM 호출은 한 번뿐이다.

## 4. 실제 Qwen node_2 좁은 검증

전체 턴을 다시 반복하지 않고 같은 runtime 함수로 node_2만 실제 Qwen에 호출했다.

- generated_by: `LLM:qwen3:14b`
- failure_type: `none`
- answer_basis_mode: `mixed_or_uncertain`
- evidence role source: `source:sample_boundary_record`
- LLM call count: 1

이번 좁은 입력은 최초 호출부터 schema를 통과해 repair가 필요하지 않았다. repair
실행 경로는 deterministic adapter 테스트로 확인했다.

## 5. 별도 발견 위험

패치 전 전체 live 턴에서 node_3 Qwen은 code가 고정한 grounding block 아래 본문에
근거 없는 대량 처리 수치를 썼고, node_4 Qwen은 이를 `pass`로 놓쳤다.

- grounding block 자체의 code-owned count는 정확했다.
- 잘못된 수치는 LLM 본문에서 새로 생성됐다.
- 이는 의미 검사 실패이므로 숫자/단어 휴리스틱이나 code 의미 판단을 추가하지 않았다.
- Codex node_3/node_4 혼합 실행 또는 구조화 claim 경계의 후속 비교 대상으로 남긴다.

## 6. 검증

- `python -m compileall songryeon_core main.py`: 통과
- ORDER 249~250 좁은 pytest: 6 passed
- 전체 pytest: 416 passed, 5 deselected
- `python main.py smoke-test`: `SMOKE_TEST_OK`
- live Qwen 후 RTX 5080 상태: 정상, 최근 nvlddmkm/WHEA/Kernel-Power 사건 없음

## 7. 하지 않은 것

- validator 약화 없음
- 미등록 ref 자동 치환 없음
- code 의미 판단 없음
- node_4 문자열/숫자 휴리스틱 없음
- R-loop 수정 없음
