# ORDER 018-040: Phase 2 Structural Sweep

**상태**: 정식 발주서  
**승격일**: 2026-06-21  
**출처**: 사용자 요청 "전부 ㄱㄱ"  
**목표**: TMP Auto Hunt Phase 2의 018~040 후보를 한 번에 얇고 넓게 구현하여 다음 개발 레일을 완성한다.

## 범위

1. 0/1/2/3의 DataStore payload 저장 레일을 만든다.
2. 턴 outcome, runtime export, main CLI를 만든다.
3. prompt scaffold와 LLM adapter/interface를 만든다.
4. JSON 검증, FakeLLM, Qwen HTTP adapter spike를 만든다.
5. 3/2/1/0 LLM probe wrapper를 만든다.
6. embedding backend, document snapshot, vector cache metadata를 만든다.
7. failure signal v0.2, turn capsule persistence, trace replay, smoke test를 만든다.

## 구현 원칙

1. 실제 Qwen 실행은 `QWEN_LOCAL_ENDPOINT`가 없으면 시도하지 않는다.
2. LLM 노드화는 Fake adapter probe까지만 기본 검증한다.
3. 기존 dry_run 경로는 계속 규칙 기반으로 유지한다.
4. 새 기능은 trace/DataStore/source id 원칙을 따른다.

## 완료 기준

1. `python dry_run.py`가 통과한다.
2. `python main.py smoke-test`가 통과한다.
3. `python main.py dry-run --export <dir>`가 trace/data/report/summary를 저장한다.
4. `python main.py replay <dir>`가 저장된 trace/data를 읽는다.
5. Qwen endpoint가 없을 때는 명시적 실패 결과를 돌려준다.

## 주의

이 발주서는 깊은 품질 개선이 아니라 구조 레일 확장이다.  
각 노드의 실제 지능, 프롬프트 품질, Qwen 성능, 임베딩 품질은 후속 세부 발주서에서 다룬다.
