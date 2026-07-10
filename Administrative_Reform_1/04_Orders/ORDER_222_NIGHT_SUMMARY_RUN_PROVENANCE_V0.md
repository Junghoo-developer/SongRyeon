# ORDER 222: Night Summary Run Provenance v0

## 목표

심야 정부가 생성하는 LLM 요약 그래프 노드에 “몇 번째/어떤 심야 요약 실행에서 만들어졌는가”를 절대정보로 명시한다.

## 배경

그래프 DB에는 원본 source, source leaf 요약, token budget bundle 요약, TimeBundle 요약이 쌓인다. 앞으로 동적 source가 변경되면 기존 요약을 삭제하지 않고 무효화하거나 추적해야 한다.

이를 안정적으로 하려면 요약 노드 자체에 다음 좌표가 있어야 한다.

- 어떤 summary run에서 생성됐는가
- 어떤 night turn에서 생성됐는가
- 어떤 night batch에 속하는가
- 언제 생성됐는가
- 이 출처 좌표가 기록됐는가

## 구현 범위

다음 LLM 요약 frame/node payload에 run provenance 필드를 추가한다.

- `NightSourceLeafSummaryFrame`
- `NightTimeBundleSummaryFrame`
- `NightTokenBudgetBundleSummaryFrame`

추가 필드:

- `summary_run_id`
- `night_turn_id`
- `night_batch_id`
- `summary_created_at`
- `run_provenance_status`

이번 MVP에서 새로 생성되는 요약은 `run_provenance_status=recorded`로 기록한다.
기존 legacy payload를 일괄 무효화하지 않기 위해, 필드가 없는 옛 요약은 `legacy_not_recorded` 상태를 허용한다.

## 하지 않는 것

- 기존 Neo4j 기록 일괄 삭제 또는 일괄 무효화
- 기존 요약 내용 재작성
- LLM이 run provenance를 직접 쓰게 하기
- source 의미 판단 변경
- R loop, L loop, node_1 routing 변경
- 새로운 외부 DB 구조 추가

## 완료 조건

- 새 source leaf 요약 payload에 run provenance가 기록된다.
- 새 time bundle 요약 payload에 run provenance가 기록된다.
- 새 token budget bundle 요약 payload에 run provenance가 기록된다.
- legacy 요약을 즉시 불량으로 만들지 않는다.
- `python -m compileall songryeon_core main.py`
- 관련 pytest 통과
- 가능한 경우 quick smoke 통과

