# ORDER 098: Run-Aware Terminal/Final Renderer v0

## 상태

구현 완료.

단, 2026-06-25 기준 완료 범위는 다음처럼 읽는다.

- 완료: runtime count 기준 분리, 최신 L run 우선 terminal/final 표시, L internal continuation과 top-level same-turn reroute 표시 분리, node_3 grounding count block의 code 고정 생성.
- prompt/brief 경계까지 완료: node_3 최종 보고자가 내부 노드명을 자기정체성으로 쓰지 말라는 지시.
- 후속 과제: node_4가 user-facing identity leak을 code guard로 직접 반려하는 구조는 아직 별도 발주가 필요하다.
- 후속 과제: node_1 LLM router 실패 뒤 code fallback이 쓰인 사건을 routing frame에 더 선명히 남기는 작업은 ORDER_099에서 다룬다.
- 후속 과제: node_4 remand의 return target 구조화와 자동 재작성 루프는 아직 열지 않는다.

따라서 이 문서의 "구현 완료"는 화면 정직성, count 정합성, run-aware renderer 기준의 완료다.
identity leak의 node_4 강제 반려까지 완료됐다는 뜻이 아니다.

기준 실행 기록:

- `Administrative_Reform_1/05_Execution_Records/order_098_run_aware_terminal_final_renderer_2026_06_25_001.md`
- `Administrative_Reform_1/05_Execution_Records/runtime_count_run_aware_renderer_2026_06_25_001.md`
- `Administrative_Reform_1/05_Execution_Records/node3_code_grounding_block_2026_06_25_001.md`
- `Administrative_Reform_1/05_Execution_Records/order_098_status_baseline_2026_06_25_001.md`

이 문서는 qwen-turn 실험에서 확인된 runtime 표시 혼동을 고치기 위한 작은 MVP 발주서다.

이번 발주서는 그래프를 확장하지 않는다.
목표는 L루프와 route=2 downstream이 이미 기록한 사실을 terminal/final renderer가 정직하게 보여주도록 만드는 것이다.

## 배경

다음 입력으로 qwen-turn 테스트를 실행했다.

```text
최대한 많은 내부 문서를 아무거나 골라서 읽고 이를 총합해서 지금 너가 무엇인지 스스로 추측해봐
```

관찰 결과는 전반적으로 좋았다.

- L1은 `exploratory_multi_doc` 성격의 목표를 잡았다.
- L1은 최소 3개 문서 읽기를 요구했다.
- 실제 보고 가능한 문서는 2개였다.
- L3는 목표 달성을 `partial`로 판단했다.
- node_3 최종 답변도 읽은 문서 2개와 한계를 명시했다.

하지만 runtime 출력에는 사람이 오해할 수 있는 표시가 있었다.

## 문제 1: read_doc 수량 불일치

같은 턴에서 다음 표시가 서로 달랐다.

```text
L 도구 예산: read_doc=2/3
node_3 input brief: documents=2
route=2 handoff: read_doc=3
```

핵심 질문:

```text
2개 읽었는데 왜 어떤 화면은 3개라고 말하는가?
```

감사 후보:

- `node_3 input brief`는 본문 텍스트가 있는 문서만 보고 가능한 문서로 세는지 확인한다.
- `route=2 handoff`는 `tool_result:read_doc` / `tool_result:read_artifact` 계열 record를 더 넓게 세는지 확인한다.
- 실패했거나 빈 `read_artifact` 기록이 `read_doc=3`으로 섞여 들어가는지 확인한다.
- 같은 DataStore 안에서 최종 L run이 아닌 과거/중간 extract record까지 같이 세는지 확인한다.

원칙:

```text
보고 가능한 문서 수와 원시 읽기/추출 시도 수를 같은 read_doc 숫자로 보여주지 않는다.
```

권장 표시:

```text
reportable_documents=2
raw_document_extract_records=3
```

또는 같은 의미를 사용자에게 더 쉬운 한국어로 표시한다.

```text
보고 가능 문서: 2
읽기/추출 시도 기록: 3
```

## 문제 2: L 내부 revision과 top-level L reroute 표시 혼동

관찰 결과:

```text
L loop run namespace: run=1
same-turn reroute controller: policy disabled, close_route_2
route=2 handoff path: L:L1_L2_tools_L3 가 두 번 표시됨
```

핵심 질문:

```text
L을 다시 돈 게 아닌데 왜 path는 L을 두 번 돈 것처럼 보이는가?
```

감사 후보:

