# ORDER 251 실행 기록

- 날짜: 2026-07-11
- 결과: `.env` 자동 로드 및 `python main.py` 한 줄 대화 실행 구현 완료
- 발주서: `ORDER_251_ONE_COMMAND_LOCAL_LAUNCHER_V0.md`

## 1. 구현

- `main.py`가 프로젝트 루트의 Git 비추적 `.env`를 자동으로 읽는다.
- 프로세스에 이미 존재하는 환경 변수는 `.env` 값으로 덮어쓰지 않는다.
- 인자가 없으면 기존 argparse에 다음 qwen-chat 기본 인자를 공급한다.
  - timeout 180초
  - live trace 켜짐
  - Neo4j 설정 완전 시 R experimental/Vessel gate 켜짐
- 기존 명시적 subcommand와 옵션은 그대로 유지한다.
- 공개 설정 예시는 `.env.example`로 추가했다.

## 2. 실제 로컬 확인

현재 `.env`에는 Neo4j URI, user, database, password가 모두 설정돼 있다. 실제 값은
출력하거나 실행기록에 복사하지 않았다.

인자 없는 실행에 `/exit`을 즉시 입력해 모델 호출 없이 확인한 결과:

```text
SongRyeon qwen-chat
간편 실행: Qwen / Vessel R=켜짐 / 실시간 진행=켜짐 / timeout=180초
송련> 종료
```

PowerShell 환경 스크립트를 dot-source하지 않은 새 명령 실행에서도:

```text
python main.py vessel-readback --database neo4j
```

결과는 `VESSEL_READBACK_OK / readback_status=passed`였다. 따라서 `.env` 자동 로드가
Neo4j password configured 상태까지 실제로 전달됐다.

## 3. 테스트

- `.env`가 프로세스 환경을 덮어쓰지 않는지 확인
- 따옴표 값과 `=`가 포함된 값을 보존하는지 확인
- Neo4j 설정 완전/불완전에 따른 auto R gate를 확인
- 명시적 `quick-smoke` 인자를 기본 qwen-chat으로 바꾸지 않는지 확인
- 인자 없는 `python main.py`가 qwen-chat을 열고 `/exit`으로 정상 종료하는지 확인

## 4. 검증

- `python -m compileall songryeon_core main.py`: 통과
- ORDER 251 pytest: 4 passed
- 전체 pytest: 420 passed, 5 deselected
- `python main.py smoke-test`: `SMOKE_TEST_OK`
- `python main.py --help`: 통과
- `git diff --check`: 통과

## 5. 경계

- 기본 실행은 무료 로컬 Qwen만 사용하며 OpenAI/Codex를 자동 선택하지 않는다.
- Vessel R auto mode는 Neo4j 필수 값이 모두 있을 때만 켜진다.
- `.env`와 실제 비밀번호는 Git 비추적 상태를 유지한다.
- 전문 감사·강제 라우팅 명령은 삭제하지 않았다.
