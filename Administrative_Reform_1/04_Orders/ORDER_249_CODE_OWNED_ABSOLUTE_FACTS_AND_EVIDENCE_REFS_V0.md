# ORDER 249: Code-Owned Absolute Facts And Evidence Refs v0

## 1. 목표

Qwen에게 절대 count를 다시 세거나 긴 내부 ID를 정확히 복사하게 한 경계를 줄인다.
코드는 절대정보 계산·복사를 맡고, Qwen은 의미 적합성과 근거 역할만 판단한다.

## 2. 확인된 실패

- L3 입력의 실제 count는 candidate 13, search document 11, read_doc 1,
  read_code_file 0이었다.
- Qwen L3 이유문은 3, 5, 3, 2로 count를 잘못 서술했다.
- node_2는 허용된 `L3:achievement_frame` 대신 파생 혼합정보 ID
  `mixed:L3_achievement_frame:reason`을 evidence source로 제출했다.
- node_2 validator는 이를 정확히 막고 safe fallback으로 닫았다.

## 3. L3 경계

- L3 운영 상태와 count는 기존 code operation check를 기준으로 삼는다.
- Qwen L3가 반환한 운영 count·운영 이유는 authoritative frame에 복사하지 않는다.
- Qwen은 `semantic_goal_match_status`와 그 의미 이유만 생성한다.
- Qwen 입력에는 계획·예산 count와 실제 count를 한꺼번에 주지 않는다.
- 실제 read/search/candidate count와 ID는 code frame에 그대로 보존한다.
- 의미 판단은 code operation status를 낮출 수 있지만 올리지는 못한다.

## 4. node_2 evidence ref 경계

- Qwen에게 raw `source_data_id`, `info_id`, trace ID를 선택 대상으로 함께 주지 않는다.
- code가 `E001`, `E002` 형식의 evidence ref table을 만든다.
- Qwen은 evidence ref와 의미 역할·이유만 반환한다.
- code가 evidence ref를 실제 `source_data_id`로 복원한다.
- 알려지지 않은 ref는 schema failure로 닫고 의미 fallback을 만들지 않는다.
- 최종 Node2AnswerBasisFrame에는 기존 실제 source_data_id를 보존한다.

## 5. 검증

1. L3 raw output에 잘못된 count가 있어도 authoritative L3 reason/count가 code
   operation facts를 유지한다.
2. Qwen L3 의미 판단은 semantic fields에만 반영된다.
3. node_2의 `E001` 선택이 정확한 source_data_id로 복원된다.
4. info sample ID나 미등록 evidence ref는 실패한다.
5. compileall, pytest, smoke-test가 통과한다.

## 6. 별도 감사

R1/R2/R3에서 LLM에게 count 계산, raw graph ID 복사, child membership 검사를
시키는 경계가 있는지 감사한다. R-loop 수정은 별도 결재 전에는 하지 않는다.

## 7. 금지

- 단어 조합 휴리스틱 추가 금지
- code의 의미 관련성 판단 금지
- validator 약화 금지
- L/R 라우팅 의미 변경 금지
- R-loop 동시 수정 금지
