# ORDER 061: Document Memory Index v2

**상태**: 정식 발주서  
**승격일**: 2026-06-22  
**출처**: 임베딩 문서 검색을 장기기억 후보 체계로 확장할 필요  
**목표**: 내부 문서와 실행 기록을 장기기억 후보로 다룰 수 있도록 안정적인 문서 기억 인덱스를 만든다.

## 배경

현재 `search_docs`는 문서를 chunk로 나누고 임베딩 캐시를 활용한다.  
하지만 이것은 검색 도구에 가까우며, 0과 L루프가 장기기억처럼 신뢰하고 재사용하기에는 문서 ID, snapshot, hash, 문서 종류의 경계가 아직 약하다.

## 범위

1. `DocumentMemoryIndexFrame` 또는 동등한 payload 구조를 만든다.
2. 문서마다 `doc_id`, `path`, `hash`, `snapshot_id`, `chunk_count`, `document_kind`를 저장한다.
3. 발주서, 실행 기록, 지도 문서, 철학 문서를 서로 다른 문서 종류로 구분한다.
4. 원본 문서와 파생 요약 문서를 분리한다.
5. `search_docs` 결과가 문서 기억 인덱스의 ID를 함께 반환하게 한다.

## 원칙

1. 인덱스에 존재한다는 사실은 문서 내용이 참이라는 뜻이 아니다.
2. 문서 내용이 바뀌면 snapshot/hash가 바뀌어야 한다.
3. 장기기억 후보는 항상 원본 문서 위치로 돌아갈 수 있어야 한다.

## 완료 기준

1. 문서 인덱스 payload가 DataStore 또는 cache에 저장된다.
2. 문서 검색 결과에서 doc/chunk/snapshot ID를 확인할 수 있다.
3. 문서 변경 후 hash가 바뀌는지 확인하는 probe가 있다.
4. `python main.py smoke-test`가 통과한다.
