# ORDER 175: Vessel-Backed R Graph Read Packet v0

## 1. Goal

R루프가 실제 Neo4j Vessel 그래프를 바로 의미 판단하지 않고, 먼저 읽기 전용 후보 봉투로 받아볼 수 있게 한다.

현재 R루프 frame/state machine과 dry-run 구조는 존재하지만, 실제 Vessel 그래프의 최신 summary/node 후보를 R루프 입력 후보로 안전하게 읽는 얇은 경계가 부족하다.

이번 발주는 R1/R2/R3 LLM 선택을 열기 전, `CoreEgo -> Time Axis` 주변의 진입 후보와 active summary 후보를 절대정보 패킷으로 고정하는 MVP다.

## 2. Required Behavior

- 새 CLI `vessel-r-read-packet`을 추가한다.
- Neo4j Vessel을 read-only로 조회한다.
- 다음 entry 후보를 읽는다.
  - `TimeBundle`
  - `SourceIngestBundle`
- 다음 summary 후보를 읽는다.
  - `SummaryGraphNode`
  - `payload_json.summary_status == "ran"`
  - `payload_json.validity_status == "active"`
- invalidated summary, failed summary, text 없는 skipped summary는 R 후보에서 제외한다.
- packet에는 다음 절대정보를 남긴다.
  - entry 후보 수
  - active summary 후보 수
  - scan한 summary 수
  - 제외된 summary 수
  - summary `data_kind`별 수
  - summary `summary_depth`별 수
  - 후보 node id, target id, summary text, source id
- `generated_by=CODE:R_LOOP_VESSEL_READ_PACKET_BUILDER`
- `info_class=absolute`
- `semantic_judgement_status=not_run`

## 3. Non-goals

- R route를 기본 live route로 열지 않는다.
- R1/R2/R3 LLM을 호출하지 않는다.
- 어떤 그래프 후보가 사용자 질문에 관련 있는지 code가 판단하지 않는다.
- semantic axis를 만들지 않는다.
- Neo4j에 새 노드/관계를 쓰지 않는다.
- summary를 생성/수정/무효화하지 않는다.

## 4. Test Plan

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_175_vessel_backed_r_read_packet.py -q
python main.py fast-test --profile graph
git diff --check
```

수동 확인:

```powershell
python main.py vessel-r-read-packet --database neo4j --format text
```
