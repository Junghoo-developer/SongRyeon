# Runtime Count + Run-Aware Renderer - 2026-06-25-001

## Source Order

- `Administrative_Reform_1/04_Orders/ORDER_098_RUN_AWARE_TERMINAL_FINAL_RENDERER_V0.md`

## 구현 범위

`route=2 handoff`의 문서 수 집계 기준을 분리했다.

기존 `read_doc_count`는 호환 필드로 유지하되, 의미를 `reportable_document_count`와 맞췄다.

새로 남기는 절대 count:

```text
reportable_document_count
raw_document_extract_record_count
empty_document_extract_record_count
```

이제 빈 `read_artifact` 또는 실패성 extract record가 실제 보고 가능한 문서 수처럼 보이지 않는다.

## L 실행/요청 표시

`route_path`가 `route=L` 요청을 무조건 실제 L 실행처럼 펼치던 표시를 줄였다.

이제 handoff는 다음을 따로 기록한다.

```text
actual_l_run_count
blocked_same_turn_l_reroute_request_count
same_turn_l_reroute_controller_decisions
l_internal_revision_count
```

policy disabled 상태에서 node_1이 다시 `route=L`을 요청하면 terminal view는 실제 L 2회차로 표시하지 않고 다음처럼 구분한다.

```text
actual_l_runs=1
blocked_top_level_l_requests=1
```

## Run-Aware Renderer

`terminal_view.py`와 fallback final renderer가 최신 L run의 run-scoped record를 우선 고르게 했다.

적용 대상:

- L1 goal
- L2 query / query plan
- search/read tool result
- L3 achievement
- route=2 handoff
- node_3 input brief
- node_3 report
- node_4 gatekeeper

legacy ID fallback은 유지한다.

## Node3 Identity Boundary

`node_3` reporting rules와 reporter prompt에 한국어/영어 경계를 보강했다.

핵심 원칙:

```text
최종 보고자는 특정 내부 노드 그 자체가 아니라, 사용자에게 보고하는 송련의 최종 응답자 관점으로 말한다.
node_0/node_1/node_2/node_3 같은 내부 역할명은 자기정체성으로 쓰지 않는다.
```

## Smoke Coverage

`python main.py smoke-test`가 추가로 확인한다.

- 보고 가능한 문서 2개와 빈 extract record 1개가 있을 때:
  - `reportable_document_count=2`
  - `raw_document_extract_record_count=3`
  - `empty_document_extract_record_count=1`
- `node_3 input brief`는 실제 보고 가능한 문서 2개만 노출한다.
- policy disabled same-turn L 요청은 L 2회차 실행으로 표시되지 않는다.
- policy enabled 2회차 실행에서는 terminal view가 `L:run:0002:*` 최신 run 자료를 표시한다.
- node_3 brief는 최종 응답자 관점과 내부 노드 자기정체성 금지를 reporting rule로 가진다.

## 범위 밖

이번 작업은 다음을 하지 않았다.

- W loop 추가
- R loop 추가
- 외부 DB 추가
- scheduler/장기기억 확장
- `max_l_runs_per_turn` 상한 증가
- LLM 의미 판단을 코드 사실처럼 표시하는 변경

## 검증

```powershell
python -m compileall songryeon_core main.py
```

결과: 통과.

```powershell
python main.py smoke-test
```

결과: 통과. `SMOKE_TEST_OK`.

추가 샘플 확인:

```text
policy disabled:
actual_l_runs=1
blocked_top_level_l_requests=1
path contains L:top_level_reroute_blocked_by_controller

policy enabled:
actual_l_runs=2
terminal view shows L:run:0002:L1:goal_frame
terminal view shows L:run:0002:L3:achievement_frame
```
