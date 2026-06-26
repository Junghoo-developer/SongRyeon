# L Loop Multi Read And Node4 Count Guard 2026-06-24 001

## 목적

사용자 테스트에서 드러난 두 문제를 동시에 고쳤다.

1. L루프가 여러 문서 읽기 예산을 승인받고도 실제로는 1개 문서만 읽는 문제.
2. node_3 답변의 grounding count가 brief와 달라도 node_4가 통과시키는 문제.

## 구현 1: L Loop Multi Read

`songryeon_core/loops/l_loop.py`를 수정했다.

기존에는 `search_docs` 결과의 첫 번째 문서만 `read_doc`했다.
이제는 검색 후보 doc_id를 순서대로 모아, 다음 조건이 허용하는 동안 여러 문서를 읽는다.

```text
tool_call_count < max_tool_calls
read_doc_count < max_read_doc_calls
input_chars_used < max_input_chars
controller iteration available
```

`max_iterations`도 승인된 `max_read_doc_calls`에 맞춰 최소한 다음만큼 확보한다.

```text
search control + read_doc controls + stop control
```

## 구현 2: Node4 Grounding Count Guard

`songryeon_core/nodes/node_4_gatekeeper.py`를 수정했다.

node_4 LLM이 `pass`를 냈더라도,
보고문의 `근거 기준:` 블록 숫자가 `Node3InputBriefFrame`과 다르면 코드가 `needs_revision`으로 강제한다.

검사 대상은 다음 세 count다.

```text
읽은 문서
검색 후보 문서
현재 턴 실행 순서 자료
```

## 추가 smoke-test

`songryeon_core/runtime/smoke_test.py`에 다음 검증을 추가했다.

```text
budget_consistency_actual_read_doc = 2
node4_grounding_count_guard = needs_revision
```

## 검증

다음을 통과했다.

```text
python -m compileall songryeon_core main.py
python main.py dry-run
python main.py smoke-test
```

수동 fake-turn 검증에서도 여러 문서 요청에서 `read_doc_count 2`가 확인되었다.

