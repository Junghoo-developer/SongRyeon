# TMP ORDER 029: LLM Node Executor Base

## 목표

프롬프트, 입력 payload, LLM adapter, 스키마 검증, trace/data 저장을 묶는 공통 노드 실행기를 만든다.

## 배경

각 노드마다 LLM 호출 코드를 따로 쓰면 구조가 빠르게 무너진다.

## 범위

1. `LLMNodeExecutor`를 만든다.
2. 입력: node_id, prompt_ref, input_payload, output_schema.
3. 출력: TraceEvent, DataRecord, validation result.
4. 실패 시 FailureSignal을 연결한다.

## 완료 기준

- FakeLLMAdapter로 하나의 dummy node 실행이 가능하다.
- trace와 data가 모두 남는다.

## 제외

- 실제 노드 교체.
- 복잡한 graph orchestration.
