# TMP ORDER 034: Embedding Backend Interface

## 목표

현재 로컬 해시 임베딩을 실제 임베딩 모델로 교체할 수 있는 인터페이스를 만든다.

## 배경

현재 `HashEmbeddingModel`은 의존성 없는 MVP용이다.  
진짜 의미 검색에는 별도 embedding backend가 필요하다.

## 범위

1. `EmbeddingBackend` 인터페이스를 만든다.
2. 기존 hash model을 `HashEmbeddingBackend`로 감싼다.
3. backend_id, dimensions, normalize 정책을 metadata로 남긴다.
4. `search_docs`는 backend 인터페이스만 사용한다.

## 완료 기준

- 기존 dry_run 결과가 유지된다.
- backend 교체 지점이 한 곳으로 모인다.

## 제외

- 실제 외부 embedding model 연결.
- vector DB.
