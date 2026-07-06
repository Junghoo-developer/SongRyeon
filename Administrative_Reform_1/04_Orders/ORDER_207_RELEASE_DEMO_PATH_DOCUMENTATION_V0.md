# ORDER_207_RELEASE_DEMO_PATH_DOCUMENTATION_V0

## 상태

구현 완료.

## 배경

ORDER_206으로 Qwen/Neo4j 없이 실행 가능한 첫 `fake-turn` 데모가 안정화되었다.
다음 배포 준비 단계는 README와 DEMO 문서가 처음 온 사용자를 올바른 순서로 안내하게 만드는 것이다.

기존 `DEMO.md`는 그래프/Vessel 경로가 먼저 보여서, Qwen이나 Neo4j가 없는 사용자가 첫 실행 전에 부담을 느낄 수 있었다.

## 목표

배포용 데모 경로를 3층으로 정리한다.

1. Qwen/Neo4j 없는 첫 실행: `fake-turn`
2. 로컬 기준선 검증: `compileall`, `pytest`, `smoke-test`
3. 선택 기능: Neo4j Vessel, R traversal, Qwen live turn, night summary

## 구현 범위

- `DEMO.md`를 3층 데모 경로로 재정렬한다.
- `README.md`와 `README.ko.md`의 Current Demo Path를 같은 순서로 맞춘다.
- `PUBLICATION_CHECKLIST.md`에 no-model 첫 데모 확인 항목을 추가한다.
- `04_Orders/README.md`와 `05_Execution_Records/README.md`에 ORDER_207 추적 항목을 추가한다.

## 금지

- 코드 기능 변경 없음.
- R/L 라우팅 정책 변경 없음.
- Neo4j/Vessel schema 변경 없음.
- Qwen adapter 변경 없음.

## 완료 조건

- 처음 온 사용자가 `DEMO.md`만 보고 1층 fake-turn부터 따라갈 수 있다.
- Qwen/Neo4j가 필요한 명령과 필요 없는 명령이 분리되어 있다.
- 실패 상태의 의미가 문서에 짧게 적혀 있다.
- `git diff --check` 통과.
