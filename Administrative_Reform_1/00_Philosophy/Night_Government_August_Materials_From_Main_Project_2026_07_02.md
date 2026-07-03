# Night Government August Materials From Main Project 2026-07-02

**계층**: 00 철학
**상태**: 본점 정밀 탐사 기반 미승격 설계 재료
**권한**: 실행 권한 없음. 향후 발주서, 유지 체계, R-loop/Night Government 지도 문서로 승격 심사한다.

## 1. 이 문서의 목적

이 문서는 SongRyeon 본점의 심야정부, Sleep Stack, CoreEgo, local council, D10 trace 문서를 탐사한 뒤, SongRyeon Core가 8월까지 완성할 심야정부에 가져올 재료를 Core식으로 정리한 문서다.

본점의 결론을 그대로 베끼지 않는다.

본점에서 가져올 것은 다음이다.

```text
밤이 낮의 경험을 정리한다.
원본과 파생 정보를 분리한다.
정책/요약/가이드는 반드시 근거 주소를 가진다.
후보/자문/승인/무효화 상태를 섞지 않는다.
R-loop가 길을 찾을 수 있게 그래프 기억을 정리한다.
```

Core에서 버릴 것은 다음이다.

```text
한 번에 모든 정부/의회/정책 그래프를 열기.
밤 산출물이 낮 route/tool/final answer 권한으로 바로 승격되기.
저가치 추측을 durable graph node로 굳히기.
private/public, candidate/approved, source/advisory 구분 없이 섞기.
진행 장부 없이 500개 넘는 파일을 한 번에 요약하기.
```

## 2. 본점 탐사 근거

읽은 본점 문서와 코드 표면:

- `ANIMA_SLEEP_STACK_V1.md`
- `ANIMA_SLEEP_STACK_V2.md`
- `ANIMA_V4_MIDNIGHT_GOVERNMENT_PROPOSAL.md`
- `ANIMA_MIDNIGHT_DMN_REORG10A_INVENTORY_2026_05_26.md`
- `D2_DAY_NIGHT_STATE_SEPARATION_AND_ZERO_SUPPLY_AUDIT_2026_06_19.md`
- `D3_NIGHT_COREEGO_SOURCE_AUTHORITY_BOUNDARY_AUDIT_2026_06_19.md`
- `D7_NIGHT_MEMORY_PROMOTION_AND_GRAPH_PRIVACY_AUDIT_2026_06_19.md`
- `D8_MIDNIGHT_GOVERNMENT_PROPORTIONAL_COUNCIL_SCOPE_AUDIT_2026_06_19.md`
- `D9_COREEGO_LOCAL_COUNCIL_PROPORTIONAL_IDENTITY_AUDIT_2026_06_19.md`
- `D10_NIGHT_COREEGO_TRACEABILITY_REPLAY_REQUIREMENTS_2026_06_19.md`
- `GOVERNOR_MIDNIGHT_COREEGO_PROPORTIONAL_COUNCIL_SYNTHESIS_2026_06_19.md`
- `ANIMA_MIDNIGHT_COREEGO_TRACE_REPLAY_FIXTURE_REPORT_2026_06_20.md`
- `Core/_archive_v3_midnight/midnight_reflection.py`
- `Core/_archive_v3_midnight/midnight/rem_governor.py`

본점의 큰 흐름은 다음이었다.

```text
Dream / TurnProcess / PhaseSnapshot
-> REMPlan / REMGovernor
-> Coverage / Supply planning / Review
-> Placement / Policy fruit
-> BranchGrowth / BranchDigest
-> DreamHint / RoutePolicy / ToolDoctrine / TacticalThought
```

Core는 이 흐름을 지금 당장 전부 열지 않는다.

Core는 먼저 다음 좁은 골격만 가져온다.

```text
Raw source
-> source version
-> leaf summary
-> source kind bundle summary
-> time bundle summary
-> CoreEgo guide summary
-> R-loop guide / traversal material
```

