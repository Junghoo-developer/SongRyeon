# ORDER_208_RELEASE_SAFETY_AND_COMMIT_READINESS_AUDIT_V0

## 상태

감사 완료.

## 배경

ORDER_204부터 ORDER_207까지 R/L route 설명, 인간 중심 학습 규칙, 배포용 fake-turn, 데모 동선 정리가 이어졌다.
다음 단계는 GitHub에 올릴 수 있는 상태인지 안전하게 점검하고, 커밋할 파일과 보류할 파일을 분리하는 것이다.

## 목표

공개/배포 전 위험 요소를 점검한다.

1. local env / password 파일이 git 추적 대상인지 확인한다.
2. token형 비밀키 패턴이 코드/문서에 남아 있는지 확인한다.
3. 로컬 절대경로나 OneDrive 경로 노출을 확인한다.
4. generated cache/output/tmp가 staging 대상이 아닌지 확인한다.
5. 현재 dirty worktree에서 커밋 가능한 변경과 보류할 변경을 구분한다.
6. `PUBLICATION_CHECKLIST.md`의 staging 안내를 `git add .` 없이 명시 파일 방식으로 정리한다.

## 감사 결과

### env / local artifact 추적 상태

- `.env`: git 추적 대상 아님, `.gitignore`에서 제외됨.
- `.env.vessel.local.ps1`: git 추적 대상 아님, `.gitignore`에서 제외됨.
- `.songryeon_core_cache/`: `.gitignore`에서 제외됨.
- `output/`: `.gitignore`에서 제외됨.
- `tmp/`: `.gitignore`에서 제외됨.

### token형 비밀키 패턴

다음 패턴으로 스캔했다.

```text
sk-...
ghp_...
github_pat_...
hf_...
BEGIN RSA/OPENSSH/PRIVATE
```

결과: `NO_TOKEN_PATTERN_HITS`.

### 넓은 password/secret 문자열 스캔

`password`, `secret`, `authorization` 같은 넓은 문자열은 여러 코드/문서에서 잡혔다.
대부분 Neo4j password 설정 필드, 실패 이유, 문서 안내, 테스트용 fake field였다.
이 항목은 "비밀값 노출"이 아니라 "비밀번호 설정을 다루는 코드/문서"로 보인다.

### 로컬 경로 문자열

`C:\Users`, `OneDrive`, `바탕 화면` 계열 스캔 결과는 일부 실행 기록과 체크리스트에서 발견됐다.
실행 기록의 대부분은 OneDrive/cache PermissionError 설명이며, 직접적인 개인 비밀값은 아니다.
다만 공개 문서에서 로컬 환경 언급이 늘어나면 소음이 될 수 있으므로 장기적으로 실행 기록 경량화/공개판 문서 분리를 검토할 수 있다.

## 커밋 가능 묶음

ORDER_204~ORDER_208의 직접 변경은 한 PR/커밋 묶음으로 볼 수 있다.

- R/L route capability card
- 인간 중심 학습 규칙
- release-friendly fake-turn
- release demo path 문서화
- release safety/checklist 정리

## 보류/주의 파일

- `Administrative_Reform_1/00_Philosophy/README.md`
- `Administrative_Reform_1/00_Philosophy/Dyadic_Vessel_Functional_Consciousness_Philosophy_2026_07_03.md`

위 파일들은 작업 시작 전부터 존재하던 unrelated dirty 항목으로 보인다.
이번 release safety commit에 섞지 않는 것이 안전하다.

## 완료 조건

- `git diff --check` 통과.
- token형 비밀키 패턴 없음.
- env/local cache가 git 추적 대상이 아님.
- PUBLICATION_CHECKLIST의 staging 안내가 명시 파일 중심으로 바뀜.
