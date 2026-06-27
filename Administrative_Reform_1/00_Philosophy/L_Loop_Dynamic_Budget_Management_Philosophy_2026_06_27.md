# L Loop Dynamic Budget Management Philosophy 2026-06-27

## 상태

미승격 철학 문서.

이 문서는 즉시 구현 명령이 아니다. 다음 발주서나 유지 체계 문서로 승격되기 전까지는 설계 방향 기록으로만 취급한다.

## 배경

최근 ORDER 추적 테스트에서 L루프는 다음 단계까지 왔다.

- L 도구 예산과 query 예산을 넓힐 수 있다.
- L3가 `partial`을 내면 L 내부 continuation이 열린다.
- 0은 L3 판정, 이전 query, 읽은 문서, 안 읽은 후보, 남은 예산을 L2에 공급한다.
- L2 revision query planner는 새 검색어를 만들 수 있다.
- L3 revision recheck가 반복된다.

하지만 아직 부족한 점이 있다.

```text
L3가 목표 미달을 말할 수는 있지만,
예산 정책 자체를 어떻게 바꿔야 하는지는 아직 별도 구조가 없다.
```

현재 구현은 대체로 다음 흐름이다.

```text
L3 partial
-> continuation controller
-> L2 revision query
-> search/read attempt
-> L3 recheck
```

아직 다음 흐름은 정식으로 열지 않았다.

```text
L3 partial
-> 예산 부족 또는 context 부족을 구조화해서 요청
-> code budget policy가 명시 상한 안에서 조정
-> 조정된 예산/후보/context packing으로 재시도
```

## 문제의식

예산은 단순히 크게 잡으면 해결되는 값이 아니다.

너무 작으면:

- 문서를 충분히 못 읽는다.
- L3가 계속 `partial`을 낸다.
- 사용자는 "검색을 더 하라"고 했는데도 조기 종료처럼 보인다.

너무 크면:

- Qwen 구조화 실패 가능성이 커진다.
- README, 실행기록, 요약문서가 과하게 들어와 원문 발주서가 밀릴 수 있다.
- node_3가 넓은 근거 묶음을 보고 답하지만, 어떤 근거가 진짜 핵심인지 흐려진다.

따라서 예산은 "무조건 크게"가 아니라 "부족 신호와 정책 상한이 만나는 곳"에서 조정되어야 한다.

## 장기 방향

향후에는 다음과 같은 구조를 검토할 수 있다.

```text
L3BudgetPressureFrame
```

또는 비슷한 이름의 구조화 frame을 두고, L3 또는 L3 이후 controller가 다음을 기록한다.

- 현재 목표 달성 상태
- 부족한 근거 종류
- 부족한 예산 종류
- 남은 후보가 있는데 못 읽은 이유
- context packing 예산 때문에 제외된 문서 존재 여부
- 다음 재시도에서 필요한 budget adjustment request

단, 이 frame이 곧바로 예산을 바꾸면 안 된다.

예산 변경 권한은 code policy에 있어야 한다.

```text
LLM/L3: "무엇이 부족해 보인다"는 판단을 mixed 정보로 제안
code budget policy: 숫자 상한, 남은 횟수, 안전 조건을 보고 승인/거절
```

## 메타정보 경계

절대정보:

- 현재 tool call count
- 현재 query attempt count
- 현재 read_doc count
- 현재 context char/token estimate
- 문서 char_count 또는 file size
- 예산 상한
- 어떤 문서가 included/excluded 되었는지
- 제외 reason code

혼합정보:

- L3가 "이 근거로는 사용자 요구 범위를 충분히 충족하지 못한다"고 판단한 설명
- L3가 "추가 검색/추가 원문/context 확장이 필요하다"고 보는 이유
- L2가 새 query가 더 적절하다고 제안하는 purpose

금지:

- code가 L3의 의미 판단을 몰래 대신해서 "중요한 문서"를 고른 척하지 않는다.
- 예산 변경을 숨은 휴리스틱으로 처리하지 않는다.
- "예산이 넓으니 충분히 읽었다"는 식의 암묵 가정을 두지 않는다.

## 동적 예산 관리 원칙 후보

1. L3는 예산 숫자를 직접 확정하지 않는다.
2. L3는 부족한 근거의 종류를 구조화해서 제안할 수 있다.
3. code는 그 제안을 절대정보처럼 믿지 않고 mixed 판단으로 보존한다.
4. code budget policy는 명시된 상한 안에서만 예산 조정을 승인한다.
5. 승인/거절은 `CODE_STATUS:*` reason code로 기록한다.
6. 예산 조정은 smoke-test 대상이어야 한다.
7. node_3가 보는 최종 근거는 "실제로 공급된 context" 기준이어야 한다.

## 이번에는 미루는 것

이번 단계에서는 동적 예산 변경을 바로 구현하지 않는다.

먼저 다음 문제를 고정한다.

```text
명시된 ORDER/document ID는 임베딩 검색 후보보다 먼저 직접 원문 후보로 잡는다.
node_3에 줄 문서는 whole-document context packing으로 정직하게 고른다.
```

이 구체 구현은 `ORDER_112_EXPLICIT_ARTIFACT_PRIORITY_AND_WHOLE_DOCUMENT_PACKING_V0`로 분리한다.
