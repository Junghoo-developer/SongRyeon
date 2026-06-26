# Node3 Code Grounding Block - 2026-06-25-001

## 요청

node_3 LLM이 `근거 기준:` 블록의 count를 직접 생성하지 못하게 하고,
code가 `Node3InputBriefFrame`의 절대 count로 grounding block을 고정 생성하게 한다.

## 구현

`songryeon_core/nodes/node_3_reporter.py`에서 최종 node_3 report 조립을 바꿨다.

이제 LLM reporter는 본문을 쓰고, code가 다음 블록을 앞에 붙인다.

```text
근거 기준:
- 읽은 문서: N개
- 검색 후보 문서: N개
- 현재 턴 실행 순서 자료: N개
- 답변 한계: ...
```

count source:

- `읽은 문서`: `len(Node3InputBriefFrame.read_documents)`
- `검색 후보 문서`: `Node3InputBriefFrame.search_candidate_count`
- `현재 턴 실행 순서 자료`: `len(Node3InputBriefFrame.runtime_tasks)`

LLM이 legacy `rendered_markdown`에 잘못된 `근거 기준:` 블록을 포함해도,
code assembly가 그 블록을 제거하고 본문만 사용한다.

## Prompt/Brief 변경

`songryeon_core/prompts/node_3_reporter_v0.md`는 이제 `body_markdown`만 반환하도록 지시한다.

`songryeon_core/nodes/node_2_handoff.py`의 reporting rule도
근거 기준 블록은 code가 고정 생성하고 node_3 LLM은 본문만 작성한다고 말한다.

## 유지한 guard

`songryeon_core/nodes/node_4_gatekeeper.py`의 grounding count guard는 제거하지 않았다.

이번 패치 뒤에는 LLM count 실수가 최종 report에 들어가지 않으므로,
count mismatch가 발생하지 않아 pass된다.

## 검증

```powershell
python -m compileall songryeon_core main.py
```

결과: 통과.

```powershell
python main.py smoke-test
```

결과: 통과. `SMOKE_TEST_OK`.

관련 smoke 값:

```text
node4_grounding_count_guard=pass
```

실 qwen-turn:

```powershell
python main.py qwen-turn "최대한 많은 내부 문서를 아무거나 골라서 읽고 이를 총합해서 지금 너가 무엇인지 스스로 추측해봐" --timeout 120 --pretty
```

결과:

- `node_3 input brief`: `reportable_documents=2`, `search_candidates=12`, `runtime_tasks=13`
- final answer grounding block:
  - `읽은 문서: 2개`
  - `검색 후보 문서: 12개`
  - `현재 턴 실행 순서 자료: 13개`
- `node_4 gatekeeper: pass`

## 남은 위험

위 qwen-turn 본문에서 node_3가 여전히 "노드 3" 관점으로 자신을 설명하는 표현이 일부 나왔다.

이번 긴급 패치의 목표는 count를 code 절대정보로 고정하는 것이므로,
자기정의 표현 차단은 별도 좁은 guard/prompt 패치 후보로 남긴다.
