# Live Self-Status Freshness Failure 2026-07-20 001

- 실행일: 2026-07-20
- 상태: 라이브 실행 완료, 최신성 과업 실패
- 모델: `qwen3:14b` via direct Ollama
- 제품 코드 변경: 없음

## 1. 사용자 입력

```text
내부 문서를 아무거나 여러 개 직접 찾아 읽고, 그 문서들을 근거로 송련 Core가 최근
어디까지 개발됐는지 설명해줘. 그다음 현재 상태에 대해 네가 어떻게 평가하는지도 말하되,
문서에서 확인한 사실과 네 해석을 분리하고 한계를 밝혀줘.
```

강제 라우팅 없이 실행했다.

## 2. 런타임 절대정보

- 상태: `ok`
- route: `L -> 2`
- 총 시간: 168,344ms
- LLM calls: 14회
- LLM 총 시간: 153,548ms
- L runs: 1회
- L internal revision: 있음
- search_docs: 2회
- 실제 read_doc: 2개
- 최종 검색 후보: 21개
- L3 document summaries: 2개
- 최신 L3: `achieved / semantic=matched`
- node_4: `pass`

## 3. 실제 읽은 문서

1. `01_Maintenance_System/NEO4J_CONTEXT_GRAPH_LESSONS_FOR_SONGRYEON_NIGHT_GOVERNMENT_V0.md`
2. `05_Execution_Records/metainfo_classification_code_audit_2026_06_26_001.md`

둘째 문서는 2026-06-26 감사 기록이고 이후 구현 상태를 반영하지 않는다.

## 4. 검색기는 최신 후보를 일부 찾았다

최초 검색 결과에는 다음 문서가 포함됐다.

- 4위: `order_261_code_range_material_assembly_and_l3_recheck_2026_07_17_001.md`
- 7위: `l3_live_semantic_binding_failure_audit_2026_07_18_001.md`

revision 검색에는 다음 문서도 포함됐다.

- `ORDER_274_L_REVISION_FINAL_STATUS_RECONCILIATION_AUDIT_V0.md`
- `order_260_l2_explicit_code_path_contract_implementation_2026_07_14_001.md`

따라서 최신 문서가 검색 후보에 전혀 없었던 것은 아니다. L2/controller가 최초 검색 1·2위의
오래된 문서를 먼저 읽었고, revision은 새 후보를 찾은 뒤 추가 원문을 읽지 않았다.

## 5. L3 상태 변화

최초 L3는 읽은 두 문서가 최근 개발 진도를 직접 설명하지 않는다고 판단했다.

```text
semantic_goal_match_status=partial
```

revision L3는 새 원문을 추가로 읽지 않은 상태에서 같은 두 원문을 근거로 다음처럼 뒤집었다.

```text
semantic_goal_match_status=matched
achievement_status=achieved
```

즉 revision 검색 후보 수가 늘어난 사실과, 최근 상태를 설명할 원문이 실제 확보된 사실이
분리되지 못했다.

## 6. 최종 답변의 오래된 주장

최종 답변은 다음을 현재 상태처럼 말했다.

- 외부 graph DB adapter가 미비하다.
- Night Government summary node가 미비하다.
- 상대정보와 혼합정보를 구분하는 구현 경로가 부재하다.

현재 저장소에는 다음 구현이 존재하므로 위 설명은 최신 상태가 아니다.

- `songryeon_core/core/graph_vessel_neo4j.py`
- `songryeon_core/core/graph_vessel_readback.py`
- `songryeon_core/core/graph_vessel_inspect.py`
- `songryeon_core/nodes/night_summarize_time_bundle.py`
- `songryeon_core/nodes/night_summarize_source_leaf.py`
- `songryeon_core/nodes/night_summarize_token_budget_bundle.py`
- `songryeon_core/nodes/node_2_metainfo_boundary.py`의 `RelativeInfoRef` 생성 경로

엔티티/사실 추출 노드의 현재 구현 여부는 이번 대조 범위에서 별도로 판정하지 않았다.

## 7. 판정

### 통과

- node_1이 문서 조사 요청을 스스로 L로 라우팅했다.
- 실제 원문 2개와 검색 후보 count를 정직하게 표시했다.
- 원문은 DataStore에 보존하고 node_3에는 L3 요약을 전달했다.
- node_3는 문서 사실과 자기 평가를 문단으로 나누고 한계를 표시했다.
- 모든 LLM call이 parse/schema/transport 실패 없이 끝났다.

### 실패

- `최근 어디까지 개발됐는가`라는 시간 요구를 검색·읽기 성공 계약으로 구조화하지 못했다.
- L2는 최신 후보보다 오래된 상위 embedding 후보를 읽었다.
- revision은 최신 후보를 찾았지만 추가 원문을 읽지 않았다.
- L3는 원문 추가 없이 `partial -> matched`로 뒤집었다.
- node_4는 공급된 낡은 문서와 답변 사이의 일관성만 확인해 `pass`했고, 현재 저장소 현실과의
  시간적 충돌은 검사하지 못했다.

최종 판정은 다음과 같다.

```text
runtime execution: pass
evidence count honesty: pass
current-development freshness: failed
final answer usefulness: failed
```

## 8. 다음 감사 후보

새 검색 휴리스틱을 바로 넣지 않는다. 먼저 다음 구조를 감사한다.

1. L1이 `최근/현재/최신`을 명시적인 temporal evidence requirement로 기록할 수 있는가.
2. 검색 후보 카드에 CODE가 확인한 문서 시각·ORDER 번호·source role을 제공하는가.
3. L2가 temporal requirement에 따라 후보를 선택했다는 이유를 출처와 함께 기록할 수 있는가.
4. L3가 최신성 요구를 만족한 원문 없이 `matched`로 승격되는 것을 막을 구조 계약이 있는가.

사용자 문장의 시간 표현을 CODE 키워드 휴리스틱으로 직접 판정하는 방식은 권장하지 않는다.

## 9. 보존 위치

```text
.songryeon_core_cache/order_280/self_status_live/
```

`report.md`, `summary.json`, `trace.json`, `data.json`을 보존했다.
