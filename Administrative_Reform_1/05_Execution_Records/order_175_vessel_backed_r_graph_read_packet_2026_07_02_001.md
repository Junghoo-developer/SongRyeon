# ORDER 175 Execution Record: Vessel-Backed R Graph Read Packet

## Summary

ORDER_175를 구현했다.

R루프가 실제 Neo4j Vessel 그래프를 바로 의미 판단하지 않고 읽기 전용 후보 봉투로 받을 수 있도록 `vessel-r-read-packet` CLI와 `RLoopVesselReadPacketFrame` 생성 경계를 추가했다.

## Changed Files

- `songryeon_core/core/r_loop_vessel_read_packet.py`
- `songryeon_core/runtime/r_loop_vessel_read_packet.py`
- `main.py`
- `songryeon_core/runtime/fast_test.py`
- `tests/test_order_175_vessel_backed_r_read_packet.py`
- `Administrative_Reform_1/04_Orders/ORDER_175_VESSEL_BACKED_R_GRAPH_READ_PACKET_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`

## Behavior

- `CoreEgo -> TimeAxis` 아래의 `TimeBundle` / `SourceIngestBundle`을 R entry 후보로 읽는다.
- `SummaryGraphNode` 중 `summary_status=ran`이고 `validity_status=active`인 summary만 R summary 후보로 읽는다.
- invalidated summary와 failed/skipped summary는 R 후보에서 제외한다.
- summary text는 Neo4j에 저장된 `payload_json.summary_text`를 복사한다.
- code는 관련성, 중요도, 의미 선택을 판단하지 않는다.
- packet은 `generated_by=CODE:R_LOOP_VESSEL_READ_PACKET_BUILDER`, `info_class=absolute`, `semantic_judgement_status=not_run`으로 고정한다.

## Verification

```powershell
python -m compileall songryeon_core main.py
```

통과.

```powershell
python -m pytest tests/test_order_175_vessel_backed_r_read_packet.py -q
```

결과: `6 passed in 0.12s`

```powershell
python main.py fast-test --profile graph
```

결과: `FAST_TEST_OK`, `108 passed in 52.51s`

```powershell
git diff --check
```

통과.

## Non-goals Preserved

- R route를 기본 live route로 열지 않았다.
- R1/R2/R3 LLM을 호출하지 않았다.
- semantic axis를 만들지 않았다.
- Neo4j에 새 노드/관계를 쓰지 않았다.
- summary를 새로 생성/수정/무효화하지 않았다.
