# TMP Auto Hunt Orders 2026-06-21

**상태**: 임시 발주서 묶음  
**목적**: 지금까지의 철학 정리본을 바탕으로, 나중에 하나씩 승격해 구현할 수 있는 후보 작업을 대량 생산한다.  
**실행 권한**: 없음. 사용자가 특정 발주서를 골라 "이거 실행"이라고 말하기 전까지 코딩하지 않는다.

## 출처

- [Conversation Summary TMP](../../00_Philosophy/Conversation_Summary_TMP_2026_06_21.md)
- [Structure Map v0](../../03_Maps/02_Function_Maps/STRUCTURE_MAP_v0.md)
- [Development Map v0](../../03_Maps/03_Development_Maps/DEVELOPMENT_MAP_v0.md)

## 임시 발주서 목록

| 번호 | 문서 | 핵심 |
|---:|---|---|
| 001 | [Schema Foundation](TMP_ORDER_001_SCHEMA_FOUNDATION.md) | 기본 데이터 그릇 정의 |
| 002 | [Trace Event Format](TMP_ORDER_002_TRACE_EVENT_FORMAT.md) | trace 이벤트 형식 |
| 003 | [ZeroState And Turn Capsule](TMP_ORDER_003_ZERO_STATE_AND_TURN_CAPSULE.md) | 0.state와 턴 캡슐 |
| 004 | [UnifiedState](TMP_ORDER_004_UNIFIED_STATE.md) | 일반 노드 공용 state |
| 005 | [Node 0 Memory Supplier](TMP_ORDER_005_NODE_0_MEMORY_SUPPLIER.md) | 0 기억공급관 |
| 006 | [Node 1 Router](TMP_ORDER_006_NODE_1_ROUTER.md) | 1 상황판단 라우터 |
| 007 | [Node 2 Metainfo Boundary](TMP_ORDER_007_NODE_2_METAINFO_BOUNDARY.md) | 2 메타정보 경계 |
| 008 | [Node 3 Reporter](TMP_ORDER_008_NODE_3_REPORTER.md) | 3 보고관 |
| 009 | [L Loop](TMP_ORDER_009_L_LOOP.md) | L1/L2/L3 내부문서 검색 루프 |
| 010 | [Prompt And Schema Registry](TMP_ORDER_010_PROMPT_AND_SCHEMA_REGISTRY.md) | 프롬프트/스키마 레지스트리 |
| 011 | [Failure Signal](TMP_ORDER_011_FAILURE_SIGNAL.md) | 기억 부족/실패 신호 |
| 012 | [Dry Run MVP](TMP_ORDER_012_DRY_RUN_MVP.md) | LLM 없는 1턴 드라이런 |

## 사용법

1. 여기 있는 문서는 자동 사냥용 후보로만 읽는다.
2. 구현하고 싶은 문서를 하나 고른다.
3. 필요하면 내용을 수정한다.
4. 정식 발주서로 승격한다.
5. 그 다음에만 코딩한다.
