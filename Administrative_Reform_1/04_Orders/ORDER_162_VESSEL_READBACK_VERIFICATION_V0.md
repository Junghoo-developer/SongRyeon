# ORDER 162: Vessel Readback Verification v0

## 상태

구현 대상.

## 목표

`vessel-first-write`로 Neo4j Vessel에 기록한 그래프를 코드가 다시 읽어, 다음 경로가 실제로 존재하는지 절대정보로 확인한다.

```text
CoreEgo -> HAS_AXIS -> TimeAxis -> HAS_BUNDLE -> TimeBundle -> CONTAINS_MEMORY -> RawCapsule
```

## 배경

ORDER 160은 로컬 Neo4j Vessel에 첫 쓰기를 열었다.
ORDER 161은 사람이 보기 쉬운 label/relationship/display vocabulary를 정리했다.
하지만 아직 “쓴 뒤에 코드가 같은 vocabulary로 다시 읽을 수 있는지”를 확인하는 좁은 검증 명령이 없다.

## 구현 범위

- `vessel-readback` CLI를 추가한다.
- Neo4j에서 다음 수량을 읽는다.
  - VesselRecord node count
  - Vessel relationship count
  - CoreEgo / TimeAxis / TimeBundle / RawCapsule count
  - HAS_AXIS / HAS_BUNDLE / CONTAINS_MEMORY count
  - CoreEgo -> TimeAxis -> TimeBundle -> RawCapsule path count
  - 필수 provenance property 누락 count
- readback 결과를 `GraphVesselNeo4jReadbackResultFrame`으로 DataStore에 남긴다.
- `generated_by=CODE:GRAPH_VESSEL_NEO4J_READBACK_VERIFIER`
- `info_class=absolute`
- `semantic_judgement_status=not_run`

## 금지

- Neo4j 데이터를 변경하지 않는다.
- R route, R1/R2/R3 자동 실행을 열지 않는다.
- node_1/node_2/node_3 답변 흐름에 자동 주입하지 않는다.
- LLM 요약, 중요도, 관련성 판단을 생성하지 않는다.
- 의미축 graph node를 만들지 않는다.

## 완료 조건

- `python -m compileall songryeon_core main.py`
- `python -m pytest tests/test_order_162_vessel_readback_verification.py -q`
- `python main.py fast-test --profile graph`
- `python -m pytest`
- `python main.py smoke-test`

## 수동 확인 명령

Neo4j 비밀번호가 환경변수 또는 `--password`로 설정된 터미널에서 다음을 실행한다.

```powershell
python main.py vessel-readback --database neo4j
```

기대값:

- `readback_status=passed`
- `core_path_exists=true`
- `core_path_count>=1`
- `core_ego_count>=1`
- `time_axis_count>=1`
- `time_bundle_count>=1`
- `raw_capsule_count>=1`

## 다음 단계 후보

ORDER 162가 통과하면, 다음 후보는 R loop 또는 수동 graph-inspect 명령이 이 readback 결과를 이용해 CoreEgo에서 시간축 후보를 열람하는 단계다.
