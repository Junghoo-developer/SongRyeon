# ORDER_143_R_LOOP_NODE0_MEMORY_PACKET_HANDOFF_V0

## Status

구현 완료.

ORDER_139~142 결과 위에서 구현한다.

실행 기록:

- `Administrative_Reform_1/05_Execution_Records/order_143_r_loop_node0_memory_packet_handoff_2026_06_30_001.md`

## 1. 목표

0 기억공급관이 R루프에 graph guide와 graph source 좌표를 안전하게 넘기는 handoff packet을 설계한다.

이번 후보는 R루프 실행 자체가 아니다.

핵심:

```text
0은 R루프에게 graph memory guide 좌표를 공급한다.
0은 의미 판단을 하지 않는다.
0은 R루프 trace/data 좌표를 downstream에 잃지 않게 전달한다.
```

## 2. 선행 조건

- ORDER_139 완료.
- RLoopGraphGuidePacket이 존재.
- ORDER_140 frame audit 완료.
- 가능하면 ORDER_142 adapter boundary 확정.

## 3. 후보 packet

후보 이름:

```text
MemoryPacketForRLoop
RLoopMemoryHandoffPacket
Node0RLoopGraphGuidePacket
```

후보 필드:

```text
packet_id
target = R_LOOP
mode = graph_guide_handoff
graph_snapshot_id
r_loop_graph_guide_packet_id
available_entry_node_ids
node_kind_counts
summary_depth_range
source_graph_node_ids
source_data_ids
source_trace_ids
generated_by = CODE:node_0_memory_supplier
info_class = absolute
semantic_judgement_status = not_run
```

## 4. 0의 책임

0이 할 수 있는 것:

- guide packet id를 복사한다.
- graph snapshot id를 복사한다.
- entry node id 목록을 복사한다.
- count/depth/status를 복사한다.
- source ids를 보존한다.

0이 하면 안 되는 것:

- 어떤 graph node가 의미상 적합한지 고른다.
- 사용자의 의도에 맞는 topic을 만든다.
- R1/R2/R3 판단을 대신한다.
- final answer에 graph memory 내용을 직접 말한다.

## 5. Runtime 표시 후보

terminal/runtime에는 다음 정도만 표시한다.

```text
r_loop_graph_guide: status=available|missing
entry_nodes=N
summary_depth_range=min..max
semantic_hint_status=not_run|ran|failed
```

내부 raw graph id를 사용자 최종 답변에 노출하지 않는다.

## 6. 금지

- node_1 route=R 연결 금지.
- R루프 자동 실행 금지.
- node_3 답변에 graph memory 자동 주입 금지.
- 0이 graph relevance 판단 금지.
- 의미축 graph hierarchy 생성 금지.

## 7. 테스트 후보

1. 0이 RLoopGraphGuidePacket id를 handoff packet에 보존한다.
2. source graph/data/trace id가 누락되지 않는다.
3. 0의 packet은 `semantic_judgement_status=not_run`이다.
4. guide packet이 없으면 missing 상태로 닫고 code fallback 의미 판단을 만들지 않는다.
5. terminal runtime은 count/status만 표시한다.

## 8. 완료 조건

구현 후 다음을 통과해야 한다.

```powershell
python -m compileall songryeon_core main.py
python -m pytest
python main.py smoke-test
git diff --check
```
