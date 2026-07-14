# ORDER 255 실행 기록: L 후보 확보와 원문 확보 상태 분리

## 결과

구현 및 검증 완료.

## 원인

기존 L search path는 실제 문서 원문을 읽지 못했을 때 먼저
`CODE_STATUS:no_candidate_document_read`를 기록하면서도, 뒤에서 다시
`completed`와 `stop_success_candidates_preserved`로 상태를 덮을 수 있었다.

L3 code fallback은 검색 후보 수와 `stop_success`를 보고 `achieved`를 만들 수 있었기 때문에,
문서 주소만 찾은 상태가 문서 원문까지 확보한 상태처럼 보일 수 있었다.

## 새 절대 상태

코드는 비어 있지 않은 실제 원문 record의 존재만 세어 다음 상태를 만든다.

```text
none
candidates_only
original_material_acquired
```

- `none`: 검색 후보와 비어 있지 않은 원문이 모두 없다.
- `candidates_only`: 검색 후보는 있으나 비어 있지 않은 원문은 없다.
- `original_material_acquired`: `read_doc`, `read_artifact`, `read_code_file` 중 비어 있지 않은 원문이 하나 이상 있다.

이 상태는 원문의 관련성이나 품질을 뜻하지 않는다. 코드는 원문이 존재하는지만 확인하고,
질문에 유용한지에 대한 의미 판단은 L3 LLM의 책임으로 유지했다.

## 원문 요구 상태

L1이 선언한 `minimum_read_documents`와 실제 원문 수를 코드가 비교해 다음을 기록한다.

```text
not_required
satisfied
unsatisfied
```

L1의 요구량 자체는 LLM 판단이다. 코드는 요구량을 임의로 바꾸지 않고 수량만 대조한다.

## L control 변경

검색 후보는 있지만 원문이 없는 search path를 다음 상태로 닫는다.

```text
decision = stop_candidate_only
reason = CODE_STATUS:stop_candidate_only_without_original_material
budget stop_reason = low_yield_stop
```

따라서 `candidates_only`는 L3에서 최대 `partial`이며, 원문 확보 성공으로 승격되지 않는다.
비어 있지 않은 원문을 실제 확보한 기존 정상 경로는 계속 `stop_success`와 `achieved` 후보가 된다.

## 전달 범위

새 절대 상태와 원문 수는 다음 경로에 보존했다.

- `L3AchievementFrame`
- `LLoopReturnSummaryFrame`
- node_0 L return memory item
- `Node3InputBriefFrame`
- node_3 LLM payload와 prompt 경계
- terminal/runtime 출력

node_3는 이제 `candidates_only`를 실제 원문 읽기 성공이나 L 목표 달성으로 표현하지 않도록
명시적인 경계를 받는다.

## 테스트

전용 테스트는 검색 후보가 있으나 `read_doc` 원문이 빈 경우와,
실제 비어 있지 않은 원문을 읽은 정상 대조군을 함께 검증했다.

```text
후보 있음 + 원문 0:
  evidence_acquisition_status = candidates_only
  original_material_count = 0
  original_material_requirement_status = unsatisfied
  L3 achievement_status = partial
  final_control_decision = stop_candidate_only

후보 있음 + 원문 1:
  evidence_acquisition_status = original_material_acquired
  original_material_count = 1
  original_material_requirement_status = satisfied
  L3 achievement_status = achieved
  final_control_decision = stop_success
```

## 검증

```text
python -m compileall songryeon_core main.py
passed

L 관련 집중 회귀시험
66 passed

ORDER 255 전용 및 schema 시험
4 passed

python -m pytest
434 passed, 5 deselected in 80.33s

python main.py smoke-test
SMOKE_TEST_OK

git diff --check
passed
```

## 일부러 하지 않은 것

- 임베딩 점수 또는 키워드 관련도 휴리스틱 추가
- 검색 후보를 실제 원문으로 계산
- context pack 문서를 `read_doc` 실행으로 계산
- 코드가 원문의 의미 적합성을 판정
- L/R 반복 횟수 변경
- node_2 또는 node_4 권한 변경

## 남은 위험

- `original_material_acquired`는 원문이 존재한다는 절대정보일 뿐, 질문과 관련 있다는 보증이 아니다.
- L3 LLM의 관련성 판단 품질은 별도 live 시험 대상이다.
- 문서 원문을 일부만 반환하는 도구 정책이 생기면, 그 record가 무엇을 의미하는지 별도 절대 상태가 필요할 수 있다.
