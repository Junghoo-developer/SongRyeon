# 자율 R 라우팅 완전 통합 시험 실패 기록

- 날짜: 2026-07-10
- 시험 조건: ORDER_242 통합 질문, `--enable-vessel-r-route`, force flag 없음
- export: `.songryeon_core_cache/r_autonomous_integration_order_242_20260710_001`

## 절대 결과

- route sequence: `L -> L requested -> 2`
- node_1 최초 route: `L`, generated_by=`LLM:qwen3:14b`
- R Vessel traversal ledger: 0
- L actual read_doc: 3
- node_3 supplied document context: 0
- node_4: pass

## 확인된 LLM 판단

- node_1은 R graph traversal이 RawSource 원문을 다루지 못한다고 판단했다.
- 이 판단은 ORDER_242 강제 R 시험에서 RawSource 원문까지 6단계로 읽은 현재 코드 능력과 어긋난다.
- L3는 사용자 질문에 특정 문서 요청이 없었다고 판단했다.
- 실제 질문에는 `ORDER 090 L Loop Budget Plan`이 명시되어 있었다.
- L3는 README와 무관한 실행기록 2개를 읽은 수량만으로 achieved 처리했다.
- node_3는 별도 근거 블록을 다시 만들고 실제 read_doc 3개를 0개라고 썼다.
- node_4는 이 count/grounding 모순을 감지하지 못하고 pass했다.

## 결론

- 강제 R 전체 배선은 통과했지만 node_1 자율 L/R 선택은 아직 정상화되지 않았다.
- 다음 감사 대상은 node_1 R capability card/prompt 현실 일치, L3 명시 문서 목표 보존,
  node_3 중복 grounding 제거, node_4 두 번째 grounding/count 모순 검사다.
- 이 기록에서는 코드 패치를 수행하지 않았다.
