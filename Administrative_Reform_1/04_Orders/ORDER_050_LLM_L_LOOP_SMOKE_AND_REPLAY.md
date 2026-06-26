# ORDER 050: LLM L Loop Smoke And Replay

**상태**: 정식 발주서  
**승격일**: 2026-06-21  
**출처**: 사용자 요청 "llm 넣고 ... 능률 도구 사용까지"  
**목표**: LLM이 들어간 L루프를 smoke test와 replay로 검증해, 모델 문제와 구조 문제를 분리해서 볼 수 있게 한다.

## 배경

LLM 자율 도구 사용은 한 번에 믿으면 안 된다.  
성공했을 때도 왜 성공했는지, 실패했을 때도 어디서 실패했는지 replay할 수 있어야 한다.

## 범위

1. FakeLLM 기반 deterministic test를 만든다.
2. Qwen endpoint가 있을 때만 Qwen integration test를 선택적으로 실행한다.
3. LLM L루프 실행 결과를 runtime artifact로 export한다.
4. replay가 LLM call, tool choice, tool result, controller decision을 순서대로 보여준다.
5. 규칙 기반 L루프와 LLM L루프의 산출물 차이를 요약한다.

## 원칙

1. 기본 smoke test는 네트워크나 Qwen endpoint 없이 통과해야 한다.
2. Qwen 테스트 실패는 구조 실패와 구분해서 기록한다.
3. replay는 사람이 학습할 수 있을 정도로 읽기 쉬워야 한다.

## 완료 기준

1. `python main.py smoke-test`가 FakeLLM 기반 L루프 검사를 포함한다.
2. `python main.py qwen-l-loop-smoke` 또는 동등한 명령은 endpoint가 있을 때만 실행된다.
3. runtime artifact에 LLM call과 tool use 흐름이 저장된다.
4. replay로 L루프의 자율 도구 사용 경로를 확인할 수 있다.
