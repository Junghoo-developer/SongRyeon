# ORDER 171: Night Token Budget Layer Summary v0

## 1. Goal

심야정부가 source leaf 요약을 만든 뒤, 그 요약들을 날짜 단위가 아니라 예산 단위로 묶어 상위 summary layer를 만들게 한다.

이번 MVP의 목표 흐름:

```text
source leaf summary nodes
-> code-generated token budget summary bundle queue
-> one bundle graph node
-> LLM summary graph node attached to that bundle
-> optional Vessel write
```

## 2. Important v0 Budget Boundary

정확한 tokenizer adapter는 아직 없다.

따라서 v0은 토큰 예산 구조를 여는 발주서이지만, 실제 계량 단위는 code가 확정 가능한 `summary_text` 문자 수(`char_budget`)로 둔다. 이 값을 토큰 수라고 숨기지 않는다.

나중에 tokenizer가 추가되면 queue/bundle 구조는 유지하고 budget calculator만 교체한다.

## 3. Required Behavior

- leaf summary graph node 중 `summary_status=ran`, `validity_status=active`, `data_kind=source_leaf_summary`인 것만 대상으로 삼는다.
- code가 summary text 길이를 세고, `max_bundle_chars` 안에 들어가도록 summary node들을 순서대로 묶는다.
- source summary 하나가 budget보다 크면 원문을 자르지 않고 단독 bundle로 둔다.
- queue는 code-generated absolute record로 남긴다.
- 실행은 한 번에 한 bundle만 처리한다.
- bundle graph node는 원본 summary node들을 `CONTAINS` edge로 가진다.
- LLM은 bundle 안의 summary text들을 보고 상위 요약문만 쓴다.
- 여러 summary에 근거한 상위 요약이므로 성공한 summary는 `info_class=mixed`다.
- code는 의미 요약문을 쓰지 않는다.
- 원본 leaf summary node는 삭제/수정하지 않는다.
- optional Vessel/Neo4j write는 명시 `--write-vessel`이 있을 때만 한다.

## 4. Non-goals

- 정확 tokenizer 구현은 하지 않는다.
- semantic axis는 만들지 않는다.
- R loop live route는 열지 않는다.
- CoreEgo 직속 의미축 재편성은 하지 않는다.
- 모든 layer를 한 번에 끝까지 재귀 요약하지 않는다.
- failed bundle 자동 재시도 정책은 만들지 않는다.

## 5. Command

```powershell
python main.py night-summarize-token-layer --store-dir .songryeon_core_cache/night_changed_sources --llm-mode qwen --max-bundle-chars 8000
```

Neo4j까지 매 step 반영:

```powershell
python main.py night-summarize-token-layer --llm-mode qwen --max-bundle-chars 8000 --write-vessel
```

## 6. Test Plan

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_171_night_token_budget_layer_summary.py -q
python main.py fast-test --profile graph
git diff --check
```
