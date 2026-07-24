# ORDER 286 SongRyeon Core Archive And Empty Refoundation Space 실행 기록

- 실행일: 2026-07-24
- 상태: 완료
- 성격: Git/GitHub 보존 및 빈 브랜치 마련
- 새 송련 설계·구현: 없음

## 1. 사용자 승인 경계

사용자는 기존 SongRyeon Core의 안전한 처리를 Codex에 맡기고, 새 송련은 모든 내용을
사용자가 직접 결재하므로 Codex가 설계 철학에 개입하지 말고 GitHub 공간만 마련하도록
지시했다.

따라서 이번 작업은 기존 자료 보존과 Git ref 생성만 수행했다. 새 송련의 README,
폴더, 코드, 의존성, 라이선스, 설계 문서는 만들지 않았다.

## 2. 시작 상태

- 로컬 브랜치: `main`
- 로컬 `main`과 `origin/main` 관계: 로컬이 20 commit 앞섬
- 수정 파일: 4개
- 미추적 파일: 2개
- 보존 대상의 성격:
  - 정후용 코드 독해 교재
  - 학습 시간 안전 기준선 감사 기록
  - 해당 문서 README 색인
  - 2026-07-23 테스트 기준선 README 갱신

현재 변경을 폐기하거나 stash하지 않고 보존 스냅샷에 포함했다.

## 3. 생성한 Git 참조

### 기존 Core 보존

- 브랜치: `archive/songryeon-core-v0-2026-07-24`
- 최초 보존 스냅샷 commit:
  `7f89a419029763fb8f9616520dbf9f64b75b6f2d`
- 고정 태그: `songryeon-core-v0-archive-2026-07-24`

### 새 송련의 빈 공간

- 브랜치: `refoundation/songryeon-v1`
- commit: `2dd3ad6c7d608b447c33727ba88f5c947ea83e67`
- tree: `4b825dc642cb6eb9a060e54bf8d69288fbee4904`
- 현재 tree entry count: `0`
- 부모 commit:
  `7f89a419029763fb8f9616520dbf9f64b75b6f2d`

refoundation commit은 기존 archive 스냅샷을 부모로 가지므로 Git 역사가 끊기지 않는다.
현재 tree는 비어 있으므로 기존 Core 파일이나 Codex가 임의로 정한 새 설계 파일은 없다.

## 4. 원격 검증

첫 push 뒤 `git ls-remote --heads`로 다음을 확인했다.

```text
7f89a419029763fb8f9616520dbf9f64b75b6f2d
refs/heads/archive/songryeon-core-v0-2026-07-24

2dd3ad6c7d608b447c33727ba88f5c947ea83e67
refs/heads/refoundation/songryeon-v1
```

실행 기록을 포함한 최종 archive commit에는
`songryeon-core-v0-archive-2026-07-24` annotated tag를 부착하고, branch와 tag를
다시 원격 검증한다.

## 5. 변경하지 않은 것

- 로컬 `main`
- 원격 `origin/main`
- GitHub 기본 브랜치
- 기존 원격 브랜치와 태그
- 새 송련의 제품명 세부 표기, 목표, 구조, 철학, 코드
- 대회 제출 대상 브랜치

## 6. 복구·열람 방법

기존 Core의 전체 보존판은 다음 태그 또는 archive 브랜치로 열람할 수 있다.

```powershell
git switch --detach songryeon-core-v0-archive-2026-07-24
git switch archive/songryeon-core-v0-2026-07-24
```

새 송련의 빈 공간은 사용자가 설계와 첫 파일을 결재한 뒤에만 사용한다.

```powershell
git switch refoundation/songryeon-v1
```