## 3. 본점에서 배운 가장 중요한 실패 방지선

본점 문서들이 반복해서 말한 경계는 하나다.

```text
밤 산출물은 유용하지만, 낮의 명령권이 아니다.
```

따라서 Core 심야정부 산출물의 기본 상태는 다음이어야 한다.

| 산출물 | 기본 지위 | 낮 루프 권한 |
| --- | --- | --- |
| leaf summary | 근거 달린 relative/mixed 요약 | 직접 route/tool/final 권한 없음 |
| source kind bundle summary | 여러 원본 묶음에 대한 mixed 요약 | R-loop 탐색 안내 가능 |
| time bundle summary | 특정 관측 시간 묶음에 대한 mixed 요약 | R-loop 탐색 안내 가능 |
| CoreEgo guide summary | 그래프 탐색 가이드 | R-loop 안내 가능, 낮 route 명령 금지 |
| invalidation ledger | 절대정보 상태 장부 | 현재 근거 사용 가능 여부 표시 |
| night job ledger | 절대정보 작업 장부 | 재개/진행/실패 표시 |

밤이 만든 요약은 사용자가 바로 믿어야 하는 최종 진실이 아니다.

요약은 source bundle에서 파생된 정보이고, 사용 시점마다 다음을 드러내야 한다.

```text
generated_by
info_class
semantic_judgement_status
source_graph_node_ids
source_data_ids
source_trace_ids
validity_status
summary_depth
```

## 4. Core가 이미 가진 기반

Core는 본점처럼 처음부터 새 기억 DB를 만들 필요가 없다.

이미 있는 기반:

- `TraceStore`
- `DataStore`
- `TurnStateCapsule`
- source manifest
- graph memory builder
- graph vessel adapter
- Neo4j readback/inspect
- source version lineage
- summary invalidation ledger
- source leaf summary worker

따라서 Core 심야정부의 출발점은 새 `MemoryRecord`가 아니다.

출발점은 다음이다.

```text
이미 존재하는 trace/data/capsule/source manifest 좌표를
그래프 DB의 raw/source node로 올리고,
그 위에 요약 node를 별도로 붙인다.
```

## 5. 8월 심야정부의 기본 재료

8월 완성판을 위해 필요한 재료 후보는 다음이다.

### 5.1 NightJobLedger

심야정부 작업 장부다.

절대정보로 기록할 것:

- job id
- target graph node id
- target source version hash
- planned action
- status: `pending`, `running`, `written`, `failed`, `superseded_before_run`, `skipped_no_text`
- started_at / finished_at
- llm call id
- output graph node id
- failure reason
- next resume cursor

목적:

```text
심야정부가 중간에 끊겨도 어디까지 했는지 알고 다시 시작한다.
```

### 5.2 SourceVersionLineage

동적 원본의 버전 계보 장부다.

코드/문서처럼 변할 수 있는 데이터는 같은 path라도 같은 원본이 아니다.

기준:

```text
source kind + path + observed_at + source_last_modified_at + content hash
```

새 버전이 생기면 예전 버전을 삭제하지 않는다.

예전 버전에서 파생된 요약은 현재 근거로 쓰지 못하도록 무효화한다.

### 5.3 SummaryInvalidationLedger

요약 무효화 장부다.

규칙:

```text
pending summary target이 실행 전에 새 버전으로 대체되면 요약하지 않는다.
완료된 옛 summary는 삭제하지 않고 invalidated로 바꾼다.
상위 summary는 하위 active summary fingerprint가 바뀌면 stale이 된다.
```

핵심은 삭제가 아니라 상태 변경이다.

### 5.4 LeafSummaryGraphNode

원본 하나에 직접 대응하는 요약 노드다.

분류:

```text
source leaf 1개 -> summary 1개
info_class = relative
```

예:

