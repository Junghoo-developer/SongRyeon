# ORDER 172: Night Token Layer Auto Reduce Until Context Budget v0

## 1. Goal

ORDER_171의 token-budget layer summary를 사람이 수십 번 반복 실행하지 않아도 되게 한다.

목표는 "몇 계층까지"를 고정 숫자로 정하는 것이 아니라, 현재 활성 summary layer 전체량이 target context budget 이하가 될 때까지 계층 요약을 자동으로 조금씩 진행하는 것이다.

## 2. Command

```powershell
python main.py night-summarize-token-layer --llm-mode qwen --max-bundle-chars 8000 --until-context-budget --target-context-chars 12000 --max-layer-depth 5 --max-steps 5
```

Neo4j까지 반영:

```powershell
python main.py night-summarize-token-layer --llm-mode qwen --max-bundle-chars 8000 --until-context-budget --target-context-chars 12000 --max-layer-depth 5 --max-steps 5 --write-vessel
```

## 3. Rules

- 기본 one-bundle-at-a-time 동작은 유지한다.
- `--until-context-budget`을 켰을 때만 자동 반복한다.
- 자동 반복은 한 번에 무제한으로 돌지 않는다.
- `--max-steps`로 이번 실행에서 처리할 최대 bundle 수를 제한한다.
- layer 2 queue가 미완료이면 먼저 layer 2를 계속 처리한다.
- layer N이 완료된 뒤 그 layer의 성공 summary 전체 문자 수가 `target_context_chars` 이하이면 멈춘다.
- 아직 크면 layer N+1 queue를 만든다.
- `max_layer_depth`에 도달하면 더 깊게 가지 않고 멈춘다.
- v0 budget 단위는 tokenizer가 아니라 code-counted characters다.
- 실패 bundle은 다음 layer 재료로 쓰지 않는다.
- code는 의미 요약을 쓰지 않는다.

## 4. Non-goals

- 정확 tokenizer adapter는 만들지 않는다.
- semantic axis는 만들지 않는다.
- R loop live route는 열지 않는다.
- failed bundle retry policy는 만들지 않는다.
- 원본/기존 summary node를 삭제하거나 덮어쓰지 않는다.

## 5. Test Plan

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_172_night_token_layer_auto_reduce.py -q
python main.py fast-test --profile graph
git diff --check
```
