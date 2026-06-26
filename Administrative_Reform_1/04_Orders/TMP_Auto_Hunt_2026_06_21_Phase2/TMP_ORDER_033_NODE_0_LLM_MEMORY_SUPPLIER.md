# TMP ORDER 033: Node 0 LLM Memory Supplier

## 목표

0 기억공급관을 LLM 기반으로 바꾸되, 기억을 창조하지 못하게 source 제한을 강제한다.

## 배경

0은 현재 설계의 핵심이다.  
LLM화하더라도 trace/DataStore/ZeroState에 없는 기억을 만들어내면 안 된다.

## 범위

1. 0의 입력 bundle 스키마를 만든다.
2. 0의 출력 memory packet payload 스키마를 사용한다.
3. memory_items마다 source_trace_ids/source_data_ids를 강제한다.
4. 출처 없는 memory item은 검증 실패한다.
5. 실패 시 memory_insufficient FailureSignal을 만든다.

## 완료 기준

- 0이 source 없는 기억을 출력하면 실패한다.
- L1/L2/2에 전달되는 memory packet이 DataStore payload로 저장된다.

## 제외

- 장기기억 그래프 DB.
- C루프 자동 호출.
