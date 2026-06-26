# TMP ORDER 024: Main CLI Entry Point

## 목표

프로젝트 공식 실행 진입점 `main.py`를 만든다.

## 배경

현재 루트에는 `dry_run.py`가 있지만, 원래 구성 요소 목록에는 `main.py`가 있었다.

## 범위

1. `main.py`를 만든다.
2. `dry-run`, `search-docs`, `show-orders` 같은 최소 명령을 제공한다.
3. argparse만 사용하고 외부 CLI 라이브러리는 쓰지 않는다.
4. 기존 `dry_run.py` 래퍼는 유지한다.

## 완료 기준

- `python main.py dry-run`이 통과한다.
- `python main.py search-docs "검색어"`가 임베딩 검색 결과를 출력한다.

## 제외

- 대화형 채팅 UI.
- 장기 실행 서버.
