# 04 Orders

발주서는 개발 지도에서 내려온 실무 계획서다.

현재 정식 발주서는 `ORDER_001`부터 `ORDER_101`까지 있다.

`ORDER_066`부터 `ORDER_075`까지는 메타정보 관리법을 실제 런타임과 LLM 노드 배선에 적용하기 위한 복구 로드맵이다.

`ORDER_076`부터 `ORDER_079`까지는 route=2 이후 0/code/2/3/4 보고 경로를 정리하고, node_3에 내부 ID 대신 의미 브리프를 공급하기 위한 후속 로드맵이다.

`ORDER_080`부터 `ORDER_085`까지는 W 문제감지 루프, 루프 권한표, node_4 반려 차단, W smoke/runtime view를 구현하기 위한 로드맵이다.

`ORDER_086`은 L3의 거시/미시 목표 달성 판단을 바탕으로 L2 재검색 또는 L루프 연속 검색을 어떻게 열지 다루는 설계 메모다. 아직 인간 결재 전이므로 즉시 구현 명령이 아니다.

`ORDER_087`은 아버지의 scheduler/task queue 구상을 바로 병렬 실행으로 밀지 않고, 현재 순차 노드 동선을 `TaskFrame`과 `TaskResultFrame`으로 장부화하는 첫 구현 발주서다.

`ORDER_088`은 휴리스틱 없이 node_3에게 현재 턴 실행 순서 자료를 항상 전달하여, task ledger/노드 순서 질문을 문서 검색 실패로 오판하지 않게 하는 보강 발주서다.

`ORDER_089`는 L3가 목표 미달을 판단했을 때 바로 route=2로 보내지 않고, L루프 내부에서 `L3 -> 0 -> L2` 제한 재검색 경로를 여는 첫 그래프 배선 발주서다.

`ORDER_090`은 L1이 L루프 목표에 필요한 예산을 요청하고, 코드가 정책 상한 안에서 승인하는 BudgetPlan v0 설계 발주서다.

`ORDER_091`은 `read_doc` 승인 횟수와 총 `tool_calls` 승인 횟수가 서로 모순되지 않도록 BudgetPolicy에 파생 제약을 추가하는 발주서다.

`ORDER_092`는 승인된 `read_doc` 예산을 실제 L루프 실행에 반영하여 검색 후보 여러 개를 순서대로 읽게 하는 발주서다.

`ORDER_093`은 node_3 최종 답변의 grounding count가 brief의 절대 count와 다를 때 node_4가 코드 guard로 반려하게 하는 발주서다.

`ORDER_094`는 상위 L 재라우팅을 열기 전에 L 복귀/route 재진입 계열 ID를 run-scoped로 만들어, 같은 턴의 L 1회차와 2회차 복귀 기록이 충돌하지 않게 하는 발주서다.

`ORDER_095`는 상위 L 재라우팅을 열기 전에 node2 이후 downstream 기록 ID를 run-scoped로 실제 적용하여, 같은 턴의 L 1회차와 2회차 route=2 이후 기록이 충돌하지 않게 하는 발주서다.

`ORDER_096`은 상위 L 재라우팅을 기본값으로 열지 않고, 명시적 policy guard 아래에서만 같은 턴 L 2회차를 허용하는 controller/runtime-flow 발주서다.

`ORDER_097`은 L루프의 기본 도구 호출 예산과 정책 상한을 5회로 맞추는 작은 예산 정책 발주서다.

`ORDER_098`은 L루프 run-scoped 기록과 route=2 downstream 기록을 terminal/final renderer가 정직하게 표시하도록, 최신 L run 우선 표시와 read_doc 집계 기준 분리를 다루는 발주서다.

`ORDER_099`는 node_1 LLM router 실패 뒤 code fallback이 쓰이는 사건을 routing frame과 terminal view에 명시적으로 남기는 정직성 잠금 발주서다.

