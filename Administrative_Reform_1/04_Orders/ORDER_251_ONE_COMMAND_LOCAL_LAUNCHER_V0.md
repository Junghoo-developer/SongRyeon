# ORDER 251: One Command Local Launcher v0

## 1. 목표

로컬 설정이 준비된 사용자는 긴 CLI 옵션 없이 다음 한 줄로 송련 대화를 시작한다.

```powershell
python main.py
```

## 2. 배경

현재 Qwen chat, live trace, Vessel R 실험 gate, Neo4j database, timeout 옵션을 매번
터미널에 적어야 한다. 기능 검증에는 유용하지만 일상 사용과 외부 배포에는 부담이다.

## 3. 구현 경계

- `main.py`는 프로젝트 루트의 `.env`를 자동으로 읽는다.
- 이미 설정된 프로세스 환경 변수는 `.env` 값으로 덮어쓰지 않는다.
- 인자가 없으면 `qwen-chat`을 기본 실행한다.
- 기본 timeout은 180초, live trace는 켠다.
- Neo4j URI/user/password/database가 모두 설정돼 있으면 Vessel R gate를 자동으로 켠다.
- 명시적 기존 subcommand와 옵션은 바꾸지 않는다.
- `.env` 값과 비밀번호는 terminal, trace, Git에 출력하지 않는다.
- 공개 저장소에는 값 없는 `.env.example`만 둔다.

## 4. 설정 정책

- `SONGRYEON_DEFAULT_TIMEOUT_SECONDS`: 기본 LLM timeout, 기본값 180
- `SONGRYEON_DEFAULT_LIVE_TRACE`: 기본 live trace, 기본값 true
- `SONGRYEON_DEFAULT_ENABLE_VESSEL_R`: `auto`, `true`, `false`; 기본값 auto
- `QWEN_MODEL_ID`: 선택적 Qwen 모델 이름
- 기존 `SONGRYEON_NEO4J_*` 값은 그대로 사용한다.

## 5. 완료 조건

1. `.env`가 현재 프로세스 환경을 덮어쓰지 않고 로드된다.
2. 인자 없는 기본 argv가 qwen-chat/timeout/live-trace를 포함한다.
3. Neo4j 설정이 완전할 때만 auto mode가 R gate를 포함한다.
4. `/exit`을 입력한 `python main.py`가 모델 호출 없이 정상 종료한다.
5. 기존 CLI, pytest, smoke-test가 유지된다.

## 6. 금지

- 비밀번호 hard-code 및 Git 기록 금지
- 기본 실행에서 OpenAI/Codex 유료 경로 자동 선택 금지
- node_1 의미 라우팅을 code가 대신하는 규칙 추가 금지
- 기존 전문 CLI 삭제 금지
