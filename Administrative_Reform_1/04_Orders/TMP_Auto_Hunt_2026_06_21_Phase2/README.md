# TMP Auto Hunt Orders 2026-06-21 Phase 2

**상태**: 임시 발주서 묶음  
**목적**: ORDER 017까지 구현된 현재 구조를 기준으로, 다음에 승격해 구현할 수 있는 후보 작업을 대량 생산한다.  
**실행 권한**: 없음. 사용자가 특정 발주서를 골라 "이거 실행"이라고 말하기 전까지 코딩하지 않는다.

## 현재 기준점

현재 L루프는 다음 DataStore payload 흐름을 가진다.

```text
L1:goal_frame
-> L2:query_frame
-> tool_result:search_docs:*
-> L3:preserved_info_frame
```

아직 0, 1, 2, 3의 payload 본체와 LLM 연결은 약하다.  
이 묶음은 그 약한 구간을 순서대로 채우기 위한 후보 발주서다.

## 임시 발주서 목록

| 번호 | 문서 | 핵심 |
|---:|---|---|
| 018 | [Node 0 Memory Packet Payload Store](TMP_ORDER_018_NODE_0_MEMORY_PACKET_PAYLOAD.md) | 0의 기억 패킷 본체 저장 |
| 019 | [Node 1 Routing Decision Payload Store](TMP_ORDER_019_NODE_1_ROUTING_DECISION_PAYLOAD.md) | 1의 라우팅 결정 본체 저장 |
| 020 | [Node 2 Metainfo Boundary v0.2](TMP_ORDER_020_NODE_2_METAINFO_BOUNDARY_V02.md) | DataStore 기반 절대정보 경계 확장 |
| 021 | [Node 3 Report Frame Schema](TMP_ORDER_021_NODE_3_REPORT_FRAME_SCHEMA.md) | 3의 보고 payload 스키마화 |
| 022 | [Turn Outcome Frame](TMP_ORDER_022_TURN_OUTCOME_FRAME.md) | 턴 성패/상태 프레임 |
| 023 | [Runtime Artifact Export](TMP_ORDER_023_RUNTIME_ARTIFACT_EXPORT.md) | trace/data/state JSON 내보내기 |
| 024 | [Main CLI Entry Point](TMP_ORDER_024_MAIN_CLI_ENTRYPOINT.md) | `main.py` 실행 진입점 |
| 025 | [Prompt Files Scaffold](TMP_ORDER_025_PROMPT_FILES_SCAFFOLD.md) | 프롬프트 파일 구조 |
| 026 | [LLM Adapter Interface](TMP_ORDER_026_LLM_ADAPTER_INTERFACE.md) | 로컬 LLM 추상 인터페이스 |
| 027 | [LLM JSON Schema Validation](TMP_ORDER_027_LLM_JSON_SCHEMA_VALIDATION.md) | LLM 출력 검증 레이어 |
| 028 | [Qwen Local Adapter Spike](TMP_ORDER_028_QWEN_LOCAL_ADAPTER_SPIKE.md) | Qwen 연결 실험 |
| 029 | [LLM Node Executor Base](TMP_ORDER_029_LLM_NODE_EXECUTOR_BASE.md) | LLM 노드 실행 공통 래퍼 |
| 030 | [Node 3 LLM Reporter](TMP_ORDER_030_NODE_3_LLM_REPORTER.md) | 3 보고관 LLM화 |
| 031 | [Node 2 LLM Metainfo Boundary](TMP_ORDER_031_NODE_2_LLM_METAINFO_BOUNDARY.md) | 2 경계관 LLM화 |
| 032 | [Node 1 LLM Router](TMP_ORDER_032_NODE_1_LLM_ROUTER.md) | 1 라우터 LLM화 |
| 033 | [Node 0 LLM Memory Supplier](TMP_ORDER_033_NODE_0_LLM_MEMORY_SUPPLIER.md) | 0 기억공급관 LLM화 |
| 034 | [Embedding Backend Interface](TMP_ORDER_034_EMBEDDING_BACKEND_INTERFACE.md) | 임베딩 백엔드 교체 인터페이스 |
| 035 | [Vector Index Cache](TMP_ORDER_035_VECTOR_INDEX_CACHE.md) | 문서 임베딩 캐시 |
| 036 | [Document Snapshot And Hash Index](TMP_ORDER_036_DOCUMENT_SNAPSHOT_HASH_INDEX.md) | 문서 변경 감지 |
| 037 | [Failure Signal v0.2](TMP_ORDER_037_FAILURE_SIGNAL_V02.md) | 실패/부족 신호 확장 |
| 038 | [Turn Capsule Persistence](TMP_ORDER_038_TURN_CAPSULE_PERSISTENCE.md) | 이전 턴 캡슐 저장/복원 |
| 039 | [Trace Replay Debugger](TMP_ORDER_039_TRACE_REPLAY_DEBUGGER.md) | trace 재생 디버거 |
| 040 | [Smoke Test Suite](TMP_ORDER_040_SMOKE_TEST_SUITE.md) | 최소 회귀 테스트 |

## 사용법

1. 이 묶음은 임시 후보로만 읽는다.
2. 다음에 구현할 번호를 하나 고른다.
3. 필요하면 사용자가 내용을 수정한다.
4. 정식 발주서로 승격한다.
5. 그 다음에만 코딩한다.
