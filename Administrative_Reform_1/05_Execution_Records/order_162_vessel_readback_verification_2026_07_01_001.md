# ORDER 162: Vessel Readback Verification 실행 기록

## 날짜

2026-07-01

## 변경 요약

Neo4j Vessel에 기록된 graph memory가 사람이 보는 label/relationship vocabulary로 다시 읽히는지 확인하는 read-only verifier를 추가했다.

추가된 핵심 파일:

- `songryeon_core/core/graph_vessel_readback.py`
- `songryeon_core/runtime/graph_vessel_readback.py`
- `tests/test_order_162_vessel_readback_verification.py`

추가된 CLI:

```powershell
python main.py vessel-readback --database neo4j
```

## 확인 대상 경로

```text
CoreEgo -> HAS_AXIS -> TimeAxis -> HAS_BUNDLE -> TimeBundle -> CONTAINS_MEMORY -> RawCapsule
```

## 기록되는 절대정보

- `readback_status`
- `core_path_exists`
- `core_path_count`
- `vessel_record_count`
- `vessel_relationship_count`
- `core_ego_count`
- `time_axis_count`
- `time_bundle_count`
- `raw_capsule_count`
- `has_axis_count`
- `has_bundle_count`
- `contains_memory_count`
- `required_property_missing_count`

결과 frame은 다음으로 고정했다.

- `generated_by=CODE:GRAPH_VESSEL_NEO4J_READBACK_VERIFIER`
- `info_class=absolute`
- `semantic_judgement_status=not_run`

## 수동 CLI 확인

Codex 실행 환경에는 Neo4j password 환경변수가 설정되어 있지 않아 다음 결과가 나왔다.

```text
readback_status=adapter_unavailable
failure_type=neo4j_config_missing
failure_reason=Neo4j password is not configured.
```

이는 실패를 성공처럼 숨기지 않는 정상 동작이다. 사용자가 비밀번호 환경변수를 설정한 VS Code 터미널에서는 아래 명령으로 실제 readback을 확인하면 된다.

```powershell
python main.py vessel-readback --database neo4j
```

## 검증

- `python -m compileall songryeon_core main.py`: 통과
- `python -m pytest tests/test_order_162_vessel_readback_verification.py -q`: 8 passed
- `python main.py fast-test --profile graph`: FAST_TEST_OK, 61 passed
- `python main.py smoke-test`: SMOKE_TEST_OK
- `python -m pytest -q`: 192 passed in 1030.04s

## 남은 위험

- 현재 Codex 셸에는 Neo4j 비밀번호가 없어 실제 로컬 DB readback pass는 사용자 터미널에서 확인해야 한다.
- `python -m pytest`는 smoke 전체를 포함해 약 17분이 걸린다. 빠른 회귀 확인은 `python main.py fast-test --profile graph`를 우선 사용한다.
- 이번 작업은 readback verification까지만이며, R route/R1/R2/R3가 Vessel을 자동 열람하는 기능은 아직 열지 않았다.
