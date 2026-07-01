# ORDER 163: Vessel Inspect Manual Walk v0

## 상태

구현 대상.

## 목표

Neo4j Vessel에 들어간 graph memory를 사람이 볼 수 있는 tree로 펼쳐 확인하는 읽기 전용 CLI를 만든다.

```powershell
python main.py vessel-inspect --database neo4j
```

## 배경

ORDER 160은 Neo4j Vessel 첫 쓰기를 열었다.
ORDER 161은 사람이 보기 쉬운 label/relationship vocabulary를 정리했다.
ORDER 162는 다음 경로가 실제로 존재하는지 readback으로 확인했다.

```text
CoreEgo -> HAS_AXIS -> TimeAxis -> HAS_BUNDLE -> TimeBundle -> CONTAINS_MEMORY -> RawCapsule
```

하지만 아직 사용자가 터미널에서 “CoreEgo 아래 무엇이 있는지”를 한눈에 펼쳐볼 수 없다.

## 구현 범위

- `vessel-inspect` CLI를 추가한다.
- Neo4j에서 CoreEgo -> TimeAxis -> TimeBundle -> RawCapsule 경로를 읽는다.
- 사람이 볼 수 있는 `tree_lines` / `tree_text`를 만든다.
- 결과를 `GraphVesselNeo4jInspectResultFrame`으로 DataStore에 남긴다.
- 결과는 다음으로 고정한다.
  - `generated_by=CODE:GRAPH_VESSEL_NEO4J_INSPECTOR`
  - `info_class=absolute`
  - `semantic_judgement_status=not_run`

## 출력 예시

```text
CoreEgo [graph:core_ego:root]
  HAS_AXIS -> Time Axis [graph:axis:time]
    HAS_BUNDLE -> Time Bundle [graph:time_bundle:manual_vessel_first_write:core]
      CONTAINS_MEMORY -> Raw Capsule: turn_vessel_first_write_0001:previous [graph:raw_capsule:turn_vessel_first_write_0001:previous]
```

## 금지

- Neo4j 데이터를 변경하지 않는다.
- R route/R1/R2/R3 자동 실행을 열지 않는다.
- node_1/node_2/node_3 답변 흐름에 자동 주입하지 않는다.
- LLM 요약, 중요도, 관련성 판단을 만들지 않는다.
- 의미축 graph node를 만들지 않는다.

## 완료 조건

- `python -m compileall songryeon_core main.py`
- `python -m pytest tests/test_order_163_vessel_inspect_manual_walk.py -q`
- `python main.py fast-test --profile graph`
- `python main.py smoke-test`

## 수동 확인 명령

Neo4j 비밀번호가 환경변수 또는 `--password`로 설정된 터미널에서 실행한다.

```powershell
python main.py vessel-inspect --database neo4j --format text
```

기대값:

- `inspect_status=passed`
- `inspected_path_count>=1`
- tree 안에 `CoreEgo`, `Time Axis`, `Time Bundle`, `Raw Capsule`이 표시된다.

## 다음 단계 후보

ORDER 163이 통과하면 다음 후보는 R loop 또는 별도 graph-walk 명령이 inspect 결과를 이용해 시간축 후보를 선택하는 단계다.
