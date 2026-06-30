# ORDER_138_INTEGRATION_BASELINE_AND_DIRTY_WORKTREE_RECONCILIATION_V0

## 1. 목표

ORDER_133 이후 codebase inspection, L tool scope, code evidence accounting, source-code outline, 그리고 심야정부 MVP가 빠르게 들어왔다.

이번 발주는 새 기능을 추가하지 않고, 현재 작업트리 상태를 기준선으로 묶어 다음 개발자가 길을 잃지 않게 한다.

## 2. 배경

최근 개발 흐름은 다음과 같다.

- ORDER_133: read-only codebase inspection 도구 추가
- ORDER_134: L tool scope와 도구군별 예산 분배 추가
- ORDER_135: `read_code_file`을 `read_doc`과 분리해 source-code evidence로 인정
- ORDER_136: 현재 capability baseline과 live test pack 문서화
- ORDER_137: `read_code_file` source-code outline을 node_3 coverage checklist로 공급
- 심야정부 MVP: JSONL 기반 외부 기억 DB와 active memory packet CLI 추가

심야정부 MVP는 검증을 통과했지만, 정식 발주서 없이 먼저 구현되어 문서-현실 불일치가 생겼다.

## 3. 이번 발주 범위

1. 현재 작업트리의 기능 확장 상태를 감사한다.
2. ORDER/Execution Records README가 최신 상태인지 확인한다.
3. 전체 검증 명령을 다시 실행해 통합 기준선을 기록한다.
4. 심야정부 MVP를 다음과 같이 분류한다.
   - 현재 상태: provisional external memory DB MVP
   - 검증 상태: local tests, full pytest, smoke-test 통과
   - 아직 아님: 송련식 메타정보 provenance DB
5. 다음 발주 후보를 분리한다.
   - 심야정부를 `info_class`, `source_mode`, `claim_alignment`, `semantic_judgement_status`, `source_data_ids/source_trace_ids` 기반으로 정렬하는 별도 발주
   - schema/test 파일 비대화 추가 분해 발주

## 4. 금지

- 새 runtime 기능 추가 금지.
- 심야정부 active packet을 0 기억공급관에 자동 주입하지 않는다.
- 외부 DB를 SQLite/Neo4j로 교체하지 않는다.
- 기존 사용자/다른 채팅방 변경을 되돌리지 않는다.
- 대량 리팩터링을 이번 발주에 끼워 넣지 않는다.

## 5. 완료 조건

1. `python -m compileall songryeon_core main.py`
2. `python -m pytest`
3. `python main.py smoke-test`
4. `git diff --check`
5. 실행 기록에 다음을 남긴다.
   - 현재 dirty worktree 요약
   - ORDER_133~137 및 심야정부 MVP 상태
   - 전체 검증 결과
   - 다음 위험과 다음 발주 후보

## 6. 다음 발주 후보

### ORDER_139_NIGHT_GOVERNMENT_METAINFO_ALIGNMENT_V0

심야정부 `MemoryRecord`와 `MemoryActivationItem`을 송련 메타정보 원칙에 맞춘다.

필수 방향:

- `memory_role`과 `info_class`를 분리한다.
- relative/mixed memory record는 orphan 금지.
- relative는 단일 source record/field가 필요하다.
- mixed는 source bundle이 필요하다.
- activation item은 현재 턴에 들어올 때 사용 권한과 한계를 표시한다.

### Schema/Test Refoundation Follow-up

`schemas.py`, `smoke_test.py`, ORDER별 pytest helper가 다시 커지고 있으므로, 다음 큰 기능 전 추가 분해를 검토한다.
