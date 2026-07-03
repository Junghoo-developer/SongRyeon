# ORDER 170: Night Changed Source One-At-A-Time Runner v0

## 1. Goal

`night-summarize-changed-sources`가 변경된 코드/문서 leaf를 한 번에 전부 요약하지 않고, 명시 옵션을 켰을 때 한 실행에 source leaf 하나만 요약하게 만든다.

목표는 긴 심야정부 실행을 다음처럼 바꾸는 것이다.

```text
첫 실행:
source manifest ingest
-> SourceObservationLedgerFrame
-> changed source leaf queue 고정
-> queue 첫 leaf 1개 요약
-> 저장

다음 실행:
기존 queue 읽기
-> 아직 처리 안 된 다음 leaf 1개 요약
-> 저장
```

## 2. Why

ORDER_169는 사람이 한 번에 심야 source 요약을 돌릴 수 있게 만들었지만, 변경 leaf가 수백 개이면 Qwen 호출이 길게 이어지고 중간 중단/재개/진척 확인이 어렵다.

이번 발주는 성능 최적화가 아니라 실행 안정성 MVP다. 한 번에 하나씩 처리하면 사용자는 중간에 멈추거나 다시 실행해도 어디까지 진행됐는지 확인할 수 있다.

## 3. Required Behavior

- 기본 `night-summarize-changed-sources` 동작은 유지한다.
- 새 옵션 `--one-at-a-time`을 켰을 때만 한 실행에 source leaf 1개만 요약한다.
- one-at-a-time 최초 실행은 `SourceObservationLedgerFrame`에서 `new_source_version` / `content_changed` leaf 목록을 절대정보 queue로 고정한다.
- 이후 실행은 새 관측으로 남은 대상을 잃지 않고 기존 queue를 읽어 다음 미처리 leaf를 고른다.
- 처리 완료 여부는 code가 기존 summary node/frame 존재 여부로 계산한다.
- LLM은 여전히 leaf 원문 하나의 요약문만 쓴다.
- code는 요약 의미를 쓰지 않는다.
- queue/progress 값은 `generated_by=CODE:*`, `info_class=absolute`, `semantic_judgement_status=not_run`으로 둔다.
- optional Neo4j write는 기존처럼 명시 `--write-vessel`이 있을 때만 실행한다.

## 4. Non-goals

- R loop를 열지 않는다.
- semantic axis를 만들지 않는다.
- source kind bundle / time bundle 상위 요약은 만들지 않는다.
- 실패 leaf 자동 재시도 정책을 만들지 않는다.
- 이전 summary를 삭제하거나 덮어쓰지 않는다.
- DataStore record를 in-place update하지 않는다.

## 5. Command

```powershell
python main.py night-summarize-changed-sources --root . --llm-mode qwen --one-at-a-time
```

Neo4j까지 매 step 반영:

```powershell
python main.py night-summarize-changed-sources --root . --llm-mode qwen --one-at-a-time --write-vessel
```

새 queue를 강제로 시작해야 하면 새 `--batch-id`를 명시한다.

```powershell
python main.py night-summarize-changed-sources --root . --llm-mode qwen --one-at-a-time --batch-id night_sources_2026_07_02_manual_002
```

## 6. Test Plan

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_170_night_changed_source_one_at_a_time.py -q
python -m pytest tests/test_order_169_night_changed_source_summary_cli.py -q
git diff --check
```
