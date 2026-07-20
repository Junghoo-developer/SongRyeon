# ORDER 280: L1 Artifact Contract Live Stability Audit v0

- 상태: 감사 완료
- 작성일: 2026-07-20
- 선행 발주: ORDER 279

## 1. 문제

ORDER 279는 명시 문서 요구 관계를 구조화하고 CODE가 실제 원문 읽기 기록과 대조하는
계약을 만들었다. 결정론적 테스트는 통과했지만, 로컬 Qwen 14B가 복합 사용자 문장에서
`exact_one / all_of / any_of / ordered_fallback`을 안정적으로 선택하는지는 확인되지 않았다.

## 2. 목표

제품 코드를 수정하지 않고 실제 Qwen L1만 좁게 호출해 다음을 분리 측정한다.

1. 올바른 요구 모드를 선택하는가.
2. 올바른 artifact 발생 순번을 선택하는가.
3. schema/parse/adapter 실패와 timeout은 얼마나 발생하는가.
4. 실패 시 CODE가 `RULE_STUB`으로 정직하게 닫는가.

## 3. 시험 행렬

각 사례를 2회 반복한다.

| 사례 | 사용자 요구 | 기대 모드 | 기대 순번 |
| --- | --- | --- | --- |
| A | 문서 하나 읽기 | `exact_one` | `[1]` |
| B | 문서 두 개 모두 읽기 | `all_of` | `[1, 2]` |
| C | 문서 둘 중 하나 읽기 | `any_of` | `[1, 2]` |
| D | A가 없으면 B 읽기 | `ordered_fallback` | `[1, 2]` |
| E | 명시 문서 없는 탐색 요청 | `not_applicable` | `[]` |

단독 L1 시험이 끝난 뒤 D 사례를 전체 L루프로 1회 실행할 수 있다. 단독 시험 결과가 이미
timeout 또는 schema 실패로 불안정하면 전체 실행을 성공 증거로 과장하지 않는다.

## 4. 기록할 절대정보

- 모델 ID와 transport
- 호출별 소요 시간
- LLM call failure type, parse status, validation status
- `goal_generation_source`
- `llm_goal_judgement_status`
- `explicit_artifact_reference_count`
- `artifact_requirement_mode`
- `artifact_reference_occurrence_indices`
- `artifact_requirement_reason`

모드 선택이 사용자 의미와 맞는지에 대한 평가는 감사자의 해석으로 별도 표시한다.

## 5. 판정 기준

- `stable`: 10회 모두 기대 모드·순번과 일치하고 LLM 실패가 없다.
- `partially_stable`: 안전한 구조 출력은 유지되지만 일부 모드·순번 오선택 또는 LLM 실패가 있다.
- `unstable`: 절반 이상이 오선택/실패하거나 같은 입력의 두 실행 결과가 반복적으로 충돌한다.

CODE fallback이 성공으로 위장하지 않으면 안전성 경계는 통과로 기록하되, 모델 적용 품질과
분리한다.

## 6. 금지

- 감사 중 프롬프트 수정
- 사용자 문장 키워드 휴리스틱 추가
- 잘못된 Qwen 출력을 CODE가 의미적으로 교정
- 예산, router, L continuation, R/Neo4j 변경
- 단독 L1 성공을 전체 L루프 성공으로 과장

## 7. 완료 조건

- 10회 L1 결과와 시간·실패 정보를 실행 기록에 남긴다.
- 기대값과 실제값을 표로 비교한다.
- 코드 계약 안전성과 Qwen 적용 품질을 별도로 판정한다.
- 다음 행동이 프롬프트 조정, 전용 selector, 모델 변경, 또는 현 상태 유지 중 무엇인지 좁힌다.