```text
RawSource: songryeon_core/tools/code_tools.py
<- SUMMARY_OF
LeafSummary: code_tools.py 요약
```

이 요약은 원본 하나에 대응하므로 상대정보다.

### 5.5 SourceKindBundleSummary

같은 종류의 원본 묶음에 대한 요약이다.

예:

```text
internal_document 묶음
source_code_file 묶음
conversation_turn 묶음
```

분류:

```text
여러 raw source 또는 여러 leaf summary 묶음 -> mixed
```

목적:

```text
R-loop가 처음부터 500개 leaf를 보지 않고, source kind별 지도부터 본다.
```

### 5.6 TimeBundleSummary

같은 관측/수집 시간에 묶인 source kind bundle들을 다시 묶은 요약이다.

분류:

```text
여러 source kind bundle 또는 여러 summary node 묶음 -> mixed
```

목적:

```text
특정 시점에 그래프 DB에 무엇이 들어왔는지 큰 흐름을 잡는다.
```

### 5.7 CoreEgoGuideSummary

CoreEgo가 R-loop에게 줄 그래프 탐색 안내 요약이다.

기본 지위:

```text
R-loop guide material
advisory
not day-route authority
not final-answer evidence
```

필수로 드러낼 것:

- 어떤 시간축 entry가 있는가
- source kind별 요약이 어디 있는가
- active summary depth 범위
- invalidated/stale summary가 있는가
- R-loop가 먼저 볼 만한 entry는 무엇인가
- 사용하면 안 되는 stale/private/candidate material은 무엇인가

## 6. 처리 흐름

8월 심야정부의 권장 처리 순서는 다음이다.

```text
1. source/capsule/trace를 관측한다.
2. 새 원본 또는 변경된 원본만 raw source version으로 올린다.
3. 같은 내용이면 새 요약 작업을 만들지 않는다.
4. pending 작업이 새 버전으로 superseded되면 요약하지 않고 닫는다.
5. 바뀐 raw source leaf를 하나씩 요약한다.
6. leaf summary가 충분히 생기면 source kind bundle summary를 만든다.
7. source kind bundle summary가 생기면 time bundle summary를 만든다.
8. time bundle summary와 graph snapshot을 보고 CoreEgoGuideSummary를 만든다.
9. R-loop는 CoreEgo guide에서 시작해서 필요한 농도까지 내려간다.
```

중요:

```text
요약 작업은 한 번에 전부 끝내야 하는 일이 아니다.
한 개씩 저장하고, 진행률을 기록하고, 중단되면 재개한다.
```

## 7. 시간축과 의미축

Core의 초기 graph memory는 시간축을 기본 골격으로 삼는다.

이유:

- 시간은 모든 사건에 붙을 수 있다.
- 코드가 비교적 안정적으로 확정할 수 있다.
- 무작위성과 정렬성을 동시에 가진다.
- R-loop가 처음 길을 잃지 않게 해준다.

그러나 장기적으로는 의미축도 필요하다.

다만 의미축은 처음부터 전부 자동 생성하지 않는다.

의미축은 다음 조건에서 수요 기반으로 만든다.

- R-loop가 시간축만으로 자주 탐색 실패한다.
- 특정 주제 질문이 반복된다.
- CoreEgo 직속 시간축 entry가 너무 많아져 R1 부담이 커진다.
- 사용자가 시간보다 주제 기준 검색을 요구한다.

초기 결론:

```text
시간축은 기본 골격.
의미축은 수요 기반 확장.
```

## 8. 메타정보 분류

심야정부의 정보 분류는 다음처럼 잠근다.

| 대상 | 분류 |
| --- | --- |
| raw source node | absolute |
| source version lineage | absolute |
| job ledger | absolute |
| invalidation ledger | absolute |
| leaf summary, source 1개 대응 | relative |
| source kind bundle summary | mixed |
| time bundle summary | mixed |
| CoreEgo guide summary | mixed/advisory |
| R-loop selected path reason | selected source 수에 따라 relative 또는 mixed |

