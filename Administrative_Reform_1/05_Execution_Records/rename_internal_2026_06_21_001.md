# Rename Internal 2026-06-21 001

## 요청

```text
이전 영어 발음식 내부 코드명을 없애고 더 쌈박한 말로 변경
```

## 결과

내부 Python 패키지명과 코드 경로를 다음처럼 변경했다.

```text
이전 내부 패키지명 -> songryeon_core
이전 표시명 -> SongRyeon Core
```

## 함께 변경한 것

1. Python import 경로.
2. 패키지 폴더명.
3. prompt ref 경로.
4. cache 폴더명.
5. README의 프로젝트 표시명.
6. CLI 표시명.

## 검증

```text
python dry_run.py
python main.py smoke-test
python main.py search-docs SongRyeon --top-k 1
이전 내부 코드명 검색
```

## 결과

```text
DRY_RUN_OK
SMOKE_TEST_OK
이전 내부 코드명 검색 결과 없음
```
