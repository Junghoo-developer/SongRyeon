# ORDER 084: Node4 Remand Blocking

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: node_4가 `needs_revision`을 냈는데도 answer가 그대로 사용자에게 출력된 실행 로그  
**목표**: node_4가 반려한 답변을 최종 성공 답변처럼 내보내지 않게 한다.

## 배경

현재 실행 로그에서 다음 현상이 확인됐다.

```text
node_4 gatekeeper: needs_revision
reason: report exposes internal code identifiers

[answer]
...
내부 코드 식별자가 포함된 답변이 그대로 출력됨
```

이것은 4의 검사 결과를 runtime에 표시만 하고, 최종 출력 통제에는 연결하지 않은 문제다.

W루프가 들어가면 이 문제는 더 중요해진다.  
W가 위험을 감지해도 4의 반려가 최종 출력에 반영되지 않으면, 시스템은 위험을 알고도 그대로 말하게 된다.

## 구현 범위

1. `node_4:gatekeeper_frame.gate_status`가 `needs_revision` 또는 `failed`이면 최종 answer 출력 경로를 바꾼다.
2. 기본 MVP에서는 자동 재작성 루프를 열지 않는다.
3. 대신 safe blocking answer를 출력한다.
4. 내부 runtime에는 원래 report와 gate reason을 보존한다.

## Safe Blocking Answer

사용자-facing 답변은 다음 원칙을 따른다.

```text
방금 생성된 답변이 내부 검사에서 반려됐다.
이유는 간단히 말한다.
반려된 원문은 최종 답변으로 확정하지 않는다.
필요하면 다시 검색하거나 질문을 좁혀야 한다.
```

금지:

- 반려된 답변을 그대로 출력.
- `needs_revision`을 pass처럼 표시.
- 내부 ID를 다시 노출.
- 4가 새 답변을 쓴 척하기.

## 후속 경로

MVP 후속으로 선택할 수 있는 경로:

1. `4 -> 1 -> W`: 왜 반려됐는지 W가 문제 진단.
2. `4 -> 1 -> L`: 근거 부족이면 L 재검색.
3. `4 -> 1 -> 2 -> 3`: 브리프를 줄여 재작성.
4. `4 -> stop_safe_failure`: 한계를 말하고 종료.

이번 발주에서는 자동 루프를 열지 않고 차단만 구현한다.

## 완료 기준

1. node_4가 `pass`일 때만 기존 answer가 출력된다.
2. node_4가 `needs_revision`이면 final answer는 safe blocking answer로 대체된다.
3. pretty runtime에는 원래 report_generation_source와 gate reason이 남는다.
4. smoke test에 fake node_3 내부 ID 노출 케이스를 추가한다.
5. 해당 케이스에서 사용자-facing answer가 반려 원문을 그대로 포함하지 않는다.
