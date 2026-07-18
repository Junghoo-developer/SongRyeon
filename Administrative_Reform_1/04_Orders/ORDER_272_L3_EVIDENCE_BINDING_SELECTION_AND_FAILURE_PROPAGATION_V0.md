# ORDER 272: L3 Evidence Binding Selection And Failure Propagation v0

## 1. 배경

ORDER 261~262는 L3 의미 판단이 실제 공급 원문에 결속되도록 만들었다. 그러나 현재
계약은 L3 LLM이 원문 발췌를 직접 다시 써야 한다. live Qwen 실행에서는 다음 두
구조 실패가 확인됐다.

- 발췌가 code의 400자 상한을 넘음
- 공백이나 Markdown이 달라져 원문과 완전히 같은 문자열이 아니게 됨

또한 이 실패 뒤 code 운영 판정으로 fallback하면 `llm_semantic_judgement_status=not_run`
만 남는다. 원문을 실제로 읽은 경우에는 L 반환 요약과 node_3 브리프가 이 실패를
`L 달성`처럼 보이게 만들 수 있다.

## 2. 목표

L3가 원문을 다시 쓰지 않고, code가 만든 정확한 원문 조각 번호표를 선택하게 한다.
L3 의미 판단 실패는 원문 확보 상태와 분리해 0→2→3 경계까지 보존한다.

## 3. 구현 범위

1. code가 공급 원문 미리보기를 최대 400자의 연속 조각으로 기계적으로 나눈다.
2. 각 조각에 재현 가능한 `evidence_excerpt_ref`를 붙인다.
3. L3 LLM은 `material_ref`와 `evidence_excerpt_ref`만 선택한다.
4. code는 선택된 번호표가 실제 공급 목록에 있고 해당 재료에 속하는지 검증한다.
5. code는 검증된 번호표를 원문의 정확한 문자열로 다시 연결해 achievement frame에
   보존한다.
6. L3 의미 판단의 실행 상태와 실패 종류·이유를 L3 achievement, L return summary,
   node_3 brief/payload에 보존한다.
7. 원문은 확보됐지만 L3 의미 판단이 실패한 경우, 자동 재검색은 열지 않고 route 2로
   진행하되 `L3 의미 검증 실패` 태도를 명시한다.
8. L3 prompt의 허용 enum과 실제 지시를 일치시킨다.

## 4. 정보 권한

- 조각 경계, 번호표, 번호표-원문 대응, LLM call 실패 종류는 code-owned absolute다.
- 어떤 조각이 사용자 질문을 의미상 뒷받침하는지는 L3 LLM이 판단한다.
- code는 의미상 좋은 조각을 고르지 않는다.
- 고정 길이 분할은 의미 휴리스틱이 아닌 공개된 기계적 입력 정책이다.

## 5. 실패 처리

- L3 성공: `llm_semantic_execution_status=ran`, 실패 종류 `none`.
- adapter 미제공: `not_run`, 실패 종류 `not_run`.
- parse/schema/adapter 실패: `failed`와 실제 실패 종류·이유를 보존한다.
- L3 실패 뒤에도 실제 읽은 원문과 code 운영 count는 유지한다.
- 원문 요구량이 충족됐다면 L3 실패만으로 L을 자동 반복하지 않는다.

## 6. 금지

- L3 원문 결속 validator 약화
- LLM 대신 code가 의미 발췌 선택
- 실패를 `not_run`으로 덮기
- node_4 guard 약화
- L/R 반복 횟수, 도구 예산, 라우팅 의미 변경
- 새 DB, scheduler, W loop 추가

## 7. 완료 조건

1. 조각을 다시 이어 붙이면 공급 원문 미리보기와 정확히 같다.
2. 모든 조각은 400자 이하이며 번호표가 재현 가능하다.
3. L3는 공급된 번호표만 선택할 수 있고 알 수 없는 번호표는 거부된다.
4. 검증된 번호표는 정확한 원문 발췌로 복원된다.
5. L3 실패 상태가 L return summary와 node_3 brief/payload까지 보존된다.
6. 원문 확보 + L3 실패는 의미 검증 실패를 숨기지 않고 route 2로 닫힌다.
7. compileall, 표적 pytest, 전체 pytest, smoke-test를 통과한다.

## 8. 후속 경계

이번 발주는 L3 입력 계약과 실패 정직성만 다룬다. 조각 크기 최적화, 의미 단위 분할,
LLM retry, L 재검색 정책은 live 결과를 다시 본 뒤 별도 결재한다.
