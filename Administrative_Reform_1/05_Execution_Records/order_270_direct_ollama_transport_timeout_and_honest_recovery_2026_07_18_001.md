# ORDER 270 Direct Ollama Transport Timeout And Honest Recovery 실행 기록

## 1. 실행 일자

- 2026-07-18

## 2. 작업 배경

ORDER 269에서 direct Ollama의 L1 호출이 150초 이상 반환하지 않았고, CLI의 configured
timeout이 module-level `ollama.chat(...)`에는 전달되지 않는다는 사실을 확인했다.

로컬에 설치된 Ollama Python package 소스를 확인한 결과 `ollama.Client(timeout=N)`의
`timeout`은 내부 `httpx.Client(timeout=N)`으로 전달된다. 이번 작업은 이 공식 transport
경로를 사용해 호출별 timeout을 실제로 강제하고, 실패를 기존 장부와 fallback 경계에
정직하게 연결했다.

## 3. 구현 내용

### 3.1 direct Ollama Client

- module-level `ollama.chat(...)`을 `ollama.Client(timeout=N).chat(...)`으로 교체했다.
- model, messages, JSON format, temperature, `num_ctx` 계약은 유지했다.
- built-in `TimeoutError`와 Ollama가 사용하는 `httpx.TimeoutException` 계열만 기술적으로
  timeout으로 분류한다.
- timeout 오류는 `direct Ollama transport timed out after configured N seconds`로
  정규화한다.

### 3.2 실패와 복구

- `LLMNodeExecutor`는 정규화된 timeout을 `adapter_failed`로 기록한다.
- parse/schema 성공으로 바꾸지 않는다.
- L1 timeout 뒤 기존 fallback은 `goal_generation_source=RULE_STUB`,
  `llm_goal_judgement_status=not_run`으로만 생성된다.
- terminal의 L fallback diagnostics가 L1 실패도 표시하게 했다.
- Qwen strict node_1은 timeout 뒤 silent code routing fallback을 허용하지 않는다.

### 3.3 runtime 절대정보

runtime은 configured timeout과 강제 위치를 구분한다.

```text
direct Ollama = enforced_by_ollama_httpx_client
compatible HTTP = enforced_by_urlopen
OpenAI Responses API = enforced_by_openai_client
fake/off = not_applicable
```

## 4. 검증 결과

```text
python -m compileall songryeon_core main.py
-> passed

ORDER 270 + ORDER 261 표적 pytest
-> 13 passed

ORDER 251/261/267/268/269/270 관련 회귀
-> 31 passed, 1 skipped

python -m pytest
-> 496 passed, 1 skipped, 5 deselected in 142.09s

python main.py smoke-test
-> SMOKE_TEST_OK in 147.7s
-> trace_count=55, data_record_count=93

python main.py competition-demo
-> SONGRYEON_COMPETITION_DEMO_OK
-> LOCAL PASS / HONEST FALLBACK PASS / CODE GUARD PASS

git diff --check
-> passed
```

Windows symbolic-link 권한 때문에 ORDER 267의 해당 테스트 하나는 계속 skip됐다.

## 5. 실제 Qwen transport 시험

제품 기본 timeout 180초는 바꾸지 않고, 시험 명령에만 `--timeout 5`를 지정했다.
workspace 강제 L 질문을 direct Ollama와 `--live-trace`로 실행했다.

완료된 LLM 호출 시간은 다음과 같다.

```text
L1          5297ms -> adapter_failed -> RULE_STUB/not_run
L_tool_scope 5046ms -> adapter_failed -> explicit failed scope frame
L2          5047ms -> adapter_failed -> existing code fallback path
L3          5031ms -> adapter_failed -> existing code operation fallback
node_1      5032ms -> adapter_failed -> Qwen strict structure_failed
```

PowerShell job 전체는 26.5초에 종료됐다. ORDER 269에서는 같은 direct Ollama L1 호출이
150초 후에도 미완료였지만, 이번에는 각 호출이 configured 5초 안팎에서 반환됐다. 따라서
transport timeout 강제는 실제 로컬 Qwen 경로에서도 확인됐다.

턴의 최종 상태는 `structure_failed`였다. 원인은 post-L node_1 router가 timeout으로
`adapter_failed`가 됐고 Qwen strict 정책이 silent code fallback을 금지했기 때문이다.
이는 transport timeout 성공과 사용자 답변 성공을 분리해서 봐야 한다.

## 6. 한계

1. httpx transport timeout은 client 대기를 끊지만 Ollama server 내부 생성 작업이 즉시
   취소되는지까지 보증하지 않는다.
2. 호출 하나의 상한만 생겼다. 여러 노드 timeout의 합계를 제한하는 전체 턴 wall-clock
   budget은 없다.
3. timeout 뒤 L1/L2/L3의 기존 code fallback은 실행되지만, Qwen strict node_1 실패는
   정상 답변으로 위장하지 않고 턴을 닫는다.
4. 이번 live 5초 시험은 timeout 경계 검증이며 Qwen 답변 품질 시험이 아니다.

## 7. 일부러 하지 않은 것

- 기본 timeout 180초 변경
- 전체 턴 global timeout
- LLM 호출 수, retry, L revision, same-turn L/R 횟수 변경
- timeout 시 code 의미 답변 생성
- node_1 strict fallback 완화
- 외부 API, Neo4j, 심야정부 변경

## 8. 판정

ORDER 270의 direct Ollama transport timeout과 정직한 실패 복구 경계는 완료됐다. 다음
의사결정은 호출별 timeout 값을 낮추는 일이 아니라, 전체 턴 wall-clock budget과 어떤
노드까지 실행할지에 관한 별도 정책 설계다.
