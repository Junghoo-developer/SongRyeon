# order_138_integration_baseline_dirty_worktree_reconciliation_2026_06_30_001

## Status Note

2026-06-30 이후 감사와 사용자 결재에 따라, 이 기록에 포함된 심야정부 MVP(`songryeon_core/night_government`, `night-*` CLI, `tests/test_night_government_mvp.py`)는 송련 Core의 기존 TurnStateCapsule/TraceStore/ZeroState 기반 기억 체계와 맞지 않는 외부 provisional 구현으로 판단되어 제거되었다.

이 기록은 과거 기준선 감사 자료로만 남기며, 심야정부 재설계의 구현 기준으로 사용하지 않는다.

## 1. 작업 요약

ORDER_138을 작성하고 현재 작업트리 기준선을 감사했다.

이번 작업은 새 runtime 기능 구현이 아니라, ORDER_133~137 및 심야정부 MVP가 빠르게 들어온 뒤 현재 상태를 추적 가능하게 묶는 정리 작업이다.

## 2. 현재 확인한 기능 상태

### ORDER_133~137

- ORDER_133: read-only codebase inspection MVP가 들어와 `code_tools.py` 기반 코드 파일 목록/검색/읽기 도구를 제공한다.
- ORDER_134: L loop가 L2 도구 선택 전에 tool scope와 도구군별 예산 분배를 만든다.
- ORDER_135: `read_code_file` 결과가 `read_doc`과 분리되어 L3/node_3에서 source-code evidence로 인정된다.
- ORDER_136: current capability baseline과 live test pack이 문서화되었다.
- ORDER_137: `read_code_file` 원문에서 source-code outline을 만들어 node_3 coverage checklist로 공급한다.

### 심야정부 MVP

현재 심야정부 MVP는 다음 파일로 들어와 있다.

- `songryeon_core/night_government/schemas.py`
- `songryeon_core/night_government/store.py`
- `songryeon_core/night_government/runtime.py`
- `tests/test_night_government_mvp.py`
- `main.py`의 `night-ingest`, `night-run`, `night-active` CLI

검증 결과, 심야정부 MVP 자체는 작동한다.

다만 현재 상태는 `memory_role` 기반 JSONL 외부 기억장 MVP다.
아직 송련식 메타정보 provenance DB로 정렬되지는 않았다.

부족한 필드/경계:

- `info_class`
- `generated_by`
- `source_mode`
- `claim_alignment`
- `semantic_judgement_status`
- `source_data_ids`
- `source_trace_ids`

따라서 심야정부는 다음 단계에서 메타정보 정렬 발주가 필요하다.

## 3. 작업트리 상태

`git status --short` 기준으로 작업트리는 여전히 매우 dirty하다.

특징:

- 기존 tracked 파일 다수가 수정되어 있다.
- ORDER_118~138 문서 다수가 아직 untracked 상태다.
- ORDER별 테스트 파일 다수가 아직 untracked 상태다.
- 심야정부 새 패키지도 아직 untracked 상태다.
- 이번 작업에서는 사용자/다른 채팅방 변경을 되돌리지 않았다.

특히 심야정부 MVP는 구현과 검증은 되었지만, 정식 발주 문서 없이 먼저 들어온 기능이므로 ORDER_138에서 provisional 상태로 기록했다.

## 4. 검증 결과

다음 명령을 실행했다.

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_night_government_mvp.py -q
python -m pytest
python main.py smoke-test
git diff --check
```

결과:

- `compileall`: 통과
- `tests/test_night_government_mvp.py`: `2 passed`
- 전체 `pytest`: `79 passed`
- `smoke-test`: `SMOKE_TEST_OK`
- `git diff --check`: 통과

## 5. 남은 위험

1. 심야정부 MVP는 아직 0 기억공급관과 연결되지 않았다.
2. 심야정부 record는 아직 송련 메타정보 정책의 `absolute/relative/mixed` 분류를 강제하지 않는다.
3. 상대/혼합 기억 record가 절대정보 source 없이 저장되는 것을 막는 validator가 아직 없다.
4. `schemas.py`, `smoke_test.py`, 일부 node 파일이 다시 커지고 있다.
5. 작업트리가 매우 dirty하므로, 다음 기능 확장 전 commit/PR 단위 정리 또는 최소 staging 기준 합의가 필요하다.

## 6. 다음 권장 발주

### ORDER_139_NIGHT_GOVERNMENT_METAINFO_ALIGNMENT_V0

심야정부 record를 송련 메타정보 원칙에 맞춘다.

핵심:

- `memory_role`과 `info_class` 분리
- relative는 단일 source 필요
- mixed는 source bundle 필요
- orphan relative/mixed record 금지
- active packet이 다음 턴에 들어올 때 사용 권한과 한계 표시

### Schema/Test 추가 정리

외부 DB를 더 키우기 전에 schema/test 비대화의 2차 분해를 검토한다.
