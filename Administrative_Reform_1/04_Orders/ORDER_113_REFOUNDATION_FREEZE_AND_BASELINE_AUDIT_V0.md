# ORDER 113: Refoundation Freeze And Baseline Audit v0

## 상태

발주서 초안.

사용자 승인 후 구현한다.

## 배경

SongRyeon Core는 최근 기억, L continuation, router honesty, node_4 guard, live trace, wide L budget까지 빠르게 확장됐다.

하지만 이제 다음 문제가 커졌다.

```text
schemas.py가 3500줄 이상이다.
smoke_test.py가 5000줄 이상이다.
pytest 체계가 없다.
tests/ 폴더가 없다.
CI는 compileall + python main.py smoke-test만 돌린다.
```

이 상태에서 ORDER_112 같은 새 기능을 바로 구현하면, 이미 비대한 파일에 더 많은 schema와 smoke가 붙는다.

따라서 기능 확장을 잠시 멈추고 재정립 기준선을 먼저 잡는다.

## 목표

현재 프로젝트 상태를 "리팩터링 전 기준선"으로 고정한다.

핵심 목표:

1. 기능 확장 freeze 선언
2. 현재 파일 비대도와 테스트 구조 감사
3. compileall / smoke-test 기준선 기록
4. pytest 전환과 schema/smoke 분해의 순서 확정
5. ORDER_112 구현 재개 조건 명시

## 구현 범위

### 1. 기준선 감사 실행

다음을 확인한다.

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
```

추가로 다음 정보를 기록한다.

- 가장 큰 Python 파일 상위 20개
- `schemas.py` line count
- `smoke_test.py` line count
- pytest 설정 파일 존재 여부
- `tests/` 폴더 존재 여부
- GitHub Actions 테스트 명령
- 현재 ORDER_112는 구현 보류 상태인지

### 2. 실행 기록 작성

실행 기록 후보:

```text
Administrative_Reform_1/05_Execution_Records/refoundation_freeze_baseline_2026_06_27_001.md
```

기록해야 할 것:

- 왜 기능 확장을 멈췄는지
- 현재 기준선 명령 결과
- 비대한 파일 수치
- 다음 발주 순서
- ORDER_112 재개 조건

### 3. 개발 freeze 범위 명시

ORDER_113 완료 전후로 다음은 하지 않는다.

- ORDER_112 구현
- 새 memory 기능
- 새 L loop 정책
- W/R loop
- scheduler
- 외부 DB/vector DB
- schema field 대량 추가

단, 기준선 측정과 문서 정리는 허용한다.

## 비범위

이번 발주에서 하지 않는다.

- pytest 도입 구현
- `schemas.py` 분해
- `smoke_test.py` 분해
- CI 변경
- 기능 동작 변경

이 발주는 "멈춤과 기준선"만 담당한다.

## 완료 조건

```powershell
python -m compileall songryeon_core main.py
python main.py smoke-test
```

완료 보고에는 다음을 적는다.

- compileall 결과
- smoke-test 결과
- `schemas.py` line count
- `smoke_test.py` line count
- pytest/tests 존재 여부
- 다음 권장 발주: ORDER_114