핵심:

```text
하나에 대응하면 relative.
여러 source bundle에 근거하면 mixed.
코드가 확인 가능한 상태/좌표/횟수/해시는 absolute.
```

## 9. trace/replay 요구

본점 D10 문서에서 Core가 반드시 가져와야 하는 원칙:

```text
좋아 보이는 설계만으로 live insertion 하지 않는다.
trace/replay로 경계가 지켜졌는지 보여야 한다.
```

심야정부/R-loop에서 최소로 보여야 할 trace row:

- producer family: night, graph builder, R-loop, L-loop, node_0, node_2 등
- material kind: raw source, leaf summary, bundle summary, guide, candidate, invalidation
- authority status: raw, relative, mixed, advisory, candidate, active, stale, invalidated
- privacy scope: private, public-safe, unknown, mixed-risk
- source graph node ids
- consumer role
- consumer use: route consideration, graph traversal, answer material, debug only
- promotion status
- final answer 사용 여부

`TRACE_INSUFFICIENT`는 실패가 아니라 정직한 차단 상태다.

## 10. 8월 완성판까지의 추천 단계

### Phase A. 진행 장부와 재개성

가장 먼저 해야 한다.

- one-by-one 처리
- progressive save
- progress inspect
- resume cursor
- superseded pending skip
- failed job 재시도 경계

### Phase B. leaf summary 안정화

- 새로 들어왔거나 바뀐 코드/문서 leaf만 요약
- 원문 하나당 요약 하나
- relative 정보로 기록
- 원본 없는/빈 파일은 `skipped_no_text`로 닫기

### Phase C. source kind bundle summary

- internal document끼리 묶기
- source code file끼리 묶기
- conversation turn끼리 묶기
- 서로 다른 data kind는 섞지 않기

### Phase D. time bundle summary

- 같은 ingest/observation batch의 source kind bundle들을 시간 묶음으로 정리
- summary depth와 source counts를 계산

### Phase E. CoreEgo guide summary

- R-loop가 볼 첫 안내판 생성
- active/stale/invalidated 상태 분리
- source kind와 time bundle entry를 사람이 읽을 수 있게 정리

### Phase F. R-loop read path

- R1이 guide를 보고 목표/예산/농도 설정
- R2가 entry 선택
- R3가 충분성/농도/가지 문제 판단
- 0이 R-loop trace와 읽은 graph node를 downstream에 전달

### Phase G. 수요 기반 의미축

나중에 연다.

- 반복 탐색 실패
- 반복 주제 질문
- R1 context 초과
- 시간축 과밀화

위 조건이 관측되기 전에는 의미축을 자동 대량 생성하지 않는다.

## 11. 8월 전까지 금지할 것

아직 하지 않는다.

- 밤 산출물이 낮 route/tool/answer mode를 직접 결정하게 하기
- DreamHint/SecondDream류를 최종 답변 근거로 바로 쓰기
- candidate/local/proportional material을 approved identity로 승격하기
- private SongRyeon material을 public-safe로 묵시 승격하기
- 의미축 자동 대량 생성
- 저가치 추측 노드 durable 저장
- 작업 장부 없는 대량 LLM 요약
- 실패한 요약을 성공한 요약처럼 숨기기
- 원본을 잘라서 중간 청크만 요약하고 전체 원본 요약처럼 표시하기

## 12. 한 줄 결론

8월의 Core 심야정부는 "밤에 똑똑한 말을 많이 쓰는 장치"가 아니다.

8월의 Core 심야정부는 다음이어야 한다.

```text
원본을 버리지 않고,
버전과 무효화를 기록하고,
요약을 source bundle에 매달고,
R-loop가 길을 찾을 수 있는 계층 지도를 만드는
그래프 기억 행정부.
```