`ORDER_100`은 장기기억 DB를 만들기 전에 0 기억공급관이 최근 3턴 `TurnStateCapsule` 색인 좌표를 `pre_route_report` memory packet에 안전하게 공급하는 발주서다.

`ORDER_101`은 최근 8턴 raw conversation과 `TurnStateCapsule`을 `turn_id` 기준으로 대응시켜, 이번 발주에서는 관련성 판단이나 요약을 구현하지 않고 alignment 좌표만 `pre_route_report` memory packet에 공급하는 발주서다.

## 임시 발주서

- [TMP Auto Hunt Orders 2026-06-21](TMP_Auto_Hunt_2026_06_21/README.md): 지금까지의 철학 정리본을 바탕으로 만든 자동 사냥용 후보 발주서 묶음.
- [TMP Auto Hunt Orders 2026-06-21 Phase 2](TMP_Auto_Hunt_2026_06_21_Phase2/README.md): ORDER 017 이후 이어서 쓸 수 있는 후보 발주서 묶음.
- [TMP L3-L2 Continuation MVP 2026-06-23](TMP_L3_L2_CONTINUATION_MVP_2026_06_23.md): L3 비판 결과를 바탕으로 L2 수정 검색을 최대 3회까지 허용하는 가벼운 MVP 후보.

## 정식 발주서

