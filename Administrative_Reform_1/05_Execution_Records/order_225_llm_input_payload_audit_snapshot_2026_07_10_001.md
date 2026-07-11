# ORDER 225 실행 기록: LLM Input Payload Audit Snapshot

## 일시

- 2026-07-10

## 목적

Vessel R 감사에서 R2/R3 LLM 호출이 실제로 어떤 후보 번호표와 payload를 받았는지 확인할 수 있도록 `LLMCallFrame`에 입력 payload 감사 스냅샷을 추가했다.

## 구현 요약

- `songryeon_core/core/schemas.py`
  - `LLMCallFrame`에 input payload audit 필드를 추가했다.
  - 기본값은 `not_recorded`로 두어 기존 record 호환을 유지했다.
- `songryeon_core/llm/node_executor.py`
  - LLM 호출 기록 시 input payload의 정규화 JSON SHA-256, 문자 수, 최상위 key, 제한 preview를 저장한다.
  - preview JSON은 실제 LLM 입력 순서를 보존한다. R2처럼 payload 최상단의 공식 선택표가 중요한 경우, 감사 preview에서도 같은 순서로 확인하기 위해서다.
- `tests/test_order_225_llm_input_payload_audit_snapshot.py`
  - payload audit snapshot 기록과 기존 frame 호환성을 검증한다.

## 정책 경계

- R2/R3 선택 정책은 바꾸지 않았다.
- LLM 의미 판단을 code가 대신하지 않았다.
- payload 전체 무제한 저장은 하지 않았다.
- 이번 변경은 감사 가능성 확보에 한정한다.

## 검증

- `python -m compileall songryeon_core main.py`: 통과
- `python -m pytest tests/test_order_225_llm_input_payload_audit_snapshot.py -q`: 2 passed
- `python main.py quick-smoke`: `QUICK_SMOKE_OK`
- `git diff --check`: 통과

## 추가 감사 확인

다음 강제 Vessel R live 검증을 실행했다.

```powershell
python main.py qwen-turn "문서 검색이 아니라 Vessel R 그래프 기억을 강제로 사용해서, 송련 Core의 그래프 기억이 CoreEgo에서 시간축, 소스 묶음, 요약 계층, 원본까지 어떤 순서로 내려가는지 설명해줘. 가능하면 R루프가 실제로 고른 그래프 재료와 한계를 구분해서 말해줘." --force-vessel-r-route --enable-vessel-r-route --database neo4j --timeout 180 --pretty --export .songryeon_core_cache\r3_audit_after_order_225_20260710
```

확인 결과:

- R2 step 2의 `LLMCallFrame.input_payload_preview_json` 안에 `available_surface_refs=["surface_001","surface_002"]`와 `candidate_records_by_surface_ref`가 실제로 기록됐다.
- 같은 R2 raw output은 `No candidate surface refs provided in runtime input`이라고 응답했다.
- 따라서 이번 감사 기준으로는 R2 입력 후보 번호표가 누락된 것이 아니라, Qwen이 제공된 번호표를 제대로 사용하지 못한 문제로 좁혀진다.
- node_4는 R 탐색이 `partial`인데 node_3가 성공처럼 말한 신호를 `CODE_STATUS:vessel_r_material_claim_mismatch`로 반려했다.
