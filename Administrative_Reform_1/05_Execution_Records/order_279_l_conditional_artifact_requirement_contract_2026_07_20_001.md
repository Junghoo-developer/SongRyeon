# ORDER 279 L Conditional Artifact Requirement Contract 실행 기록

- 실행일: 2026-07-20
- 상태: 구현 및 검증 완료
- 선행 감사: ORDER 278

## 1. 해결한 문제

기존 L1은 `A가 없으면 B`라는 조건을 자유문장에만 적었다. L2가 B를 실제로 읽어도
L3는 A 하나만 목표로 남겨 `partial`로 닫을 수 있었다.

이번 구현은 명시 문서 사이의 관계를 다음 구조 값으로 기록한다.

- `exact_one`
- `all_of`
- `any_of`
- `ordered_fallback`
- `not_applicable`

## 2. 구현

### L1 계약

CODE는 사용자 입력에서 명시 artifact 참조를 순서대로 추출해 `occurrence_index`와
`raw_ref`를 L1에 공급한다. L1 LLM은 공급된 순번 안에서 요구 모드, 선택 순번, 이유를
작성한다. 목록 밖 순번, 중복 순번, 모드와 맞지 않는 순번 수는 validator가 거부한다.

### L3 절대 대조

CODE는 L1 계약, explicit artifact resolver frame, 실제 `read_doc` 기록을 대조해 다음을
기록한다.

- 실제 목표 문서 ID
- 실제 읽기와 대응한 문서 ID
- `matched / partial / missing / not_applicable`

`ordered_fallback`은 앞 참조가 `not_found`일 때만 다음 unique 참조를 활성 목표로 삼는다.
앞 참조가 존재하거나 ambiguous/invalid이면 임의로 건너뛰지 않는다.

revision L3 입력에도 resolver frame을 보존했고, 구조 match와 최소 원문 수와 L3 의미
match가 모두 맞을 때 기존 revision 승격 정책으로 `achieved` 처리한다.

### 화면 표시

terminal view는 L1의 요구 모드·참조 수·선택 순번·LLM 이유와 L3의 목표 문서·실제 대응
문서·충족 상태를 분리해 표시한다.

## 3. 권한 경계

- 문서 참조 문자열과 발생 순번: CODE 절대정보
- 사용자 요청의 문서 관계 해석: L1 LLM 판단
- resolver 존재 상태와 실제 읽은 문서 ID: CODE 절대정보
- 읽은 원문이 질문 의미에 맞는지: L3 LLM 판단
- 구조 조건과 의미 조건을 함께 검사한 최종 승격: CODE guard

CODE가 사용자 문장의 `없으면`, `모두`, `하나` 같은 단어를 직접 해석하는 휴리스틱은
추가하지 않았다.

## 4. 결정론적 검증

```text
python -m compileall songryeon_core main.py
PASS

python -m pytest tests/test_order_279_l_conditional_artifact_requirement.py -q
7 passed

python -m pytest
517 passed, 1 skipped, 5 deselected

python main.py smoke-test
SMOKE_TEST_OK

git diff --check
PASS
```

Windows host에서 symbolic link 생성이 불가능한 기존 테스트 1개는 조건부 skip되었다.

## 5. 라이브 Qwen 관찰

시험 요청은 존재하지 않는 첫 문서를 요구하고, 없으면 실제 ORDER 275 문서를 찾아 읽도록
했다.

첫 전체 실행에서 Qwen L1은 두 참조를 받았지만 `exact_one`과 첫 참조만 선택했다. L2는
대체 ORDER 275 원문을 읽었으나 새 CODE guard는 선언된 첫 목표와 불일치를 감지해
성공으로 위장하지 않았다.

프롬프트에 조건부 대체 예시를 추가한 뒤 단독 L1 시험에서는 Qwen이 둘째 참조를
`exact_one`으로 선택했다. 대체 목표 자체는 골랐지만 관계 이름 `ordered_fallback`은
여전히 안정적으로 생성하지 못했다.

두 번째 전체 실행은 L1 호출이 180초 timeout으로 실패해 `RULE_STUB`으로 정직하게
닫혔다. 따라서 이 실행은 구조 계약의 라이브 성공 사례로 세지 않는다.

## 6. 남은 위험

스키마와 CODE 대조는 조건부 계약을 안전하게 표현하고 검증할 수 있다. 그러나 현재 로컬
Qwen 14B가 복합 조건에서 적절한 모드를 안정적으로 고른다고는 아직 말할 수 없다.

이 문제를 숨은 CODE 문장 휴리스틱으로 덮지 않았다. 다음 단계가 필요하다면 새 기능 확장
전에 L1 계약 선택만 좁게 재시험하고, 전용 selector 또는 모델 역할 조정이 필요한지 별도
감사한다.

## 7. 일부러 하지 않은 것

- 검색·도구·continuation 예산 증가
- L/R router와 R loop 변경
- Neo4j 변경
- L3 semantic validator 또는 node_4 guard 약화
- Qwen의 잘못된 계약을 CODE가 임의 교정하는 fallback