- [ORDER 001: Schema Foundation](ORDER_001_SCHEMA_FOUNDATION.md)
- [ORDER 001A: Schema Absolute Refinement](ORDER_001A_SCHEMA_ABSOLUTE_REFINEMENT.md)
- [ORDER 002: Trace Store](ORDER_002_TRACE_STORE.md)
- [ORDER 003: ZeroState And Turn Capsule](ORDER_003_ZERO_STATE_AND_TURN_CAPSULE.md)
- [ORDER 004: UnifiedState](ORDER_004_UNIFIED_STATE.md)
- [ORDER 005-012: Dry Run Stack](ORDER_005_012_DRY_RUN_STACK.md)
- [ORDER 005-012A: L Nodes Folder Split](ORDER_005_012A_L_NODES_FOLDER.md)
- [ORDER 013: Embedding Document Tools](ORDER_013_EMBEDDING_DOCUMENT_TOOLS.md)
- [ORDER 014: DataStore And Tool Result Payload Store](ORDER_014_DATA_STORE.md)
- [ORDER 015: L3 Preserved Frame Schema](ORDER_015_L3_PRESERVED_FRAME_SCHEMA.md)
- [ORDER 016: L2 Query Frame Schema](ORDER_016_L2_QUERY_FRAME_SCHEMA.md)
- [ORDER 017: L1 Goal Frame Schema](ORDER_017_L1_GOAL_FRAME_SCHEMA.md)
- [ORDER 018-040: Phase 2 Structural Sweep](ORDER_018_040_PHASE2_SWEEP.md)
- [ORDER 041: Node2 Input Frame](ORDER_041_NODE2_INPUT_FRAME.md)
- [ORDER 042: L3 Achievement Frame](ORDER_042_L3_ACHIEVEMENT_FRAME.md)
- [ORDER 043: LLM Runtime Activation](ORDER_043_LLM_RUNTIME_ACTIVATION.md)
- [ORDER 044: LLM Call Trace And Retry](ORDER_044_LLM_CALL_TRACE_AND_RETRY.md)
- [ORDER 045: L2 LLM Query Planner](ORDER_045_L2_LLM_QUERY_PLANNER.md)
- [ORDER 046: Tool Catalog And Choice Frame](ORDER_046_TOOL_CATALOG_AND_CHOICE_FRAME.md)
- [ORDER 047: Autonomous L Loop Controller](ORDER_047_AUTONOMOUS_L_LOOP_CONTROLLER.md)
- [ORDER 048: Tool Result Distillation](ORDER_048_TOOL_RESULT_DISTILLATION.md)
- [ORDER 049: Tool Efficiency Policy](ORDER_049_TOOL_EFFICIENCY_POLICY.md)
- [ORDER 050: LLM L Loop Smoke And Replay](ORDER_050_LLM_L_LOOP_SMOKE_AND_REPLAY.md)
- [ORDER 051: Mixed Info Boundary](ORDER_051_MIXED_INFO_BOUNDARY.md)
- [ORDER 052: Safe Report Frame v2](ORDER_052_SAFE_REPORT_FRAME_V2.md)
- [ORDER 053: Evidence Citation Policy](ORDER_053_EVIDENCE_CITATION_POLICY.md)
- [ORDER 054: User Facing Turn Summary](ORDER_054_USER_FACING_TURN_SUMMARY.md)
- [ORDER 055: Report Style Modes](ORDER_055_REPORT_STYLE_MODES.md)
- [ORDER 056: Hallucination Refusal And Uncertainty](ORDER_056_HALLUCINATION_REFUSAL_AND_UNCERTAINTY.md)
- [ORDER 057: ZeroState Read Window Policy](ORDER_057_ZERO_STATE_READ_WINDOW_POLICY.md)
- [ORDER 058: Memory Packet Relevance Scoring](ORDER_058_MEMORY_PACKET_RELEVANCE_SCORING.md)
- [ORDER 059: Memory Insufficient Backpressure](ORDER_059_MEMORY_INSUFFICIENT_BACKPRESSURE.md)
- [ORDER 060: Turn Capsule Compression v2](ORDER_060_TURN_CAPSULE_COMPRESSION_V2.md)
- [ORDER 061: Document Memory Index v2](ORDER_061_DOCUMENT_MEMORY_INDEX_V2.md)
- [ORDER 062: Knowledge Graph Candidate Schema](ORDER_062_KNOWLEDGE_GRAPH_CANDIDATE_SCHEMA.md)
- [ORDER 063: Memory Promotion Policy](ORDER_063_MEMORY_PROMOTION_POLICY.md)
- [ORDER 064: Runtime Artifact Manager](ORDER_064_RUNTIME_ARTIFACT_MANAGER.md)
- [ORDER 065: Project Self-Inspection Loop](ORDER_065_PROJECT_SELF_INSPECTION_LOOP.md)
- [ORDER 066: Metainfo Audit Inventory](ORDER_066_METAINFO_AUDIT_INVENTORY.md)
- [ORDER 067: Code Semantic Text Lockdown](ORDER_067_CODE_SEMANTIC_TEXT_LOCKDOWN.md)
- [ORDER 068: Runtime Metainfo Labels v2](ORDER_068_RUNTIME_METAINFO_LABELS_V2.md)
- [ORDER 069: Node1 LLM Router](ORDER_069_NODE1_LLM_ROUTER.md)
- [ORDER 070: L1 LLM Goal Setter](ORDER_070_L1_LLM_GOAL_SETTER.md)
- [ORDER 071: L3 LLM Result Keeper](ORDER_071_L3_LLM_RESULT_KEEPER.md)
- [ORDER 072: Node2 LLM Metainfo Boundary v2](ORDER_072_NODE2_LLM_METAINFO_BOUNDARY_V2.md)
- [ORDER 073: Node3 LLM Reporter](ORDER_073_NODE3_LLM_REPORTER.md)
- [ORDER 074: Node4 Gatekeeper And Return Loop](ORDER_074_NODE4_GATEKEEPER_AND_RETURN_LOOP.md)
- [ORDER 075: Metainfo Governance End-to-End Smoke](ORDER_075_METAINFO_GOVERNANCE_E2E_SMOKE.md)
- [ORDER 076: Route2 Handoff Integrity](ORDER_076_ROUTE2_HANDOFF_INTEGRITY.md)
- [ORDER 077: Node3 Input Brief](ORDER_077_NODE3_INPUT_BRIEF.md)
- [ORDER 078: Node4 Brief-Grounded Gatekeeper](ORDER_078_NODE4_BRIEF_GROUNDED_GATEKEEPER.md)
- [ORDER 079: Route2 Brief End-to-End Smoke](ORDER_079_ROUTE2_BRIEF_E2E_SMOKE.md)
- [ORDER 080: W Loop Authority Policy](ORDER_080_W_LOOP_AUTHORITY_POLICY.md)
- [ORDER 081: W1 Problem Triage Schema](ORDER_081_W1_PROBLEM_TRIAGE_SCHEMA.md)
- [ORDER 082: W1 LLM Node And Prompt](ORDER_082_W1_LLM_NODE_AND_PROMPT.md)
- [ORDER 083: W Loop Runtime Wiring](ORDER_083_W_LOOP_RUNTIME_WIRING.md)
- [ORDER 084: Node4 Remand Blocking](ORDER_084_NODE4_REMAND_BLOCKING.md)
- [ORDER 085: W Loop Smoke And Runtime View](ORDER_085_W_LOOP_SMOKE_AND_RUNTIME_VIEW.md)
- [ORDER 086: L3 Goal Continuation And L2 Scope Revision](ORDER_086_L3_GOAL_CONTINUATION_AND_L2_SCOPE_REVISION.md)
- [ORDER 087: Task Ledger v0](ORDER_087_TASK_LEDGER_V0.md)
- [ORDER 088: Node3 Runtime Task Sequence Brief](ORDER_088_NODE3_RUNTIME_TASK_SEQUENCE_BRIEF.md)
- [ORDER 089: L Loop Continuation v0](ORDER_089_L_LOOP_CONTINUATION_V0.md)
- [ORDER 090: L Loop Budget Plan v0](ORDER_090_L_LOOP_BUDGET_PLAN_V0.md)
- [ORDER 091: L Loop Budget Consistency v0](ORDER_091_L_LOOP_BUDGET_CONSISTENCY_V0.md)
- [ORDER 092: L Loop Multi Read Doc v0](ORDER_092_L_LOOP_MULTI_READ_DOC_V0.md)
- [ORDER 093: Node4 Grounding Count Guard v0](ORDER_093_NODE4_GROUNDING_COUNT_GUARD_V0.md)
- [ORDER 094: L Loop Return Reroute ID Scope v0](ORDER_094_L_LOOP_RETURN_REROUTE_ID_SCOPE_V0.md)
- [ORDER 095: L Loop Downstream Reroute ID Scope v0](ORDER_095_L_LOOP_DOWNSTREAM_REROUTE_ID_SCOPE_V0.md)
- [ORDER 096: Policy-Guarded Same-Turn L Reroute Controller v0](ORDER_096_POLICY_GUARDED_SAME_TURN_L_REROUTE_CONTROLLER_V0.md)
- [ORDER 097: L Loop Tool Budget Max 5 v0](ORDER_097_L_LOOP_TOOL_BUDGET_MAX_5_V0.md)
- [ORDER 098: Run-Aware Terminal/Final Renderer v0](ORDER_098_RUN_AWARE_TERMINAL_FINAL_RENDERER_V0.md)
- [ORDER 099: Router Fallback Honesty MVP v0](ORDER_099_ROUTER_FALLBACK_HONESTY_MVP_V0.md)
- [ORDER 100: Recent Turn Capsule Read Window Packet v0](ORDER_100_RECENT_TURN_CAPSULE_READ_WINDOW_PACKET_V0.md)
- [ORDER 101: Recent Raw Conversation Capsule Alignment v0](ORDER_101_RECENT_RAW_CONVERSATION_CAPSULE_ALIGNMENT_V0.md)
- [ORDER 102: Relative Info Direct-Field Smoke v0](ORDER_102_RELATIVE_INFO_DIRECT_FIELD_SMOKE_V0.md)
