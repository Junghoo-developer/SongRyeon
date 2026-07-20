# ORDER 276 L Live Final State Reconciliation Matrix 실행 기록

- 실행일: 2026-07-20
- 기준 commit: `e855303`
- 모델: `qwen3:14b` via Ollama
- 제품 코드 변경: 없음
- export: `.songryeon_core_cache/order_276/`

## 1. 종합 판정

| 사례 | 판정 | 핵심 절대정보 |
| --- | --- | --- |
| A. 단순 원문 성공 | 통과 | 원문 1개, legacy=`stop_success`, latest L3=`achieved`, node_4=`pass` |
| B. 초기 실패 뒤 대체 원문 회복 | 부분 통과 | 대체 원문 1개, revision 3회, legacy=`stop_failed`, latest L3=`partial`, node_4=`pass` |
| C. 후보만 확보 | 상태 색인 통과 / grounding 문구 실패 발견 | 후보 12개, 원문 0개, legacy=`stop_candidate_only`, latest L3=`partial`, node_4=`pass` |

ORDER 275의 final-state index 계약은 세 사례 모두 통과했다. legacy control과 canonical
latest L3 source가 섞이지 않았다. 다만 사례 C에서 별도 grounding 문구 모순을 발견했다.

## 2. 사례 A: 단순 원문 성공

```powershell
python main.py qwen-turn "Administrative_Reform_1/04_Orders/ORDER_275_L_RUN_FINAL_STATE_INDEX_AND_LEGACY_SCOPE_V0.md 파일을 직접 읽고, L루프가 최초 control 판단과 revision 포함 최신 상태를 어떻게 분리하는지 원문 근거로 짧게 설명해줘." --force-l --max-tool-calls 5 --max-query-attempts 2 --max-read-doc-calls 2 --timeout 180 --compact --export ".songryeon_core_cache\order_276\case_a_direct_success"
```

- runtime: `ok`
- route: `L -> 2`
- 실제 원문: 1개
- `l_loop_final_decision=stop_success`
- `l_loop_final_decision_scope=legacy_pre_revision_terminal_control`
- latest L3/source: `L3:achievement_frame / achieved`
- final continuation: `stop_achieved`
- node_4: `pass`

## 3. 사례 B: 초기 실패 뒤 대체 원문 회복

```powershell
python main.py qwen-turn "Administrative_Reform_1/04_Orders/ORDER_275_DOES_NOT_EXIST.md 파일을 먼저 직접 읽어줘. 그 파일이 없으면 포기하지 말고 ORDER_275 final state index 발주서를 내부 문서에서 다시 검색한 뒤 실제 원문을 읽고, 최초 control 판단과 revision 포함 최신 상태의 차이를 설명해줘." --force-l --max-tool-calls 8 --max-query-attempts 3 --max-read-doc-calls 2 --timeout 180 --compact --export ".songryeon_core_cache\order_276\case_b_revision_recovery"
```

- runtime: `ok`
- 실제 대체 원문: 1개
- revision query: 3회
- `l_loop_final_decision=stop_failed`
- legacy source: `L:control:0002`
- latest source: `L3:revision_achievement:0003`
- latest status: `partial`
- final continuation: `stop_failed_final`
- node_4: `pass`

상태 색인은 정확했다. 다만 L1 success condition이 존재하지 않는 원래 파일을 계속 핵심
목표로 잡아, 사용자가 허용한 대체 문서를 실제로 읽고 의미 match를 했는데도 최종 상태가
`partial`로 남았다. 이는 조건부 목표·대체 성공 계약의 별도 한계다.

## 4. 사례 C: 후보만 확보

```powershell
python main.py qwen-turn "내부 문서에서 ORDER_275 final state index와 관련된 문서 후보 목록만 찾아줘. 이번 시험에서는 원문을 읽지 말고, 검색 후보 수와 실제 읽은 원문 수를 반드시 구분해서 짧게 말해줘." --force-l --max-tool-calls 1 --max-query-attempts 1 --max-read-doc-calls 1 --timeout 180 --compact --export ".songryeon_core_cache\order_276\case_c_candidates_only"
```

- runtime: `ok`
- 후보: 12개
- 실제 read_doc 원문: 0개
- `l_loop_final_decision=stop_candidate_only`
- latest L3/source: `L3:achievement_frame / partial`
- final continuation: `stop_budget_exhausted`
- node_3 본문: 후보 12개와 원문 0개를 정확히 구분
- node_4: `pass`

그러나 CODE grounding block의 답변 한계 문장이 다음처럼 기록됐다.

```text
L 원문은 확보됐지만 L3 의미 검사가 실패했으므로 ...
```

같은 block 위쪽의 `실제 read_doc 도구 원문 읽기: 0개`와 충돌한다.

## 5. 원인 감사

- `node_2_handoff._l_loop_result_attitude_hint()`는 semantic execution이 실패하면
  실제 원문 수를 확인하지 않고 항상
  `l_loop_original_material_acquired_l3_semantic_failed`를 반환한다.
- `node_3_reporter._grounding_limit_text()`는 이 hint를 그대로 받아
  `L 원문은 확보됐지만` 문장을 CODE grounding block에 쓴다.
- `supplied_document_context_count=1`은 검색 후보 context가 공급됐다는 뜻이지
  `actual_tool_read_doc_count=1`이라는 뜻이 아니다.
- node_4는 LLM 본문의 후보 12/원문 0 구분은 확인했지만 CODE-supplied grounding block
  내부의 이 문장 모순은 반려하지 않았다.

## 6. 결론

ORDER 275 L final-state index는 라이브 기준선을 통과했다. 다음 패치는 상태 색인이 아니라
원문 확보 태도와 grounding 한계 문장의 count consistency로 좁혀야 한다.

다음 발주 후보:

```text
ORDER_277_L_ORIGINAL_MATERIAL_ATTITUDE_AND_GROUNDING_LIMIT_CONSISTENCY_V0
```

필요 작업:

1. semantic failure와 original material 확보 여부를 별도 절대필드로 판별한다.
2. 원문 0개일 때 `original_material_acquired` hint를 금지한다.
3. CODE grounding block 내부 모순을 deterministic test로 막는다.
4. 후보 context와 실제 read_doc 원문을 같은 것으로 부르지 않는다.

이번 감사에서는 결함을 발견한 뒤 제품 코드를 수정하지 않았다.
