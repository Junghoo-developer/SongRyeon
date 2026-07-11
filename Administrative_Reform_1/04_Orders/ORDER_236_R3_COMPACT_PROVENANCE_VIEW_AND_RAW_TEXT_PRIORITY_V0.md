# ORDER 236: R3 Compact Provenance View And Raw Text Priority v0

## 상태

- Status: implemented and regression verified; follow-up completed through ORDER_242
- Date: 2026-07-10
- Scope: R3 LLM input payload only / provenance preservation / selected material visibility

## 배경

ORDER 234~235 단독 Vessel R traverse는 RawSource 원문까지 읽고 `sufficient`로 끝났지만 완전 통합 qwen-turn은 마지막 R3에서 두 번 schema 실패했다.

export 감사 결과:

- 마지막 R3 LLM input payload는 약 68,889자였다.
- `r1_goal`과 `r2_selection`의 수천 개 source trace/data ID가 입력 앞부분을 차지했다.
- 선택된 RawSource 원문 3,722자는 그 뒤에 있었다.
- Qwen은 원문이 없다고 판단해 `low_summary / deeper`를 반복했다.
- 원본 프레임과 provenance 장부에는 문제가 없고 LLM용 payload 복사 범위가 문제였다.

## 목표

- R1/R2/step-memory의 의미 판단 필드와 구조 필드만 compact view로 R3에 공급한다.
- provenance source IDs는 DataStore/TraceStore 원본 프레임에 그대로 보존한다.
- 선택된 candidate, 특히 RawSource 원문을 R3 payload 앞쪽에 둔다.
- code가 원문을 요약하거나 의미를 대신 판단하지 않는다.

## 구현 경계

- `selected_candidate_record`는 R3 LLM payload 앞부분에 둔다.
- R1 compact view는 목표, 예산, 정지 조건, 메타정보 경계만 포함한다.
- R2 compact view는 선택 결과와 선택 이유만 포함한다.
- previous step memory compact view는 직전 선택, R3 신호, continuation, 남은 예산 count만 포함한다.
- full source_trace_ids/source_data_ids는 LLM payload에서 제외하되 원본 records와 LLM call provenance에는 유지한다.

## 하지 않는 것

- trace/data records를 삭제하거나 축약 저장하지 않는다.
- RawSource 원문을 요약하지 않는다.
- Qwen context 크기를 무작정 늘리지 않는다.
- 의미 선택 fallback이나 키워드 휴리스틱을 넣지 않는다.
- R1/R2/R3 역할을 바꾸지 않는다.

## 완료 조건

- R3 payload의 selected candidate가 R1/R2 compact view보다 앞에 있다.
- R1/R2/previous memory LLM view에 전체 provenance ID 목록이 없다.
- 원본 프레임의 provenance는 유지된다.
- RawSource 원문 text가 R3 payload에 존재한다.
- compact payload 크기가 회귀 테스트 상한 안에 든다.
- 완전 통합 qwen-turn에서 R material이 node_2/node_3까지 전달된다.
