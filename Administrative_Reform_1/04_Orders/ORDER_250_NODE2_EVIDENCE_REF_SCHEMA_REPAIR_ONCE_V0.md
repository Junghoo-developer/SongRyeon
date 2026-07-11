# ORDER 250: Node2 Evidence Ref Schema Repair Once v0

## 1. 목표

ORDER 249의 evidence ref 경계는 유지하면서, node_2 Qwen이 JSON 항목을 빠뜨린
경우 동일 LLM이 공식 evidence ref 표를 보고 형식만 한 번 고치게 한다.

## 2. 확인된 live 실패

- ORDER 249 live Qwen 턴에서 L3의 code-owned count는 정상 보존됐다.
- node_2 Qwen은 parse 가능한 JSON을 반환했지만 일부 `evidence_roles` 항목에
  `evidence_ref` 또는 `evidence_role`을 빠뜨렸다.
- validator는 이를 `schema_failed`로 정확히 차단했다.

## 3. 구현 경계

- 최초 node_2 answer-basis 호출은 기존 입력과 validator를 그대로 사용한다.
- parse 성공 후 schema validation만 실패한 경우에만 repair를 한 번 허용한다.
- repair 입력에는 실패 payload, validation error, 공식 evidence ref 표를 넣는다.
- repair 판단과 역할 선택은 동일 LLM이 한다.
- code는 evidence ref를 실제 source data ID로 복원하고 membership만 검사한다.
- repair도 실패하면 기존 `mixed_or_uncertain + llm_mode_selection_failed`로 닫는다.

## 4. 별도 위험 기록

동일 live 턴에서 node_3 Qwen이 grounding block 아래 본문에 근거 없는 대량 수치를
썼고 node_4 Qwen이 이를 통과시켰다. 이는 의미 검사 실패로 기록하되, 이번 발주에서
단어/숫자 휴리스틱을 추가하거나 code가 의미 판단을 대신하지 않는다. Codex node_4
혼합 경계와 구조화 claim 검사는 별도 후속 논의 대상으로 남긴다.

## 5. 검증

1. 첫 payload의 evidence role 필드 누락이 repair 1회 후 통과한다.
2. repair가 선택한 공식 ref를 code가 실제 source data ID로 복원한다.
3. 두 번 모두 미등록 ref를 반환하면 기존 fallback으로 닫힌다.
4. 최초 payload가 정상이라면 repair를 실행하지 않는다.
5. compileall, 관련 pytest, smoke-test가 통과한다.

## 6. 금지

- validator 약화 금지
- code 의미 선택 금지
- 미등록 evidence ref 자동 치환 금지
- 문자열/숫자 휴리스틱 추가 금지
- R-loop 동시 수정 금지
