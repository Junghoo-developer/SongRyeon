# night_government_mvp_removed_2026_06_30_001

## 1. 작업 요약

외부 채팅방에서 먼저 구현된 심야정부 MVP를 송련 Core 런타임에서 제거했다.

제거 판단:

- `MemoryRecord`는 기존 TurnStateCapsule/TraceStore/DataStore 좌표를 재사용하지 않는 별도 JSONL 기억 카드였다.
- `NightGovernmentPacket`은 송련의 0 기억공급관이나 캡슐 계층과 연결되지 않은 독립 active packet이었다.
- `MemoryActivationItem`은 기존 메타정보 출처 체계와 정렬되지 않은 별도 활성화 항목이었다.
- 따라서 현재 상태로는 송련 Core의 "절대정보에서 상대/혼합정보가 파생된다"는 원칙을 강화하기보다, 중복 기억 저장소를 만들 위험이 컸다.

## 2. 제거한 것

- `songryeon_core/night_government/__init__.py`
- `songryeon_core/night_government/runtime.py`
- `songryeon_core/night_government/schemas.py`
- `songryeon_core/night_government/store.py`
- `tests/test_night_government_mvp.py`
- `main.py`의 `night-ingest`, `night-run`, `night-active` CLI

## 3. 남긴 것

- ORDER_138과 관련 실행 기록은 과거 감사 자료로 남겼다.
- 단, 두 문서 상단에 심야정부 MVP가 제거되었고 재설계 기준으로 쓰면 안 된다는 상태 표시를 추가했다.

## 4. 향후 원칙

심야정부나 외부 DB 기억 체계를 다시 열 경우, 다음 조건을 먼저 만족해야 한다.

- 기존 TurnStateCapsule/TraceStore/DataStore 좌표를 우선 사용한다.
- relative/mixed 정보는 orphan으로 저장하지 않는다.
- 외부 DB record는 `info_class`, `generated_by`, `semantic_judgement_status`, `source_trace_ids`, `source_data_ids` 같은 송련 메타정보 경계를 먼저 갖춘다.
- 0 기억공급관과의 연결은 별도 발주와 smoke-test를 둔다.

## 5. 검증 결과

다음 명령을 실행했다.

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
```

결과:

- `compileall`: 통과
- 전체 `pytest`: `77 passed`
- `smoke-test`: `SMOKE_TEST_OK`

참고:

- 제거 전 전체 pytest는 심야정부 전용 테스트 2개를 포함해 `79 passed`였다.
- 제거 후 `tests/test_night_government_mvp.py`를 삭제했기 때문에 전체 pytest 수가 `77`로 줄어든 것은 의도된 결과다.
