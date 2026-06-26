# ORDER 062: Knowledge Graph Candidate Schema

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: trace, data, 문서, 근거 사이의 관계를 나중에 그래프화하기 위한 준비  
**목표**: 실제 그래프 DB를 붙이기 전에, 지식 그래프 후보 node/edge를 스키마로 보존한다.

## 배경

프로젝트는 이미 trace ID, data ID, tool result, LLM call, routing reason을 저장한다.  
이 정보들은 서로 관계를 가진다. 예를 들어 어떤 L2 검색어 후보는 어떤 0 보고에서 파생되었고, 어떤 L3 판단은 어떤 tool result를 근거로 삼는다.

## 범위

1. `GraphNodeCandidate`와 `GraphEdgeCandidate` 또는 동등한 구조를 만든다.
2. node 후보 종류는 `turn`, `trace`, `data`, `document`, `chunk`, `schema`, `tool`, `llm_call`, `reason`을 우선 지원한다.
3. edge 후보 종류는 `produced_by`, `source_of`, `derived_from`, `cites`, `selected_tool`, `queried`, `returned`를 우선 지원한다.
4. 후보 graph payload는 실제 DB 없이 JSON으로 export 가능해야 한다.
5. 각 edge는 source ID와 target ID를 반드시 가진다.

## 원칙

1. 그래프 후보는 최종 지식이 아니라 관계 후보이다.
2. LLM이 만든 관계는 근거 ID 없이 확정하면 안 된다.
3. 처음에는 자동 생성 가능한 관계부터 만든다.

## 완료 기준

1. 한 dry-run에서 graph candidate payload가 생성된다.
2. L2 query, tool result, L3 achievement 사이의 edge가 남는다.
3. graph candidate JSON을 replay에서 다시 읽을 수 있다.
4. `python main.py smoke-test`가 통과한다.
