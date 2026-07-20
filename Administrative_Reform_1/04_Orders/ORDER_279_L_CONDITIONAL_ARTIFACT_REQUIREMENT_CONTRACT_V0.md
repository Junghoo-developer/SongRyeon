# ORDER 279: L Conditional Artifact Requirement Contract v0

- 상태: 구현 및 검증 완료
- 작성일: 2026-07-20
- 선행 감사: ORDER 278

## 1. 문제

L1은 `A가 없으면 B`라는 사용자 조건을 자유문장에는 보존할 수 있지만, 현재 schema는
명시 문서 사이의 관계를 구조적으로 표현하지 못한다. L2가 B 원문을 실제로 읽어도 최신
L3는 존재하지 않는 A 하나만 목표로 남겨 `partial`로 닫을 수 있다.

## 2. 목표

명시 문서 요구 관계를 다음 네 종류와 미적용 상태로 제한해 기록한다.

- `exact_one`: 지정된 문서 하나가 필요하다.
- `all_of`: 지정된 문서를 모두 읽어야 한다.
- `any_of`: 지정된 문서 중 하나를 읽으면 된다.
- `ordered_fallback`: 앞 문서가 없을 때 뒤 문서를 순서대로 허용한다.
- `not_applicable`: 구조화된 명시 문서 요구 계약을 만들지 않았다.

LLM은 사용자 요청에서 요구 관계와 참조 순번을 판단한다. CODE는 사용자 문장에서 이미
추출한 참조 목록, resolver 상태, 실제 read_doc ID를 대조한다.

## 3. 구현 범위

1. L1 입력에 code가 추출한 명시 artifact 참조와 발생 순번을 제공한다.
2. `L1GoalFrame`에 요구 모드, 선택한 참조 순번, 이유, 전체 참조 수를 기록한다.
3. L1이 목록 밖 순번을 선택하면 schema 실패로 닫는다.
4. explicit artifact resolver frame을 revision L3에도 전달한다.
5. L3 code goal match가 요구 모드별로 실제 read_doc ID를 검사한다.
6. 기존 revision semantic completion policy를 재사용해 다음 조건이 모두 맞을 때만
   `achieved`로 승격한다.
   - 요구 관계 충족
   - 최소 원문 수 충족
   - L3 semantic match
7. 기존 단일 hint 경로는 `not_applicable`의 호환 경로로 유지한다.

## 4. 권한 경계

- 사용자 문장의 `all/any/fallback` 의미 선택: L1 LLM의 혼합 판단
- 참조 문자열 추출과 발생 순번: CODE 절대정보
- 참조의 실제 문서 ID와 존재 상태: CODE resolver 절대정보
- 실제 원문 열람 ID와 count: CODE tool record 절대정보
- 읽은 내용이 질문에 의미상 맞는지: L3 LLM 판단
- 최종 `achieved` 승격: 위 구조 조건을 대조하는 CODE guard

CODE는 자유문장 키워드를 새로 해석해 요구 모드를 만들지 않는다.

## 5. 테스트

1. `ordered_fallback`: 첫 참조 `not_found`, 둘째 unique 원문 읽기면 구조 match다.
2. `ordered_fallback`: 첫 참조가 unique인데 둘째만 읽으면 match가 아니다.
3. `all_of`: 일부만 읽으면 partial이다.
4. `any_of`: 허용된 하나를 읽으면 matched다.
5. 목록 밖 참조 순번은 L1 validator가 거부한다.
6. resolver frame이 revision L3 source IDs에 보존된다.
7. 조건부 대체 구조 match와 semantic match가 함께 맞으면 revision은 `achieved`와
   `stop_achieved`로 닫힌다.
8. 기존 exact lookup과 후보-only guard가 회귀하지 않는다.

## 6. 금지

- 사용자 문장 키워드 휴리스틱으로 요구 모드 생성
- resolver에서 unique인 아무 문서나 자동 성공 처리
- 대체 문서를 원래 문서로 위장
- L3 semantic validator 또는 node_4 guard 약화
- 검색/도구/continuation 예산 증가
- L/R router, R loop, Neo4j 변경

## 7. 완료 조건

- ORDER 278 사례 B가 구조적으로 `ordered_fallback`을 표현할 수 있다.
- 대체 원문을 읽은 절대 사실과 대체가 허용됐다는 LLM 판단의 출처가 분리된다.
- 조건부 성공과 다중 문서 전부 읽기 계약을 혼동하지 않는다.
- compileall, 표적 pytest, 전체 pytest, smoke-test를 통과한다.
