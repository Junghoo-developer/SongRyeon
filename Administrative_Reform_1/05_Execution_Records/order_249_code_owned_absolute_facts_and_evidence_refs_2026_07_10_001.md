# ORDER 249 실행 기록

- 날짜: 2026-07-10
- 결과: L3 운영 절대정보 code ownership 및 node_2 evidence ref 경계 구현 완료
- 발주서: `ORDER_249_CODE_OWNED_ABSOLUTE_FACTS_AND_EVIDENCE_REFS_V0.md`

## 1. 구현 배경

ORDER 248 실제 Qwen 턴 감사에서 두 문제가 확인됐다.

- L3 입력의 실제 값은 candidate 13, search document 11, read_doc 1,
  read_code_file 0이었지만 Qwen 이유문은 3, 5, 3, 2라고 잘못 썼다.
- node_2는 허용된 `L3:achievement_frame` 대신 파생 정보 ID를 evidence source로
  제출해 schema_failed fallback으로 닫혔다.

두 문제 모두 Qwen의 의미 판단 능력보다 code가 이미 아는 숫자와 긴 ID를 다시
생성·복사시키던 경계가 원인이었다.

## 2. L3 변경

- L3 운영 상태, candidate count, read/search ID, controller 상태는 기존
  `CODE:OPERATION_CHECK` frame이 authoritative source다.
- L3 Qwen 출력은 `semantic_goal_match_status`와
  `semantic_goal_match_reason`만 받는다.
- Qwen이 이전 형식의 achievement status, 운영 이유, 잘못 센 count를 추가로
  반환해도 authoritative L3 frame에는 복사하지 않는다.
- Qwen 입력에서 계획 예산 숫자, 실제 count 묶음, raw source data ID를 제거했다.
- 의미 적합성 판단이 partial/missing이면 기존 code semantic guard가 운영 상태를
  낮출 수 있지만 Qwen이 code 상태를 올리지는 못한다.

## 3. node_2 변경

- code가 허용 근거를 `E001`, `E002` 형식의 evidence ref table로 만든다.
- node_2 Qwen에는 `evidence_ref`, `source_label`, `source_kind`만 제공한다.
- absolute/relative/mixed sample도 raw `info_id`, `source_data_id`, trace ID 대신
  evidence ref와 사람이 읽을 정보만 제공한다.
- Qwen은 evidence ref와 근거 역할·이유만 반환한다.
- code가 evidence ref를 실제 source data ID로 복원해 기존
  `Node2AnswerBasisFrame`에 보존한다.
- 미등록 `E999` 같은 ref는 기존처럼 schema_failed safe fallback으로 닫는다.

## 4. 회귀 테스트

새 파일:

- `tests/test_order_249_code_owned_absolute_facts_and_evidence_refs.py`

확인한 것:

- Qwen이 잘못된 운영 숫자를 반환해도 L3 count와 운영 이유는 code 값을 유지한다.
- Qwen 의미 적합성 필드만 L3 frame에 반영된다.
- node_2 입력에는 raw source/info ID가 없고 `E001` 계열 번호표만 있다.
- `E004`가 실제 `source:sample_boundary_record`로 복원된다.
- `E999`는 schema_failed fallback으로 닫힌다.

## 5. R-loop 추가 감사

별도 기록:

- `r_loop_code_owned_absolute_facts_boundary_audit_2026_07_10_001.md`

결론:

- R2 공식 ref 선택과 code ID 복원·membership 검사는 이미 안전하다.
- R3 child count/ID/depth/leaf count는 code가 기록하고, LLM은 충분성·농도·가지
  판단만 한다.
- 즉시 수정할 R count 오염은 확인되지 않았다.
- 후속 후보는 R1 anchor ID code assembly와 R1/R2/R3 입력의 불필요한 내부 ID
  축소다. 이번 발주에서는 R 코드를 수정하지 않았다.

## 6. 검증

- `python -m compileall songryeon_core main.py`: 통과
- ORDER 249 전용 pytest: 3 passed
- 관련 L3/node_2/R 경계 pytest: 47 passed
- 전체 pytest: 413 passed, 5 deselected
- `python main.py smoke-test`: SMOKE_TEST_OK

## 7. live Qwen 검증 중단 사유

ORDER 248과 같은 입력으로 실제 Qwen 턴을 실행했으나 출력 전에 RTX 5080이
시스템에서 이탈했다.

- `nvidia-smi`: `GPU is lost. Reboot the system to recover this GPU`
- 남은 RTX 2080 Ti: utilization 0%
- Windows System log: 2026-07-10 22:09:48, WHEA-Logger event 17,
  PCI Express Root Port corrected hardware error
- Windows AC display/sleep/hibernate timeout: 모두 0(사용 안 함)

따라서 live Qwen 검증은 코드 실패나 timeout으로 판정하지 않고 hardware interruption
상태로 기록한다. pytest와 smoke는 GPU 이탈 전에 모두 통과했다.

## 8. 하지 않은 것

- 단어 휴리스틱 추가 없음
- node_2/L3 의미 판단을 code가 대신하지 않음
- validator 약화 없음
- R route/R1/R2/R3 기능 변경 없음
- L/R 예산과 반복 횟수 변경 없음
- GPU 재부팅이나 장치 설정 변경 없음
