# ORDER 013: Embedding Document Tools

**상태**: 정식 발주서  
**승격일**: 2026-06-21  
**출처**: 사용자 요청 "search_docs는 임베딩으로 하자"  
**목표**: 내부 문서를 읽기 전용으로 다루는 도구와 임베딩 검색 도구를 만들고, L루프 드라이런에 연결한다.

## 범위

1. `songryeon_core/tools/` 패키지를 만든다.
2. Markdown 문서를 안전하게 목록화하고 읽는 도구를 만든다.
3. 문서를 chunk로 나누고 로컬 임베딩 벡터를 만든다.
4. `search_docs`를 키워드 검색이 아니라 벡터 유사도 검색으로 구현한다.
5. 도구 실행 결과를 trace에 남기는 `ToolRunner`를 만든다.
6. L루프가 L2 이후 `search_docs` 도구를 호출하게 한다.

## 원칙

1. 도구는 읽기 전용이다.
2. 기본 문서 루트는 `Administrative_Reform_1/`이다.
3. 외부 임베딩 모델은 아직 붙이지 않는다.
4. 현재 임베딩은 의존성 없는 로컬 해시 임베딩이다.
5. 검색 결과는 절대정보 metadata와 score로 남기고, 의미 판단은 나중에 L3/2가 맡는다.

## 완료 기준

1. `python dry_run.py`가 통과한다.
2. L루프 안에서 `search_docs` 도구 호출 trace가 생긴다.
3. 도구 결과 DataRef가 생성된다.
4. Qwen, LangGraph, DB는 아직 사용하지 않는다.
