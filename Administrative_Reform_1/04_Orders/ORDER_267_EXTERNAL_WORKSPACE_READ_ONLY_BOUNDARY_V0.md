# ORDER 267: External Workspace Read-Only Boundary v0

## 1. 배경

SongRyeon Core의 L루프는 현재 송련 저장소의 `Administrative_Reform_1` 문서와
현재 실행 폴더의 코드 파일을 조사할 수 있다. 심야 소스 수집 명령도 `--root`를
받지만, 실제 manifest는 `AGENTS.md`, `README.md`, `main.py`와 송련 전용 glob에
묶여 있다.

따라서 사용자가 자신의 업무 폴더를 명시적으로 선택하고 그 안의 문서와 코드를
조사하는 일반 제품 경계는 아직 없다.

## 2. 목표

사용자가 선택한 외부 업무 폴더를 로컬 fake/Qwen 턴에 읽기 전용으로 연결한다.
코드는 업무 폴더의 파일 좌표와 관측 metadata를 절대정보 manifest로 기록하고,
L루프는 기존 도구 계약을 재사용해 해당 폴더 안에서만 검색하고 원문을 읽는다.

## 3. 승인된 정책

1. 파일을 송련 저장소로 복사하지 않고 원래 업무 폴더를 읽기 전용으로 연결한다.
2. 첫 MVP 지원 범위는 `.md`, `.txt`, `.py`, `.json`, `.toml`, `.yaml`, `.yml`이다.
3. `.env`, 비밀키 이름, `.git`, 가상환경, cache, build 산출물은 명시 정책으로 제외한다.
4. 외부 API 명령에는 workspace 옵션을 열지 않는다. fake/Qwen 로컬 경로만 사용하며,
   workspace가 활성화된 Qwen HTTP endpoint는 loopback 주소만 허용한다.
5. Neo4j와 심야정부에는 자동 적재하지 않는다.
6. 폴더 밖 경로와 symbolic-link 탈출은 code가 차단한다.
7. 후보 파일 수와 실제 도구 원문 읽기 기록을 분리한다.

## 4. 구현 범위

1. `WorkspaceManifestFrame`에 다음 절대정보를 기록한다.
   - 선택한 root와 사람이 볼 workspace label
   - 지원 파일의 상대 경로, 종류, 확장자, 크기, 수정 시각, content hash
   - 제외된 파일/폴더 count와 명시적 제외 이유 count
   - read-only, local-only, graph-ingest not-run 상태
2. node_0 pre-route memory packet에 manifest 좌표와 count를 복사한다.
3. node_1은 active workspace가 있다는 사실과 지원 파일 count만 보고 L/2를 판단한다.
4. L루프의 document root와 code root를 선택한 workspace로 함께 바꾼다.
5. `.md`와 `.txt`는 문서 도구, 나머지 허용 확장자는 코드/설정 도구로 읽는다.
6. `--workspace` CLI와 `SONGRYEON_WORKSPACE_ROOT` 로컬 기본 설정을 제공한다.
7. `workspace-check`로 LLM 호출 없이 manifest 경계를 미리 확인할 수 있게 한다.

## 5. 정보 권한

- 파일 존재, path, count, size, mtime, hash, 실제 도구 read 결과는 code-owned absolute다.
- 어떤 파일이 사용자 질문과 관련 있는지는 L1/L2/L3의 명시된 LLM 판단이다.
- code는 파일명 단어를 보고 의미 관련성을 추측하지 않는다.
- 제외 규칙은 숨은 휴리스틱이 아니라 이 발주서와 코드 상수에 드러난 보안 정책이다.

## 6. 금지

- 파일 수정, 삭제, 이동
- 외부 API로 workspace 원문 전송
- 자동 Neo4j/심야정부 적재
- PDF, Word, Excel, 이미지, binary 파싱
- 의미 기반 secret 탐지라고 과장
- workspace 파일 관련성을 code가 대신 판단
- 기존 송련 전용 manifest를 일반 workspace manifest로 덮어쓰기

## 7. 완료 조건

1. `workspace-check`가 지원 파일과 제외 count를 code absolute로 표시한다.
2. `.env`, private-key 계열 이름과 제외 폴더가 manifest와 도구 목록에서 빠진다.
3. root 밖 상대경로와 symbolic link는 읽히지 않는다.
4. fake/Qwen 로컬 턴에 workspace root가 전달된다.
5. L루프가 workspace의 `.md`/`.txt` 문서 또는 코드 파일을 실제 도구로 읽을 수 있다.
6. runtime 출력에서 workspace candidate count와 graph ingest not-run을 확인할 수 있다.
7. 외부 API 명령은 workspace 옵션을 제공하지 않는다.
8. `python -m compileall songryeon_core main.py` 통과.
9. 표적 pytest와 전체 pytest 통과.
10. `python main.py smoke-test` 통과.

## 8. 후속 경계

이 작업 뒤에는 새 기능 확장을 동결하고 live local 안정성 기준선 감사로 넘어간다.
업무 파일의 그래프 적재, 변경 계보, GUI 업로드, binary 문서 지원은 별도 발주다.
