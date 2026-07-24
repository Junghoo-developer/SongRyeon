# ORDER 286: SongRyeon Core Archive And Empty Refoundation Space v0

- 상태: 사용자 승인 / 실행 중
- 작성일: 2026-07-24
- 승인 문장: 기존 송련 Core를 안전하게 처리하고, 새 송련에는 설계 개입 없이 GitHub 공간만 마련한다.

## 1. 목적

기존 SongRyeon Core의 코드, 문서, 테스트, 미커밋 학습 자료와 Git 역사를 원격
저장소에 보존한다. 같은 GitHub 저장소와 SongRyeon 이름을 유지하면서, 사용자 승인
전에는 어떤 설계나 구현도 들어 있지 않은 빈 refoundation 브랜치를 마련한다.

## 2. 보존 대상

1. 현재 로컬 `main`이 `origin/main`보다 앞선 20개 커밋
2. 2026-07-24 작업 시작 시점의 수정 파일 4개
3. 2026-07-24 작업 시작 시점의 미추적 학습/감사 문서 2개
4. 전체 기존 Git commit history

## 3. Git 참조

- 보존 브랜치: `archive/songryeon-core-v0-2026-07-24`
- 보존 태그: `songryeon-core-v0-archive-2026-07-24`
- 빈 재건 공간: `refoundation/songryeon-v1`

`refoundation/songryeon-v1`은 기존 역사에 부모 연결을 둔 빈 tree commit으로 만든다.
따라서 새 브랜치의 현재 파일 공간은 비어 있지만, 과거 commit history는 끊지 않는다.

## 4. 허용 작업

1. 현재 변경을 보존 브랜치에 명시적으로 stage하고 commit
2. 보존 브랜치와 태그를 원격 GitHub 저장소에 push
3. 빈 tree commit과 refoundation 브랜치를 생성하고 원격에 push
4. 원격 ref hash를 read-only 명령으로 재검증
5. 이 작업의 실행 기록과 README 색인을 보존 브랜치에 남김

## 5. 금지

- 기존 `main` 또는 `origin/main` 삭제
- force push 또는 history rewrite
- 기존 사용자 변경 폐기
- 새 송련의 설계 철학, 폴더 구조, 코드, 의존성, 라이선스 결정
- GitHub 기본 브랜치 변경
- 새 송련 브랜치에 placeholder 설계나 임의 README 추가
- 기존 archive 파일을 refoundation 현재 tree에 복제

## 6. 완료 조건

1. 원격 보존 브랜치가 기존 Core 전체와 현재 변경을 포함한다.
2. 원격 보존 태그가 고정된 archive commit을 가리킨다.
3. 원격 refoundation 브랜치의 현재 tree가 비어 있다.
4. refoundation commit은 기존 SongRyeon 역사에 부모 연결을 가진다.
5. 기존 `main`과 GitHub 기본 브랜치는 변경하지 않는다.
6. 새 송련의 설계·구현 파일은 0개다.
