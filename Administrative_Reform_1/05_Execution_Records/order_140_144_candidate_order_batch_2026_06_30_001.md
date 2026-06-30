# order_140_144_candidate_order_batch_2026_06_30_001

## 1. 작업 요약

ORDER_139 이후 예상되는 R루프/심야정부 graph memory 로드맵을 후보 발주서로 미리 작성했다.

이번 작업은 구현이 아니다.

## 2. 작성한 후보 발주서

- `ORDER_140_R_LOOP_FRAME_ONLY_STATE_MACHINE_AUDIT_V0_CANDIDATE.md`
- `ORDER_141_CORE_EGO_GUIDE_WORKER_LLM_HINTS_V0_CANDIDATE.md`
- `ORDER_142_EXTERNAL_GRAPH_DB_ADAPTER_BOUNDARY_V0_CANDIDATE.md`
- `ORDER_143_R_LOOP_NODE0_MEMORY_PACKET_HANDOFF_V0_CANDIDATE.md`
- `ORDER_144_R_ROUTE_DRY_RUN_ONLY_V0_CANDIDATE.md`

## 3. 공통 상태

모든 문서는 후보 발주서다.

사용자 별도 결재와 선행 ORDER 완료 전 구현 금지로 표시했다.

## 4. 의도

밤샘 개발 중에도 "다음 수"가 흥분에 밀려 범위 초과되지 않도록, 구현 순서와 금지선을 미리 문서화했다.

로드맵:

```text
ORDER_139: graph memory foundation + RLoopGraphGuidePacket
ORDER_140 candidate: R frame/state machine audit
ORDER_141 candidate: CoreEgoGuideWorker LLM hints
ORDER_142 candidate: external graph DB adapter boundary
ORDER_143 candidate: node_0 -> R handoff packet
ORDER_144 candidate: dry-run only R route skeleton
```

## 5. 검증

문서 작성만 수행했다.

`git diff --check`만 확인한다.
