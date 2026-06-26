# TMP ORDER 026: LLM Adapter Interface

## 목표

Qwen이든 다른 로컬 모델이든 같은 방식으로 호출할 수 있는 LLM 어댑터 인터페이스를 만든다.

## 배경

현재 노드는 전부 규칙 기반이다.  
LLM을 직접 노드에 박으면 나중에 교체와 테스트가 어려워진다.

## 범위

1. `songryeon_core/llm/` 패키지를 만든다.
2. `LLMRequest`, `LLMResponse`, `LLMAdapter` 인터페이스를 만든다.
3. `FakeLLMAdapter`를 만들어 테스트용 응답을 돌려준다.
4. 실제 Qwen 연결은 다음 발주서로 미룬다.

## 완료 기준

- Fake adapter로 요청/응답 객체가 왕복한다.
- 노드 코드는 아직 LLM adapter를 사용하지 않아도 된다.

## 제외

- Qwen 실행.
- 스트리밍.
