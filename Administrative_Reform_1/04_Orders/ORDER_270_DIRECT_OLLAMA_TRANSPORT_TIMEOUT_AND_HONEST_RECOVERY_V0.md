# ORDER 270: Direct Ollama Transport Timeout And Honest Recovery v0

## 1. 배경

ORDER 269 live 진단에서 강제 L 경로의 `L1` Qwen 호출이 150초 이상 반환하지 않았다.
코드 감사 결과 `QwenLocalHTTPAdapter.timeout_seconds`는 OpenAI-compatible HTTP 경로의
`urlopen`에는 전달되지만, endpoint가 없을 때 쓰는 module-level `ollama.chat(...)`에는
전달되지 않았다. 따라서 `--timeout 180`은 direct Ollama transport에서 실제 강제 장치가
아니었다.

## 2. 목표

direct Ollama 호출을 timeout이 설정된 Ollama Python `Client` 경로로 바꾸고, transport
timeout을 LLM 성공으로 위장하지 않은 채 기존 `llm_call` 실패 장부와 명시적 code
fallback 경계로 연결한다.

## 3. 구현 범위

### 3.1 direct Ollama transport timeout

- 설치된 Ollama Python 패키지의 `ollama.Client(timeout=N)`을 사용한다.
- 이 Client가 내부 `httpx.Client(timeout=N)`에 값을 전달하는 로컬 설치 소스를 확인했다.
- 기존 model, messages, JSON format, temperature, `num_ctx` 요청은 유지한다.
- transport timeout은 `TimeoutError`로 정규화해 configured timeout과 transport를
  오류 메시지에 드러낸다.

### 3.2 정직한 복구

- `LLMNodeExecutor`는 timeout을 기존 `adapter_failed`로 기록한다.
- parse/schema 성공으로 바꾸지 않는다.
- L1 timeout 뒤에는 기존 `RULE_STUB`, `llm_goal_judgement_status=not_run`만 허용한다.
- L1 `llm_call` 실패 record는 terminal fallback diagnostics에 표시한다.
- code가 L1 의미 목표를 새로 판단했다고 표시하지 않는다.

### 3.3 runtime timeout 상태

runtime은 다음을 구분한다.

- direct Ollama: `enforced_by_ollama_httpx_client`
- compatible HTTP: `enforced_by_urlopen`
- OpenAI Responses API: `enforced_by_openai_client`
- fake/off: `not_applicable`

설정 timeout과 transport 강제 상태는 절대정보로 표시한다.

## 4. 한계

Ollama Client timeout은 HTTP transport 수준의 제한이다. Ollama server 내부 생성 작업이
즉시 취소되는지까지 이번 코드가 보증하지 않는다. 또한 호출 하나의 상한을 강제할 뿐,
여러 노드의 순차 호출 총시간 상한은 별도 정책이다.

## 5. 금지

- timeout 기본값 180초 변경
- 전체 턴 global timeout 추가
- LLM 호출 수, retry, L revision, same-turn L/R 횟수 변경
- timeout 시 의미 기반 code 답변 생성
- timeout을 parse/schema 성공으로 변환
- 외부 API, Neo4j, 심야정부 변경

## 6. 완료 조건

1. direct Ollama Client 생성 시 configured timeout이 전달된다.
2. 기존 `num_ctx`와 JSON format 요청이 유지된다.
3. transport timeout이 `adapter_failed`와 명시 오류 메시지로 기록된다.
4. L1 timeout 뒤 L1 frame은 `RULE_STUB / semantic=not_run`이다.
5. terminal이 L1 실패와 runtime timeout 강제 상태를 표시한다.
6. 표적 pytest, 전체 pytest, smoke-test, competition-demo를 통과한다.
7. 짧은 live Qwen 시험에서 configured timeout 안팎으로 완료 또는 실패가 반환된다.

## 7. 후속 경계

ORDER 270 뒤 호출별 시간표를 보고 전체 턴 wall-clock budget이 필요한지 별도 결재한다.
노드 생략이나 예산 감소는 이번 발주에 포함하지 않는다.
