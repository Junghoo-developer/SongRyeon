# L3 Goal Match Guard MVP 2026-06-23 001

## 목적

L3가 `search_docs 후보가 있음`만 보고 너무 쉽게 `achieved`를 선언하지 않도록 막는다.

특히 사용자가 특정 문서나 문서 경로를 요구했는데 L루프가 그 문서를 직접 읽지 못한 경우, L3의 목표 달성 판정을 `partial` 또는 `failed`로 낮춘다.

## 구현

1. `L3AchievementFrame`에 문서 목표 매칭 필드를 추가했다.
   - `requested_doc_hint`
   - `read_doc_ids`
   - `search_result_doc_ids`
   - `goal_match_status`
   - `goal_match_reason`

2. L루프가 L3에게 원래 사용자 입력을 넘기게 했다.
   - L3는 사용자 입력에서 문서 경로/문서명 힌트를 추출한다.
   - 실제 `read_doc`으로 읽은 문서 ID와 `search_docs` 후보 문서 ID를 대조한다.

3. L3 goal match guard를 추가했다.
   - 특정 문서 요청이 없으면 `not_applicable`.
   - 요구 문서를 직접 읽었으면 `matched`.
   - 검색 후보에는 있지만 직접 읽지 못했으면 `partial`.
   - 다른 후보만 있고 요구 문서는 없으면 `partial`.
   - 증거 자체가 없으면 `missing`.

4. `goal_match_status`가 `partial` 또는 `missing`이면 L3의 `achieved` 판정을 낮춘다.
   - `partial`이면 `achieved -> partial`.
   - `missing`이면 `achieved/partial -> failed`.
   - 이때 `achievement_generation_source`에 `+CODE:GOAL_MATCH_GUARD`를 붙여 코드 안전핀이 개입했음을 드러낸다.

5. 런타임 출력에 L3 문서 목표 매칭 결과를 표시했다.
   - 사용자는 이제 L3가 어떤 문서 힌트를 잡았고, 어떤 문서 ID를 실제 후보/읽기 결과로 봤는지 확인할 수 있다.

## 확인

`python -m compileall songryeon_core main.py`

`python main.py smoke-test`

확인 결과:

- `SMOKE_TEST_OK`
- `l3_goal_match_status`: `partial`
- `l3_goal_match_achievement_status`: `partial`

추가 화면 확인:

`python main.py fake-turn "문서 03_Maps/02_Function_Maps/CODE_STRUCTURE_MAP_v1을 찾아 읽어줘" --pretty --max-tool-calls 1`

확인 결과:

- `L3 문서 목표 매칭: partial`
- `achievement_generation_source`: `LLM:...+CODE:GOAL_MATCH_GUARD`
- 검색 후보는 있었지만 요구 문서를 직접 읽지 못했으므로 L3가 `partial`로 낮췄다.

## 한계

아직 L3가 `partial` 이후 직접 L2로 재검색을 보내지는 않는다.

이번 MVP는 판정 강화와 런타임 정직성 확보까지만 한다. 다음 단계에서 L3의 `partial/failed`를 바탕으로 L2 재검색 또는 1 재라우팅을 설계할 수 있다.
