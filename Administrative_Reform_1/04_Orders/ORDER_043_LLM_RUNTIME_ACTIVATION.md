# ORDER 043: LLM Runtime Activation

**상태**: 정식 발주서  
**승격일**: 2026-06-21  
**출처**: 사용자 요청 "아 몰랑 아무튼 llm 넣고"  
**목표**: 이미 있는 LLM adapter 뼈대를 실제 런타임 선택지로 올리고, Qwen 로컬 호출을 안전하게 켜고 끌 수 있게 한다.

## 배경

현재 `songryeon_core/llm/`에는 `LLMAdapter`, `FakeLLMAdapter`, `QwenLocalHTTPAdapter`, `LLMNodeExecutor`가 있다.  
초기에는 Qwen이 endpoint가 있을 때만 ping 가능한 spike 상태였지만, 이후 원본 `SongRyeon_Project` 방식에 맞춰 Ollama 직접 호출도 지원하도록 바뀌었다.

## 범위

1. LLM runtime 설정 객체를 만든다.
2. `fake`, `qwen`, `off` 모드를 명시적으로 선택한다.
3. `QWEN_LOCAL_ENDPOINT`, model id, timeout을 설정에서 읽는다.
   - endpoint가 있으면 OpenAI-compatible HTTP 호출을 사용한다.
   - endpoint가 없으면 기본적으로 Ollama의 `qwen3:14b`를 직접 호출한다.
4. `main.py qwen-ping` 또는 동등한 CLI 명령으로 연결 상태를 확인한다.
5. Qwen 연결 실패 시 구조 실행 전체가 죽지 않고 실패 신호나 fallback 결과를 남긴다.

## 원칙

1. LLM은 구조를 대체하지 않는다. 스키마와 trace/data 계약 안에서만 호출된다.
2. Qwen이 꺼져 있어도 기존 dry run과 smoke test는 계속 돌아야 한다.
3. LLM 호출 가능 여부는 절대정보로 기록한다. 예: endpoint 존재 여부, model id, 실패 메시지.

## 완료 기준

1. `python main.py qwen-ping`이 Ollama 성공, HTTP endpoint 성공, adapter 실패를 명시적으로 보고한다.
2. `python dry_run.py`는 LLM 모드와 무관하게 통과한다.
3. `python main.py smoke-test`가 통과한다.
4. Qwen endpoint가 없을 때도 Ollama transport로 호출되거나, Ollama 자체 문제를 구조화된 실패로 보고한다.
