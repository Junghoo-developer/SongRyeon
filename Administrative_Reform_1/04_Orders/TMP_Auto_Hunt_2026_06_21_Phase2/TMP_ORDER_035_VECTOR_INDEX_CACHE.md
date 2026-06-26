# TMP ORDER 035: Vector Index Cache

## 목표

매번 문서를 다시 chunk/embedding하지 않고 인덱스를 캐시한다.

## 배경

현재 `search_docs`는 호출 때마다 문서를 읽고 임베딩한다.  
문서가 늘면 느려진다.

## 범위

1. 인덱스 캐시 파일 형식을 정한다.
2. document snapshot hash와 embedding backend id가 같으면 캐시를 재사용한다.
3. 캐시 miss 시 재생성한다.
4. 캐시 metadata를 DataStore 또는 실행 기록에 남긴다.

## 완료 기준

- 같은 문서 상태에서 두 번째 검색은 캐시를 사용한다.
- 캐시가 깨졌을 때 안전하게 재생성한다.

## 제외

- 외부 vector DB.
- ANN 최적화.
