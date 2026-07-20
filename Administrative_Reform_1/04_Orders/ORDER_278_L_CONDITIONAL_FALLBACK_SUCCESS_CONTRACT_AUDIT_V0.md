# ORDER 278: L Conditional Fallback Success Contract Audit v0

- 상태: 감사 완료
- 작성일: 2026-07-20
- 완료일: 2026-07-20

## 1. 배경

ORDER 276 사례 B에서 사용자는 존재하지 않는 문서를 먼저 요청하면서, 없으면 실제
ORDER 275 문서를 다시 검색해 원문을 읽으라고 명시했다. L은 대체 원문 1개를 확보하고
내용도 답했지만 revision 3회 뒤 최신 L3 상태는 `partial`, continuation은
`stop_failed_final`로 끝났다.

## 2. 감사 질문

1. L1이 사용자의 조건부 대체 허용을 성공 조건에 보존했는가?
2. L2 revision은 어떤 목표와 후보 ID를 전달받았는가?
3. L3는 대체 문서를 읽은 사실과 원래 문서 부재를 어떻게 판정했는가?
4. code의 명시 문서 match 규칙이 대체 성공을 구조적으로 표현할 수 있는가?
5. 이 현상은 모델 성능, prompt, schema, code contract 중 어디의 한계인가?

## 3. 범위

- ORDER 276 사례 B export 재감사
- L1 goal frame과 success condition
- explicit artifact reference frame
- L2 initial/revision query frames
- tool result와 read_doc ID
- L3 initial/revision achievement frames
- continuation과 L return summary
- 관련 prompt/schema/code

## 4. 금지

- 감사 중 코드·prompt·schema 수정
- 대체 문서를 원래 문서로 위장
- 원래 실패 record 삭제
- 질문 단어 휴리스틱 추가
- validator 약화
- 예산·반복 횟수 증가

## 5. 완료 조건

1. 실행 순서를 record ID와 상태값으로 복원한다.
2. 직접 원인과 구조적 원인을 분리한다.
3. code가 판단할 절대정보와 LLM이 판단할 대체 적합성을 구분한다.
4. 작은 후속 발주 후보를 제안하되 구현하지 않는다.

## 6. 감사 결론

- L1은 조건부 대체 요청을 자유문장 목표와 성공 조건에는 보존했다.
- L2는 존재하지 않는 첫 파일의 실패 뒤 ORDER 275 후보를 검색했고, 실제 대체 원문 1개를 읽었다.
- 최신 revision L3에는 명시 문서 resolver frame과 controller 성공 판정이 전달되지 않았다.
- 현재 L3 목표 대조는 `requested_doc_hint` 하나만 표현하므로 `원본 A가 없으면 B 허용` 계약을 구조적으로 판정할 수 없다.
- 따라서 사례 B의 `partial`은 검색 실패가 아니라 조건부 대체 성공 계약의 구조적 부재가 주원인이다.
- L3 의미 LLM이 대체 문서를 `matched`로 판단한 것은 prompt의 단일 문서 규칙과 충돌했지만,
  code guard가 최종 `achieved` 승격을 막아 과장된 성공은 공개되지 않았다.

상세 근거와 후속 설계 경계는
`05_Execution_Records/order_278_l_conditional_fallback_success_contract_audit_2026_07_20_001.md`에 남긴다.
