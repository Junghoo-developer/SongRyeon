# TMP ORDER 030: Node 3 LLM Reporter

## 목표

가장 위험이 낮은 3 보고관부터 LLM adapter로 교체하는 실험을 한다.

## 배경

3은 2가 허용한 정보 안에서만 말하면 되므로, 첫 LLM 노드 실험 대상으로 적합하다.

## 범위

1. `ReportFrame`을 입력으로 사용한다.
2. 2가 허용한 DataRef 밖의 단정 금지 규칙을 프롬프트에 넣는다.
3. LLM 출력은 새 report payload로 저장한다.
4. 기존 규칙 기반 reporter fallback을 유지한다.

## 완료 기준

- FakeLLMAdapter 기준으로 3 보고관 실행이 통과한다.
- 실제 Qwen 연결은 선택적으로만 검증한다.

## 제외

- 2의 판단 LLM화.
- 자유로운 장문 대화.
