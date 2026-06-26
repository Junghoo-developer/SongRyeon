# Node4 Remand Blocking MVP 2026-06-23 001

## 목표

`node_4`가 `needs_revision` 또는 `failed`를 내면 `node_3`의 보고문을 최종 사용자 답변처럼 그대로 출력하지 않게 한다.

## 바뀐 파일

```text
songryeon_core/runtime/terminal_view.py
songryeon_core/runtime/smoke_test.py
main.py
```

## 구현 내용

- `render_chat_answer()`가 `node_4:gatekeeper_frame`을 먼저 확인한다.
- `gate_status`가 `needs_revision` 또는 `failed`이면 safe blocking answer를 출력한다.
- 반려된 `node_3` 원문 보고문은 DataStore/runtime 기록에는 남지만, 사용자-facing answer에는 그대로 노출하지 않는다.
- `qwen-turn`/`fake-turn`의 일반 JSON 요약에서도 반려된 report preview를 기본적으로 숨긴다.
- smoke test에 node_4 반려 차단 케이스를 추가했다.

## 확인

```text
python main.py smoke-test
```

결과:

```text
SMOKE_TEST_OK
node4_remand_blocked = true
node4_remand_gate_status = needs_revision
```

## 하지 않은 것

- 자동 재작성 루프는 만들지 않았다.
- `4 -> 1 -> L/W/2` 재라우팅은 열지 않았다.
- node_4가 새 답변을 쓰는 것처럼 꾸미지 않았다.

## 학습 포인트

이번 MVP의 핵심은 `node_4`의 판단과 runtime의 강제가 다르다는 점이다.

```text
node_4 = 검사한다.
runtime = 검사 결과를 보고 최종 출력 여부를 강제한다.
```

이제 송련은 문제가 있는 답변을 "문제 있음"이라고 표시만 하는 상태에서 한 단계 나아가, 최종 answer로 확정하지 않는 최소 브레이크를 갖게 됐다.
