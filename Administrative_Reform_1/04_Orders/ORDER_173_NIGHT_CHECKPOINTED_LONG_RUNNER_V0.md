# ORDER 173: Night Checkpointed Long Runner v0

## 1. Goal

심야정부 token layer 요약을 사람이 수동으로 여러 번 치지 않아도 되게 한다.

단, "무식한 한 방"이 아니라 다음 성질을 가진 긴 실행 runner로 만든다.

```text
loop:
  다음 pending bundle 1개 처리
  DataStore/TraceStore 저장
  progress JSONL 기록
  선택 정책에 따라 Vessel write
  failure/runtime/max_steps 조건 확인
```

## 2. Required Behavior

- 기존 `--until-context-budget` 자동 reducer를 유지한다.
- 매 step 뒤 DataStore/TraceStore checkpoint를 남긴다.
- 매 step 진행 상황을 JSONL로 남길 수 있게 한다.
- `--max-runtime-minutes`로 이번 실행의 시간 상한을 둘 수 있게 한다.
- `--stop-on-failure` 기본값으로 실패 bundle이 나오면 멈춘다.
- Vessel write는 다음 모드를 지원한다.
  - `none`
  - `every-step`
  - `at-end`
- 기존 `--write-vessel`은 호환상 `every-step`과 같은 의미로 둔다.
- 중간에 죽어도 재실행 시 queue와 기존 summary node/frame을 보고 이어간다.

## 3. Non-goals

- 정확 tokenizer adapter는 만들지 않는다.
- semantic axis는 만들지 않는다.
- R loop live route는 열지 않는다.
- failed bundle retry policy는 만들지 않는다.
- 원본/기존 summary node를 삭제하거나 덮어쓰지 않는다.

## 4. Command

```powershell
python main.py night-summarize-token-layer --llm-mode qwen --max-bundle-chars 8000 --until-context-budget --target-context-chars 12000 --max-layer-depth 5 --max-steps 999 --max-runtime-minutes 60 --vessel-write-mode at-end
```

기존 방식:

```powershell
python main.py night-summarize-token-layer --llm-mode qwen --until-context-budget --max-steps 5 --write-vessel
```

## 5. Test Plan

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_173_night_checkpointed_long_runner.py -q
python main.py fast-test --profile graph
git diff --check
```