- `route_path`가 `route=L` 요청 기록을 실제 L 실행처럼 `L:L1_L2_tools_L3`로 펼쳐 보여주는지 확인한다.
- node_1이 L 복귀 뒤 다시 `route=L`을 요청했지만 controller가 policy disabled로 닫은 경우를 실제 L 실행과 구분하는지 확인한다.
- L 내부 continuation/revision frame과 top-level same-turn L reroute controller frame이 terminal 출력에서 서로 다른 이름으로 보이는지 확인한다.

원칙:

```text
실제 실행된 L run
차단된 top-level L reroute 요청
L 내부 continuation/revision
```

위 세 가지를 한 줄 path 안에서 섞지 않는다.

권장 표시:

```text
actual_l_runs=1
top_level_l_reroute_request=blocked_by_policy
l_internal_revision=present 또는 none
```

route path가 필요하면 실제 실행과 요청/차단을 분리한다.

예:

```text
실제 실행 경로: 0 -> 1 -> 0 -> L(run=1) -> 0 -> 1 -> 2 -> 3 -> 4
차단된 추가 요청: node_1 route=L, controller=close_route_2, reason=policy_disabled
```

## 문제 3: node_3 최종 답변의 자기정의 표현

관찰 결과:

```text
저는 node2의 역할을 수행...
```

같은 표현은 위험하다.

node_3 최종 답변자는 사용자에게 보고하는 송련의 최종 응답자 관점으로 말해야 한다.
특정 내부 노드 하나를 자기정체성처럼 말하면 안 된다.

핵심 질문:

```text
최종 보고자는 자신을 어느 노드로 말해야 하는가?
```

원칙:

```text
최종 보고자는 node_0/node_1/node_2/node_3 그 자체가 아니다.
최종 보고자는 사용자에게 보고하는 송련의 최종 응답자 관점으로 말한다.
내부 노드명은 필요할 때 실행 경로 설명에만 제한적으로 쓴다.
```

권장 보강:

- `node_3_reporter.py` prompt를 점검한다.
- `node_3_input_brief`의 `reporting_rules`에 한국어 경계 문장을 추가한다.
- node_3 LLM payload에 내부 실행 순서가 포함되더라도, 그 내부 node label을 자기정체성으로 쓰지 말라고 명시한다.

예:

```text
너는 특정 내부 노드 그 자체가 아니라, 사용자에게 보고하는 송련의 최종 응답자 관점으로 말한다.
node_0/node_1/node_2/node_3 같은 내부 역할명은 자기정체성으로 쓰지 않는다.
```

## 구현 대상 감사 파일

우선 다음 파일을 감사한다.

```text
songryeon_core/runtime/terminal_view.py
songryeon_core/nodes/node_2_handoff.py
songryeon_core/nodes/node_3_input_brief.py
songryeon_core/nodes/node_3_reporter.py
songryeon_core/runtime/smoke_test.py
```

필요하면 다음 파일도 확인한다.

```text
songryeon_core/runtime/dry_run.py
songryeon_core/runtime/same_turn_l_reroute.py
songryeon_core/loops/l_loop.py
songryeon_core/loops/l_loop_revision_tool_attempt.py
songryeon_core/nodes/node_0_memory_supplier.py
```

## 구현 범위

### 1. run-aware terminal renderer

`terminal_view.py`가 legacy ID만 먼저 고르는지 확인하고, L run이 여러 개 있으면 최종 run의 다음 자료를 우선 표시하게 한다.

```text
L1 goal frame
L2 query frame / query plan
tool result / distillation
L3 achievement frame
turn outcome
node_2 handoff
node_3 input brief
node_3 report
node_4 gatekeeper
```

단, 사용자-facing 최종 답변에는 raw internal ID를 노출하지 않는다.

### 2. run-aware fallback final renderer

LLM report가 없어서 fallback final answer를 만들 때도 최신 L run의 evidence/reportable documents를 우선 사용한다.

legacy ID fallback은 유지하되, run-scoped record가 있으면 run-scoped record를 먼저 사용한다.

### 3. runtime count consistency

`route=2 handoff`와 `node_3 input brief`가 서로 다른 기준의 수량을 같은 이름으로 표시하지 않게 한다.

필요하면 frame payload에 다음처럼 분리된 count를 둔다.

```text
reportable_document_count
raw_document_extract_record_count
empty_document_extract_record_count
```

단, 이 count는 코드가 확인 가능한 절대정보로만 만든다.
문서 의미나 충분성 판단을 코드가 새로 하지 않는다.

