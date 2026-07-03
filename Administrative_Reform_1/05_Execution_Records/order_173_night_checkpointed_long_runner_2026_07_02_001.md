# ORDER 173 Execution Record: Night Checkpointed Long Runner v0

## 변경 요약

- `night-summarize-token-layer --until-context-budget` 자동 reducer에 checkpointed long-runner 옵션을 추가했다.
- 매 step 이후 `TraceStore` / `DataStore` 저장은 기존 구조를 유지하고, 추가로 progress JSONL을 남기게 했다.
- `--max-runtime-minutes`로 실행 시간 상한을 둘 수 있게 했다.
- `--vessel-write-mode none|every-step|at-end`를 추가했다.
- 기존 `--write-vessel`은 호환상 `every-step`으로 해석한다.
- 실패 bundle을 만나면 기본적으로 멈추는 `stop_on_failure=True` 정책을 추가했고, CLI에서는 `--no-stop-on-failure`로 끌 수 있게 했다.

## 주요 파일

- `songryeon_core/runtime/night_token_budget_layer_summary.py`
- `main.py`
- `songryeon_core/runtime/fast_test.py`
- `tests/test_order_173_night_checkpointed_long_runner.py`
- `Administrative_Reform_1/04_Orders/ORDER_173_NIGHT_CHECKPOINTED_LONG_RUNNER_V0.md`
- `Administrative_Reform_1/04_Orders/README.md`

## 구현 경계

- 새 요약 의미 판단은 추가하지 않았다.
- 정확 tokenizer는 만들지 않았다.
- semantic axis, R live route, failed bundle retry policy는 열지 않았다.
- 원본 graph node나 기존 summary node를 삭제/덮어쓰기 하지 않았다.

## 검증

```powershell
python -m compileall songryeon_core main.py
```

통과.

```powershell
python -m pytest tests/test_order_173_night_checkpointed_long_runner.py -q
```

`3 passed`.

```powershell
python -m pytest tests/test_order_172_night_token_layer_auto_reduce.py tests/test_order_173_night_checkpointed_long_runner.py -q
```

`6 passed`.

```powershell
git diff --check
```

통과.

```powershell
python main.py fast-test --profile graph
```

`FAST_TEST_OK`, graph profile `100 passed`.

```powershell
python main.py smoke-test
```

`SMOKE_TEST_OK`.

```powershell
python -m pytest -q
```

604초 제한에서 timeout. 이번 ORDER_173 단독 테스트, ORDER_172+173 결합 테스트, graph fast-test, smoke-test는 통과했지만 전체 pytest 장시간 실행은 별도 재확인 대상이다.
