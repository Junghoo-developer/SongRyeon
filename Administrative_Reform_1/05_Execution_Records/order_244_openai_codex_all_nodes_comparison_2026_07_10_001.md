# ORDER 244 실행 기록

- 날짜: 2026-07-10
- 결과: 구현/로컬 회귀 통과, 실제 모델 응답은 API quota 대기
- 발주서: `ORDER_244_OPENAI_CODEX_ALL_NODES_COMPARISON_V0.md`

## 구현

- `OpenAIResponsesAdapter`를 공통 `LLMAdapter` 경계에 추가했다.
- Responses API에 `store=false`, JSON object mode, 명시적 reasoning effort와
  max output token 상한을 전달한다.
- `openai-ping`, `openai-turn`, `openai-chat` 명령을 Qwen 명령과 분리했다.
- `openai-turn`은 node_1, memory selector, L1/L2/L3, node_2/3/4와 선택된
  Vessel R adapter 자리에 동일한 OpenAI adapter를 주입한다.
- API 키는 설정 여부만 기록하며 문자열은 trace/data/runtime에 넣지 않는다.
- API attempted/completed call과 input/output/total token 합계는 adapter의
  절대정보로 분리 집계한다.
- structure failure 화면이 마지막 OpenAI API failure type/reason과
  attempted/completed count를 직접 표시한다.

## 자동 검증

- `python -m compileall songryeon_core main.py`: 통과
- ORDER 244 pytest: `7 passed`
- 전체 pytest: `401 passed, 5 deselected`
- `python main.py quick-smoke`: `QUICK_SMOKE_OK`
- `python main.py smoke-test`: `SMOKE_TEST_OK`
- 관련 파일 `git diff --check`: 통과

## 실제 OpenAI ping

- key configured: `true`
- model: `gpt-5.3-codex`
- transport: `openai_responses_api`
- reasoning effort: `low`
- max output tokens: `512`
- 1차 응답: JSON mode input 표지 누락으로 HTTP 400
- 구조 수정 후 응답: HTTP 429 `insufficient_quota`

두 번째 결과는 API 키가 설정되고 OpenAI 서버/모델 요청 경로에 도달했음을
보이지만, 모델 추론 성공을 뜻하지 않는다. billing/quota가 열린 뒤 ping 성공을
먼저 확인하고 짧은 all-node 턴을 한 번만 실행한다.

## 경계

- Qwen/Ollama 경로와 프롬프트/schema는 변경하지 않았다.
- 실패를 Qwen 또는 code 의미 fallback으로 대체하지 않았다.
- live 모델 답변이 없으므로 외부 Codex가 송련 성능을 개선했다고 평가하지 않았다.
