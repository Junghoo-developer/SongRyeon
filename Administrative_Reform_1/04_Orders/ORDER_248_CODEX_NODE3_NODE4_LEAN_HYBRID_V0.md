# ORDER 248: Codex Node 3/4 Lean Hybrid v0

## 1. 목표

ORDER 247 혼합 실행에서 Codex가 L3, node_2, node_3, node_4를 맡아 한 턴에
5회 호출되고 128,572 token을 사용한 문제를 줄인다.

Codex 5.6-sol은 사용자에게 직접 닿는 최종 보고와 최종 검사에만 배치한다.

## 2. 고정 배치

### Qwen3 14B

- node_1 router
- recent memory relevance selector
- L1 goal setter
- L tool scope selector
- L2 query/revision planner
- L3 result keeper
- node_2 metainfo boundary와 answer-basis selector
- Vessel R

### Codex 5.6-sol

- node_3 final reporter
- node_4 gatekeeper

### Code

- trace, count, ID, schema, budget, packet assembly

## 3. 원칙

- Qwen 실패를 Codex가 몰래 대신하지 않는다.
- Codex 실패를 Qwen이나 code가 몰래 대신하지 않는다.
- node_4 guard를 약화하지 않는다.
- 기존 `codex-sdk-turn` all-node 비교 경로는 유지한다.
- ORDER 247 실행 기록은 과거 비교 기준선으로 보존한다.

## 4. 완료 조건

1. hybrid runtime의 Codex node 목록이 node_3, node_4 두 개뿐이다.
2. L3와 node_2의 실제 `llm_call.model_id`가 Qwen으로 기록된다.
3. node_3와 node_4의 실제 `llm_call.model_id`가 Codex로 기록된다.
4. 실제 혼합 턴의 Codex attempted turn 수가 2회다.
5. compileall, pytest, smoke-test가 통과한다.

## 5. 금지

- 동적 의미 휴리스틱 라우팅 추가 금지
- L/R 구조 변경 금지
- API key 과금 경로 자동 전환 금지
- same-turn L reroute 횟수 변경 금지
