# ORDER 247 실행 기록

- 날짜: 2026-07-10
- 결과: Qwen3 14B + Codex 5.6-sol 혼합 턴 성공
- 발주서: `ORDER_247_QWEN_CODEX_HYBRID_JUDGEMENT_RUNTIME_V0.md`

## 구현

- `hybrid-turn`, `hybrid-chat` 명령을 추가했다.
- Qwen은 node_1, memory selector, L1, L tool scope, L2, Vessel R를 맡는다.
- Codex는 L3, node_2, node_3, node_4를 맡는다.
- Codex 실패 시 Qwen이 그 의미 판단을 대신하는 fallback은 추가하지 않았다.
- runtime에 worker/judgement model, node allocation policy, Codex turn/token을 표시한다.
- L2 renderer는 혼합 runtime 이름이 아니라 실제 L2 `llm_call.model_id`를 표시한다.

## Codex 5.6-sol CLI 호환성

Python `openai-codex==0.1.0b3`에 함께 설치된 CLI `0.137.0a4`는
`gpt-5.6-sol` 호출을 거부했다. 이 실패에서는 token 0개가 기록됐다.

저장소의 gitignored cache에 `@openai/codex@0.144.1`을 설치하고,
`CodexConfig.codex_bin`으로 그 실행 파일을 명시적으로 선택했다.

재시험 결과:

- status: ok
- auth type: chatgpt
- plan type: pro
- model: gpt-5.6-sol
- tool activity: 0
- total tokens: 9,576
- codex bin source: workspace_cache

## 실제 혼합 턴

입력:

`안녕. 지금 송련이 어떤 방식으로 답하는지 한 문장으로 말해줘`

결과:

- status: ok
- Qwen model: qwen3:14b
- Codex model: gpt-5.6-sol
- route sequence: L -> L request blocked -> 2
- Codex turns: 5 / 5 / 5
- Codex total tokens: 128,572
- Codex tool activity: 0
- node_4: pass
- 실행 시간: 약 120.6초

ORDER 246의 all-node Codex 단일 실행 206,074 token과 비교하면 이번 한 사례에서는
77,502 token, 약 37.6% 감소했다. 입력과 검색 결과가 완전히 같은 통제 실험은 아니므로
일반적인 절감률로 단정하지 않는다.

## 검증

- `python -m compileall songryeon_core main.py`: 통과
- ORDER 245~247 좁은 pytest: 8 passed
- renderer 보강 후 ORDER 246~247 pytest: 5 passed
- 전체 pytest: 409 passed, 5 deselected
- `python main.py quick-smoke`: QUICK_SMOKE_OK
- `python main.py smoke-test`: SMOKE_TEST_OK

## 남은 위험

- Codex 판단 노드가 5회 호출되어 여전히 ChatGPT 구독 사용량이 크다.
- 짧은 인사성 질문도 Qwen node_1이 L로 보냈고, L 반환 뒤에도 L을 다시 요청했다.
  혼합 모델 배선과 별개로 node_1 라우팅 품질 감사가 필요하다.
- 최신 CLI는 현재 `.songryeon_core_cache`에 있어 git에 포함되지 않는다. 다른 PC에서는
  최신 CLI를 설치하거나 `SONGRYEON_CODEX_BIN`으로 실행 파일을 지정해야 한다.
- 현 혼합 배치는 고정 정책 v0이다. 사용자가 승인하지 않은 자동 비용 최적화나
  노드별 동적 모델 선택은 열지 않았다.
