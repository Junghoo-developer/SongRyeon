# ORDER 088: Node3 Runtime Task Sequence Brief

## 상태

구현 완료.

## 문제

Task Ledger v0 구현 이후 runtime 출력에는 현재 턴의 task 장부가 보였다.

하지만 node_3 최종 보고자는 그 장부를 직접 받지 못했다.

그 결과 사용자가 다음처럼 물었을 때 문제가 생겼다.

```text
방금 턴에서 어떤 노드들이 어떤 순서로 task로 기록됐는지 설명해줘
```

runtime view에는 이미 task 순서가 있었지만, node_3는 L루프가 읽은 문서만 보고 답변했다.

따라서 node_3는 "문서에는 그런 기록이 없다"고 답할 수 있었다.

이는 환각은 아니지만 사용자 요청 달성에는 실패한 상태다.

## 원칙

휴리스틱으로 해결하지 않는다.

금지:

```text
사용자 문장에 "방금", "이번 턴", "task ledger"가 있으면 특별 분기한다.
```

대신 구조적으로 해결한다.

허용:

```text
node_3에게 항상 현재 턴 실행 순서 자료를 전달한다.
```

이렇게 하면 사용자가 실행 순서를 묻든 묻지 않든, node_3는 같은 형식의 브리프를 받는다.

## 구현

`Node3BriefRuntimeTask`를 추가한다.

이 frame은 node_3가 현재 턴 실행 순서를 설명할 때 사용할 수 있는 최소 요약이다.

포함하는 정보:

- `step_index`
- `node_label`
- `mode`
- `status`
- `model_label`
- `evidence_trace_count`
- `evidence_data_count`

의도적으로 포함하지 않는 정보:

- raw trace ID
- raw data ID
- raw task ID

## node_3 brief 변경

`Node3InputBriefFrame`에 `runtime_tasks`를 추가한다.

node_3 LLM payload에는 다음 이름으로 전달한다.

```text
runtime_task_sequence
```

단, 사용자 답변에서는 raw payload field name을 그대로 말하지 않고 "현재 턴 실행 순서 자료"라고 부르게 한다.

## 시점 경계

node_3에게 전달되는 실행 순서 자료는 node_3 보고문 생성 직전의 snapshot이다.

따라서 최종 runtime task ledger에는 이후 실행되는 node_3 report와 node_4 gatekeeper task가 추가될 수 있다.

이 경계를 숨기지 않는다.

## node_4 변경

node_4 gatekeeper는 이제 다음 세 가지를 근거 재료로 인정한다.

- `read_documents`
- `allowed_claims`
- `runtime_task_sequence`

단, raw 내부 추적 ID가 최종 답변에 노출되면 여전히 반려해야 한다.

## 검증 기준

다음이 통과해야 한다.

```text
python -m compileall songryeon_core main.py dry_run.py
python main.py smoke-test
python main.py qwen-turn "방금 턴에서 어떤 노드들이 어떤 순서로 task로 기록됐는지 설명해줘" --timeout 120 --include-report
```

Qwen 실테스트에서 node_3는 문서 검색 실패로 도망가지 않고, 현재 턴 실행 순서 자료를 바탕으로 11개 실행 단계를 설명했다.

## 현재 한계

node_3가 받는 실행 순서 자료는 보고문 작성 직전 snapshot이다.

최종 task ledger에 추가되는 node_3/node_4 task까지 node_3가 자기 답변 안에서 완료 사실로 말할 수는 없다.

이 한계는 정상이다.

완료 전의 일을 완료됐다고 말하는 것이 더 위험하다.

