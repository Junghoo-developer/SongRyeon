# ORDER 255: L Candidate vs Original Material Status v0

## 상태

구현 및 검증 완료.

## 문제

현재 L 검색 경로는 검색 후보가 있으나 `read_doc` 원문을 하나도 확보하지 못한 경우에도
다음 상태를 연달아 기록할 수 있다.

```text
CODE_STATUS:no_candidate_document_read
CODE_STATUS:l3_input_evidence_available
CODE_STATUS:stop_success_candidates_preserved
```

이후 code fallback L3는 후보 개수와 `stop_success`만 보고 `achieved`를 만들 수 있다.
따라서 “검색 후보가 있다”와 “원문 근거를 실제 확보했다”가 성공 상태에서 섞인다.

## 목표

L의 근거 확보 상태를 다음 절대 상태로 분리한다.

```text
none
candidates_only
original_material_acquired
```

- `none`: 검색 후보와 비어 있지 않은 원문 모두 없음
- `candidates_only`: 검색 후보는 있지만 비어 있지 않은 문서/코드 원문은 없음
- `original_material_acquired`: 비어 있지 않은 문서 또는 코드 원문 record가 하나 이상 있음

이 상태는 의미 적합성 판정이 아니다. 원문이 사용자 질문에 유용한지는 L3 LLM이 판단한다.

## 원문 요구 상태

L1이 선언한 `minimum_read_documents`와 실제 원문 수를 코드가 대조해 다음 상태를 만든다.

```text
not_required
satisfied
unsatisfied
```

L1의 요구량 자체는 LLM 판단에서 나온 값이다. 코드는 그 값을 의미적으로 수정하지 않고
실제 비어 있지 않은 원문 record count와 비교만 한다.

## L control 정직성

검색 후보가 양수지만 문서 원문을 하나도 읽지 못한 search path는 다음으로 닫는다.

```text
decision = stop_candidate_only
reason = CODE_STATUS:stop_candidate_only_without_original_material
budget stop_reason = low_yield_stop
```

`completed`와 `stop_success_candidates_preserved`로 다시 덮지 않는다.

## L3 운영 상태

- `stop_success + original_material_acquired`이면 운영 성공 후보가 될 수 있다.
- `candidates_only`는 최대 `partial`이다.
- LLM 의미 판정은 code operation status를 승격하지 않고 필요하면 더 낮출 수만 있다.
- 원문이 질문과 맞는지는 기존 goal/semantic match guard가 계속 판단한다.

## 전달 범위

다음 위치에 절대 상태를 보존한다.

- `L3AchievementFrame`
- `LLoopReturnSummaryFrame`
- node_0의 L return memory item
- `Node3InputBriefFrame`
- node_3 LLM payload와 prompt 경계
- terminal/runtime 출력

## 금지

- 임베딩 점수 threshold 추가 금지
- 키워드 관련도 휴리스틱 추가 금지
- 검색 후보를 원문으로 계산하는 것 금지
- context pack 문서를 실제 `read_doc`으로 계산하는 것 금지
- 코드가 원문의 의미 적합성을 판정하는 것 금지
- L/R 횟수, node_2 권한, node_4 guard 변경 금지

## 검증

1. 후보 1개, 원문 0개이면 `candidates_only`, L3 `partial`이다.
2. 비어 있지 않은 문서 원문 1개이면 `original_material_acquired`이다.
3. 빈 extract record는 원문 확보로 세지 않는다.
4. L1 최소 원문 요구를 못 채우면 `unsatisfied`다.
5. 후보만 확보한 L control은 `stop_candidate_only`다.
6. node_0, node_3 brief, terminal에서 상태가 보존된다.
7. compileall, pytest, smoke-test를 통과한다.
