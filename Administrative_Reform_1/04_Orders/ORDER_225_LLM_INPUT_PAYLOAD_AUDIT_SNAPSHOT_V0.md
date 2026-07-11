# ORDER 225: LLM Input Payload Audit Snapshot v0

## 상태

- Status: implemented
- Date: 2026-07-10
- Scope: LLM call audit only

## 배경

Vessel R 감사 중 R3는 `graph:axis:time`을 보고 `deeper`를 권고했지만, 다음 R2가 `none_selected`로 닫히는 사례가 있었다.
DataStore에는 LLM의 raw output과 검증 실패 이유는 남아 있었지만, 해당 LLM 호출에 실제로 어떤 input payload가 들어갔는지 직접 확인할 수 없었다.

따라서 `available_surface_refs`, `candidate_records_by_surface_ref` 같은 후보 번호표가 R2에게 실제로 전달됐는지 사후 감사하기 어려웠다.

## 목표

LLM 호출마다 입력 payload의 감사 가능한 절대정보를 `LLMCallFrame`에 남긴다.

## 변경

- `LLMCallFrame`에 입력 payload 감사 필드를 추가한다.
  - `input_payload_audit_status`
  - `input_payload_sha256`
  - `input_payload_json_char_count`
  - `input_payload_top_level_keys`
  - `input_payload_preview_json`
- `LLMNodeExecutor`가 LLM 호출을 기록할 때 input payload를 정규화 JSON으로 만들고 SHA-256, 문자 수, top-level key, 제한된 preview를 저장한다.
- preview는 대형 payload 폭탄을 피하기 위해 앞부분만 저장한다.
- 기존 `LLMCallFrame` 기본값은 유지하여 과거 record와 호환한다.

## 하지 않는 것

- R2/R3 선택 전략 변경 없음.
- R loop continuation 정책 변경 없음.
- LLM 입력 payload 전체 무제한 저장 없음.
- code가 LLM의 의미 판단을 대신하지 않음.
- W/R/scheduler/외부 장기기억 정책 확장 없음.

## 완료 조건

- 새 pytest로 LLM input payload audit snapshot이 기록되는지 확인한다.
- 기존 compile/test/smoke 경로를 깨지 않는다.
- 이후 R2/R3 감사에서 LLM이 실제 후보 번호표를 받았는지 DataStore에서 확인 가능해야 한다.