### 4. route path 표시 정직성

`route=L` 요청이 controller에 의해 차단된 경우, 이를 실제 L 실행처럼 표시하지 않는다.

terminal view는 최소한 다음을 구분한다.

```text
actual_l_run_count
same_turn_l_reroute_controller_decision
same_turn_l_reroute_block_reason
l_internal_revision_state
```

### 5. node_3 identity boundary

node_3 최종 응답자가 자기 자신을 `node_2`, `node_3`, `내부 노드`라고 정의하지 않도록 prompt/brief 경계를 강화한다.

이 변경은 문체 덧칠이 아니라 메타정보 경계다.
내부 실행 정보는 실행 정보로만 쓰고, 최종 응답자의 자기정체성으로 쓰지 않는다.

## 금지

- W loop를 만들지 않는다.
- R loop를 만들지 않는다.
- 외부 DB를 만들지 않는다.
- scheduler나 장기기억 확장을 하지 않는다.
- same-turn L reroute 최대 실행 횟수를 늘리지 않는다.
- `max_l_runs_per_turn=2` 정책을 이번 발주서에서 바꾸지 않는다.
- `read_doc` 수량 불일치를 그럴듯한 문구로 숨기지 않는다.
- 실패/빈 문서 extract record를 성공 문서처럼 표시하지 않는다.
- 휴리스틱 문장 매칭으로 문제를 덮지 않는다.
- LLM 판단을 코드 사실처럼 표시하지 않는다.
- 코드가 의미 판단을 한 것처럼 위장하지 않는다.

## Smoke-test 요구

기존 smoke-test를 깨지 않아야 한다.

가능하면 다음 검사를 추가한다.

```text
1. policy-enabled same-turn L reroute에서 L 2회차가 실행되면 terminal/fallback renderer가 run=2 자료를 우선 표시한다.

2. policy-disabled 상태에서 node_1이 route=L을 다시 요청해도 controller가 close_route_2 하면 terminal path가 실제 L 2회차 실행처럼 보이지 않는다.

3. 보고 가능한 문서 2개와 빈/실패 extract record 1개가 섞인 fixture에서 route=2 handoff와 node_3 brief가 서로 다른 숫자를 같은 read_doc 이름으로 말하지 않는다.

4. node_3 final answer 또는 fallback final answer에 raw internal ID가 노출되지 않는다.

5. node_3 final answer가 자기 자신을 node_0/node_1/node_2/node_3 같은 내부 노드로 정의하지 않는다.
```

## 완료 조건

다음 명령이 통과해야 한다.

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
```

완료 보고에는 다음을 적는다.

- read_doc 수량 불일치의 실제 원인.
- route=2 handoff에서 `read_doc=3`이 나온 정확한 집계 기준.
- `documents=2`와 `read_doc=3`이 계속 병존한다면 각각의 의미.
- 실제 L run count와 blocked top-level reroute request가 terminal view에서 어떻게 구분되는지.
- L 내부 continuation/revision과 top-level same-turn reroute가 어떻게 구분되는지.
- terminal/fallback final renderer가 최신 L run을 우선 표시하는지 여부.
- node_3 최종 보고자가 내부 노드명으로 자신을 정의하지 않도록 어떤 경계를 추가했는지.
- compileall / smoke-test 결과.

## 새 채팅 전달용 요약

다음 채팅에 이 발주서를 던질 때는 이렇게 말하면 된다.

```text
ORDER_098_RUN_AWARE_TERMINAL_FINAL_RENDERER_V0를 구현하라.

목표는 그래프 확장이 아니라 runtime 표시 정직성이다.

우선 read_doc count mismatch 원인을 감사하라.
2개 보고 가능 문서와 3개 extract record가 섞여 있다면 같은 read_doc 숫자로 표시하지 말고 분리하라.

그 다음 route path에서 실제 L run과 blocked same-turn L reroute request를 구분하라.
policy disabled로 controller가 close_route_2 한 요청을 실제 L 2회차처럼 표시하지 마라.

마지막으로 terminal_view/fallback final renderer가 최신 L run 자료를 우선 보게 하라.
node_3 최종 응답자는 node_2/node_3 같은 내부 노드가 아니라 송련의 최종 보고자 관점으로 말해야 한다.

W loop, R loop, 외부 DB, scheduler, 장기기억 확장, max_l_runs_per_turn 증가 금지.

구현 후:
python -m compileall songryeon_core main.py
python main.py smoke-test
```
