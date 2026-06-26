# TMP ORDER 018: Node 0 Memory Packet Payload Store

## 목표

0 기억공급관이 만든 memory packet을 trace 이름표뿐 아니라 DataStore payload로 저장한다.

## 배경

현재 `memory_packet:node_1`, `memory_packet:L`, `memory_packet:node_2`는 trace output_ref로만 존재한다.  
0이 실제로 어떤 근거를 공급했는지 본체가 약하다.

## 범위

1. `MemoryPacketPayload` 또는 확장된 `MemoryPacketFrom0` 스키마를 만든다.
2. `packet_id`, `turn_id`, `target`, `mode`, `source_trace_ids`, `source_data_ids`, `evidence_trace_ids`, `insufficient_signal_id`, `memory_items`를 둔다.
3. `record_memory_packet()`이 DataStore에 payload를 저장하게 한다.
4. L1의 source data에 `memory_packet:L`을 포함한다.
5. 2번 경계관이 memory packet payload를 `data_record:*`로 인식하게 한다.

## 완료 기준

- `python dry_run.py`가 통과한다.
- DataStore에 `memory_packet:node_1`, `memory_packet:L`, `memory_packet:node_2`가 저장된다.
- L1 source data에 `memory_packet:L`이 들어간다.

## 제외

- 0의 LLM 판단.
- 기억 요약 품질 평가.
