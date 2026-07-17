# ORDER 265: GitHub Actions Node 24 Maintenance v0

## 1. 배경

ORDER 264 수정 뒤 GitHub Actions run `29561437912`는 성공했지만,
`actions/checkout@v4`와 `actions/setup-python@v5`의 Node.js 20 runtime이
deprecated됐다는 경고가 남았다.

## 2. 목표

공식 Node.js 24 기반 action으로 CI를 갱신해 공개 저장소의 경고와 향후 실행 중단
위험을 제거한다.

## 3. 구현 범위

1. `actions/checkout@v6`을 사용한다.
2. `actions/setup-python@v6`을 사용한다.
3. workflow 권한을 `contents: read`로 명시한다.
4. Python 버전, 설치 명령, compileall, pytest, smoke-test 순서는 유지한다.

## 4. 금지

- 제품 코드 또는 테스트 의미 변경
- 검증 단계 삭제
- CI 실패 무시 또는 continue-on-error 추가
- write 권한 추가

## 5. 완료 조건

1. workflow YAML에 Node.js 24 기반 action 버전이 반영된다.
2. 새 GitHub Actions main run이 성공한다.
3. 기존 Node.js 20 deprecation 경고가 사라진다.
