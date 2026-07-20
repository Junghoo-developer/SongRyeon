# ORDER 280 L1 Artifact Contract Live Stability 감사 기록

- 실행일: 2026-07-20
- 상태: 감사 완료, 제품 코드 변경 없음
- 모델: `qwen3:14b`
- transport: direct Ollama
- context: 16,384
- 실행 장치: 100% GPU

## 1. 판정

- 사전 정의한 전체 판정: `partially_stable`
- 단순 계약 `exact_one / all_of / not_applicable`: 안정적
- 복합 관계 `any_of / ordered_fallback`: 불안정
- JSON/schema/transport 안정성: 10/10 통과
- 선택 순번 안정성: 10/10 기대값 일치
- 요구 모드 정확도: 6/10

즉 Qwen은 출력 형식과 문서 번호표는 안정적으로 지켰지만, 두 문서 사이의 의미 관계를
두 복합 사례에서 체계적으로 잘못 분류했다.

## 2. 준비 확인

```text
python main.py qwen-ping --model-id qwen3:14b --timeout 120
status=ok
elapsed=8.3s
transport=ollama
timeout_enforcement_status=enforced_by_ollama_httpx_client
```

## 3. L1 단독 시험 결과

| 사례 | 회차 | 기대 모드 | 실제 모드 | 순번 | 시간 | parse/schema |
| --- | ---: | --- | --- | --- | ---: | --- |
| A | 1 | `exact_one` | `exact_one` | `[1]` | 10.24s | pass/pass |
| B | 1 | `all_of` | `all_of` | `[1,2]` | 10.52s | pass/pass |
| C | 1 | `any_of` | `all_of` | `[1,2]` | 15.80s | pass/pass |
| D | 1 | `ordered_fallback` | `all_of` | `[1,2]` | 17.71s | pass/pass |
| E | 1 | `not_applicable` | `not_applicable` | `[]` | 8.33s | pass/pass |
| A | 2 | `exact_one` | `exact_one` | `[1]` | 9.04s | pass/pass |
| B | 2 | `all_of` | `all_of` | `[1,2]` | 10.66s | pass/pass |
| C | 2 | `any_of` | `all_of` | `[1,2]` | 16.12s | pass/pass |
| D | 2 | `ordered_fallback` | `all_of` | `[1,2]` | 17.72s | pass/pass |
| E | 2 | `not_applicable` | `not_applicable` | `[]` | 8.33s | pass/pass |

- 총 소요 시간: 124.47초
- 평균: 약 12.45초
- LLM failure: 0회
- parse failure: 0회
- schema failure: 0회
- 같은 입력의 반복 결과 충돌: 0회

반복 결과가 같았다는 것은 무작위 흔들림보다 현재 입력/프롬프트에서 일정한 오분류가
발생했음을 뜻한다.

## 4. 좁은 통제 시험

L1의 다른 목표·예산 판단을 모두 제거하고 문서 관계만 묻는 작은 프롬프트로 C와 D를 각각
두 번 더 시험했다.

| 사례 | 기대 모드 | 2회 실제 모드 | parse |
| --- | --- | --- | --- |
| C | `any_of` | `not_applicable`, `not_applicable` | 모두 pass |
| D | `ordered_fallback` | `not_applicable`, `not_applicable` | 모두 pass |

업무량을 줄이는 것만으로는 복합 관계 선택이 회복되지 않았다. 따라서 현재 증거만으로
“L1이 너무 많은 일을 맡아서 생긴 문제”라고 단정할 수 없다. Qwen 14B가 이 enum 의미를
안정적으로 적용하지 못하거나, enum 문법 자체가 이 모델에 적합하지 않을 가능성이 있다.

## 5. 안전성 해석

이번 오분류는 유효 schema 안에서 일어났으므로 CODE는 사용자 문장의 진짜 의미를 직접
알 수 없고 L1 판단을 임의 교정하지 않는다.

- `any_of -> all_of`: 필요한 것보다 더 많이 요구하는 보수적 오판이다.
- `ordered_fallback -> all_of`: 첫 문서가 없으면 구조 match가 완료되지 않아 false negative로
  닫힐 가능성이 높다.

현재 관찰은 거짓 성공보다 불필요한 추가 탐색·partial/failed 종료 쪽으로 기운다. 다만 이는
두 시험 사례에 대한 관찰이며 모든 문장에 대한 일반 보장은 아니다.

ORDER 279의 CODE guard와 결정론적 테스트는 유지된다. 이번 10회에는 LLM 실패가 없어서
라이브 `RULE_STUB` fallback은 실제 발동하지 않았으며, 기존 테스트 증거와 혼동하지 않는다.

## 6. 전체 L루프 재실행을 생략한 이유

단독 L1에서 C와 D가 각각 2/2 동일하게 잘못 분류되었다. 이 상태에서 전체 L루프를 한 번 더
돌리면 잘못 선언된 유효 계약을 비싸게 실행하는 결과가 예상되고, 관계 선택 원인을 더
좁히지 못한다. 따라서 ORDER 280의 라이브 증거는 L1 경계에서 닫았다.

## 7. 다음 수

바로 전용 selector를 제품에 추가하는 것은 아직 이르다. 좁은 통제 프롬프트도 0/4였기
때문이다. 다음 단계는 다음 둘 중 하나를 작은 비교 실험으로 결정하는 것이다.

1. enum 대신 자연어 관계 설명을 L1이 쓰고, 별도 강한 모델/사람이 구조 값으로 승인한다.
2. 로컬 후보 모델을 바꿔 같은 14개 시험을 재실행한다.

CODE 키워드 휴리스틱으로 `또는/없으면`을 직접 판정하는 방식은 현재 철학과 맞지 않으므로
권장하지 않는다.

## 8. 검증 및 변경 범위

```text
git diff --check
PASS
```

제품 코드, prompt, schema, 예산, router, L/R loop, Neo4j는 변경하지 않았다.
