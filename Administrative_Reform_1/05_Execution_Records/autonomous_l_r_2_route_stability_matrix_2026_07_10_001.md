# 자율 L/R/2 라우팅 및 R 안정성 시험 기록

- 날짜: 2026-07-10
- 목적: ORDER 243 이후 force flag 없이 node_1의 L/R/2 선택과 downstream 정직성을 교차 확인
- 공통 조건: `--enable-r-route-experimental --enable-vessel-r-route`, Qwen3 14B

## 시험 결과

| 사례 | 기대 route | 실제 route | 내부 결과 | 최종 검사 | 판정 |
| --- | --- | --- | --- | --- | --- |
| Vessel의 ORDER 090을 RawSource 원문까지 확인 | R | R | 6개 노드, 원문 1개, sufficient | pass | 통과 |
| 현재 디스크의 최신 ORDER 243 직접 확인 | L | L | read_doc 1개, supplied context 1개, achieved | pass | 통과 |
| R/L 표현이 들어간 짧은 일반 대화 | 2 | 2 | L 0, R 0 | needs_revision | 라우팅 통과, Vessel guard 오탐 |
| R/L 표현이 없는 짧은 일반 대화 | 2 | 2 | L 0, R 0 | pass | 라우팅 통과, 답변 지시 불이행 |
| Vessel의 ORDER 139를 RawSource까지 확인 | R | R | ORDER 090 가지를 재선택, 원문 1개, budget exhausted partial | pass | 가지 선택/최종 검사 실패 |
| 연결 불가능한 Neo4j 주소에서 ORDER 090 확인 | R | R | read_packet failed, node3 material failed | needs_revision/block | 안전 차단 통과, guard 사유 오탐 포함 |

## 확인된 안정 영역

- 이번 표본에서 node_1은 기대한 route를 모두 선택했다.
- 이미 적재된 ORDER 090은 R로, 아직 적재되지 않은 최신 ORDER 243은 L로 분리했다.
- 검색이 필요 없는 질문은 L/R 없이 바로 route=2로 보냈다.
- Neo4j 연결 실패를 R 성공으로 위장하지 않고 read failure와 blocked answer로 닫았다.
- R 결과와 RawSource 원문은 node_0/node_2/node_3까지 전달될 수 있다.

## 확인된 불안정 영역

1. R2 가지 선택 일반화 부족
   - ORDER 139 요청에서도 이전 성공 사례인 ORDER 090 요약/원문 가지를 다시 선택했다.
   - R task는 partial/budget exhausted였지만 최종 본문은 ORDER 139가 아닌 예산 내용을 설명했다.

2. node_4 목표 관련성 검사 부족
   - ORDER 139 질문과 무관한 ORDER 090 답변을 pass했다.
   - 현재 guard는 count/status/근거 역할은 검사하지만 사용자 목표와 최종 본문의 의미 일치까지 안정적으로 잡지 못했다.

3. 짧은 route=2 답변 태도 불안정
   - “한 문장으로 힘내자”는 요청에 내부 실행 순서 8단계를 길게 설명했다.
   - node_4도 이를 pass했다.

4. Vessel R 문자열 guard 오탐
   - 사용자 문장에 R/L 시험이라는 표현이 있다는 이유로 Vessel graph material claim mismatch가 발생했다.
   - DB 실패를 정직하게 설명하는 문장에도 같은 guard 사유가 섞였다.

## 결론

- node_1의 자율 route 선택은 이번 소규모 표본에서 정상화 조짐을 확인했다.
- R 배선, 원문 도달, 실패 차단은 MVP 기준으로 작동한다.
- 그러나 R2의 문서/가지 목표 고정과 node_4의 질문-답변 관련성 검사가 아직 일반화되지 않았다.
- 따라서 R route의 실험 플래그를 기본값으로 승격하기에는 이르다.

## Export

- `.songryeon_core_cache/r_autonomous_integration_order_243_20260710_001`
- `.songryeon_core_cache/route_stability_order_243_case_l_fresh_20260710_001`
- `.songryeon_core_cache/route_stability_order_243_case_2_direct_20260710_001`
- `.songryeon_core_cache/route_stability_order_243_case_2_direct_clean_20260710_001`
- `.songryeon_core_cache/route_stability_order_243_case_r_order139_20260710_001`
- `.songryeon_core_cache/route_stability_order_243_case_r_db_unavailable_20260710_001`
