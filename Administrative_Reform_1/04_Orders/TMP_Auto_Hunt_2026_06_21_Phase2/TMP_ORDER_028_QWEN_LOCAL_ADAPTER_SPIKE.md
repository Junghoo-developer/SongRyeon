# TMP ORDER 028: Qwen Local Adapter Spike

## 목표

로컬 Qwen 14B를 실제로 호출할 수 있는 최소 어댑터 실험을 한다.

## 배경

사용자의 최종 목표는 Qwen 14B 기반 로컬 에이전트다.  
하지만 모델 실행 방식은 환경마다 다르므로 먼저 adapter spike로 좁게 검증한다.

## 범위

1. 사용자가 선택한 실행 방식 확인: Ollama, llama.cpp, transformers 중 하나.
2. Qwen 호출 adapter 하나만 만든다.
3. 입력 prompt와 출력 text를 기록한다.
4. trace/data 구조에는 아직 깊게 연결하지 않는다.

## 완료 기준

- 로컬 Qwen에 "ping" 성격의 요청을 보내 응답을 받는다.
- 실패 시 원인을 실행 기록에 남긴다.

## 제외

- 모든 노드 LLM화.
- 성능 최적화.
- GPU/양자화 튜닝.
