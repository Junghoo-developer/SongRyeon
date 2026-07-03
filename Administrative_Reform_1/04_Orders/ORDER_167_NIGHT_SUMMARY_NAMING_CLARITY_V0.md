# ORDER 167: Night Summary Naming Clarity v0

## 1. Goal

ORDER 166에서 추가한 심야정부 TimeBundle summary worker의 이름을 더 사람이 이해하기 쉬운 표준 이름으로 정리한다.

현재 이름:

```text
night_time_bundle_summary_worker
run_night_time_bundle_summary_worker
night_time_bundle_summary_worker_v0.md
```

새 표준 이름:

```text
night_summarize_time_bundle
run_night_summarize_time_bundle
night_summarize_time_bundle_v0.md
```

## 2. Naming Rule

앞으로 심야정부 작업자는 다음 패턴을 우선한다.

```text
night_<verb>_<target>
```

예:

- `night_summarize_time_bundle`
- `night_summarize_source_kind_bundle`
- `night_review_summary_node`

이름 안에서 `worker`는 내부 구현 설명으로만 쓰고, 사용자-facing / 호출-facing 이름에서는 줄인다.

## 3. Scope

- 새 표준 함수 `run_night_summarize_time_bundle()`을 추가한다.
- 기존 `run_night_time_bundle_summary_worker()`는 compatibility alias로 유지한다.
- 새 prompt ref `songryeon_core/prompts/night_summarize_time_bundle_v0.md`를 사용한다.
- node id와 data type도 새 이름을 기준으로 기록한다.
- 기존 schema명 `NightTimeBundleSummaryFrame`은 유지한다.

## 4. Non-goals

- summary schema 구조 변경 없음.
- LLM summary 정책 변경 없음.
- R loop 자동 사용 없음.
- Neo4j/Vessel write 정책 변경 없음.
- source kind bundle summary worker 구현 없음.

## 5. Test Plan

```powershell
python -m compileall songryeon_core main.py
python -m pytest tests/test_order_166_night_time_bundle_summary_node.py -q
python main.py fast-test --profile graph
git diff --check
```
