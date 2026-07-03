# ORDER 163: Vessel Inspect Manual Walk 실행 기록

## 날짜

2026-07-01

## 변경 요약

Neo4j Vessel에 기록된 graph memory를 읽기 전용으로 펼쳐보는 `vessel-inspect` CLI를 추가했다.

추가된 핵심 파일:

- `songryeon_core/core/graph_vessel_inspect.py`
- `songryeon_core/runtime/graph_vessel_inspect.py`
- `tests/test_order_163_vessel_inspect_manual_walk.py`

추가된 CLI:

```powershell
python main.py vessel-inspect --database neo4j
python main.py vessel-inspect --database neo4j --format text
```

## 확인 대상 경로

```text
CoreEgo -> HAS_AXIS -> TimeAxis -> HAS_BUNDLE -> TimeBundle -> CONTAINS_MEMORY -> RawCapsule
```

## 출력 형태

`GraphVesselNeo4jInspectResultFrame`은 다음을 기록한다.

- `inspect_status`
- `inspected_path_count`
- `core_count`
- `time_axis_count`
- `time_bundle_count`
- `raw_capsule_count`
- `path_items`
- `tree_lines`
- `source_data_ids`
- `source_trace_ids`

결과 frame은 다음으로 고정했다.

- `generated_by=CODE:GRAPH_VESSEL_NEO4J_INSPECTOR`
- `info_class=absolute`
- `semantic_judgement_status=not_run`

## 수동 CLI 확인

Codex 실행 환경에는 Neo4j password 환경변수가 설정되어 있지 않아 다음 결과가 나왔다.

```text
status: VESSEL_INSPECT_NOT_PASSED
inspect_status: adapter_unavailable
failure_type: neo4j_config_missing
failure_reason: Neo4j password is not configured.
```

이는 실패를 성공처럼 숨기지 않는 정상 동작이다. 사용자가 비밀번호 환경변수를 설정한 VS Code 터미널에서는 아래 명령으로 실제 inspect를 확인하면 된다.

```powershell
python main.py vessel-inspect --database neo4j --format text
```

## 검증

- `python -m compileall songryeon_core main.py`: 통과
- `python -m pytest tests/test_order_163_vessel_inspect_manual_walk.py -q`: 8 passed
- `python main.py fast-test --profile graph`: FAST_TEST_OK, 69 passed
- `python main.py smoke-test`: SMOKE_TEST_OK

## 남은 위험

- 현재 Codex 셸에는 Neo4j 비밀번호가 없어 실제 로컬 DB inspect pass는 사용자 터미널에서 확인해야 한다.
- 이번 작업은 수동 tree inspect까지만이며, R route/R1/R2/R3가 Vessel inspect 결과를 자동으로 사용하는 기능은 아직 열지 않았다.
- `python -m pytest` 전체는 최근 기준 약 17분이 걸리므로 이번 작업에서는 graph fast-test와 smoke-test를 우선 검증으로 사용했다.
