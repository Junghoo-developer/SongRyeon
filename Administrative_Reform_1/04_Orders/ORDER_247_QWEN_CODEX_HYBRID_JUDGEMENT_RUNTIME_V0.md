# ORDER 247: Qwen + Codex Hybrid Judgement Runtime v0

## 1. 목표

로컬 `qwen3:14b`가 반복 작업과 탐색을 담당하고, ChatGPT 구독으로 인증된
Codex가 의미 판단·정리·최종 검사를 담당하는 명시적 혼합 실행 옵션을 만든다.

이번 발주는 모든 노드에 Codex를 넣어 큰 사용량을 소비한 ORDER 246 비교 실험을
일상 실행 구조로 바꾸지 않는다. 큰 모델은 중요한 경계에만 배치한다.

## 2. 고정 노드 배치

### Qwen3 14B 담당

- node_1 router
- recent memory relevance selector
- L1 goal setter
- L tool scope selector
- L2 query planner와 revision planner
- 선택적으로 실행되는 Vessel R 탐색

### Codex 담당

- L3 result keeper
- node_2 metainfo boundary와 answer-basis 판단
- node_3 final reporter
- node_4 gatekeeper

### code 담당

- trace, count, ID, schema, budget, packet assembly
- 실행 성공·실패와 모델별 배치 표시

## 3. 모델과 인증

- Qwen 기본 모델: `qwen3:14b`
- Codex 기본 모델: `gpt-5.6-sol`
- Codex 인증: ChatGPT 구독 인증만 허용
- API key fallback: 금지
- Codex tool 사용: 금지
- Codex sandbox: read-only
- Codex CLI가 모델을 지원하지 않으면 조용히 다른 모델로 바꾸지 않고 실패한다.

## 4. CLI

- `hybrid-turn`: 혼합 모델로 한 턴 실행
- `hybrid-chat`: 혼합 모델로 연속 대화

runtime 출력에는 다음 절대정보를 표시한다.

- worker model
- judgement model
- node allocation policy
- Codex turn 수와 token 사용량
- Codex CLI 선택 여부와 실패 원인

## 5. 실패 정책

- Qwen 또는 Codex가 실패하면 다른 모델이 의미 판단을 대신하지 않는다.
- 기존 strict router, schema validator, node_4 guard를 약화하지 않는다.
- 혼합 실행은 기존 `qwen-turn`과 `codex-sdk-turn`의 기본 동작을 바꾸지 않는다.

## 6. 완료 조건

1. `gpt-5.6-sol`을 지원하는 최신 로컬 Codex CLI를 명시적으로 선택할 수 있다.
2. 혼합 런타임이 고정 노드 배치를 사용한다.
3. runtime에서 두 모델과 Codex 사용량을 구분해 볼 수 있다.
4. 좁은 pytest와 compileall이 통과한다.
5. 가능하면 짧은 실제 혼합 턴을 실행해 Qwen/Codex 양쪽 호출을 확인한다.

## 7. 금지

- 의미 기반 code fallback 추가 금지
- API 과금 경로 자동 전환 금지
- L/R 그래프 의미 변경 금지
- same-turn L reroute 횟수 변경 금지
- 기존 dirty 작업 되돌리기 금지
