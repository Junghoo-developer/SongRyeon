# 대회 모델 실행 정책

이 문서는 송련 코어의 대회 제출·시연 경로와 별도 외부 API 통합시험을
구분합니다. 기준은 오픈소스 개발자대회
[운영규정 제9조 관련 공식 Q&A](https://osscontest.kr/notice/36)입니다.

공식 Q&A에 따르면 출품작에 탑재·적용되는 AI 모델은 최소 오픈웨이트여야
하고, 로컬 또는 자체 호스팅 서버에서 직접 실행할 수 있어야 합니다.
상용 API로만 호출하는 모델은 독립 실행 요건을 충족하지 못합니다. 다만
MCP·AI 에이전트 프레임워크처럼 AI 모델 연동 생태계를 만드는 소프트웨어의
**통합시험**에는 외부 API 호출 예외가 있고, 개발 중 코딩·디버깅 보조
서비스 사용도 허용됩니다. 사용 모델과 라이선스는 결과보고서의 AI 모델
활용·라이선스 기술명세에 기록해야 합니다.

## 대회 제출·시연 경로

송련의 공식 실행 프로필은 `contest_local_or_self_hosted`입니다.

- 모델은 로컬 PC 또는 참가자가 통제하는 자체 호스팅 서버에서 직접
  실행합니다.
- 모델 가중치와 라이선스를 확인할 수 있는 오픈웨이트 모델만 사용합니다.
- 대회용 대형 모델은 Ollama `gemma4:26b`입니다.
  - 모델 ID: `5571076f3d70`
  - 규모·양자화: 25.8B, `Q4_K_M`
  - 라이선스: Apache License 2.0
- `qwen3:14b`는 과거 모델 체급 탐색 대상이며 공식 v2 구조 비교군이나
  fallback이 아닙니다. `gemma4:26b` 결과와 섞어 집계하지 않습니다.
- 외부 상용 API를 자동 fallback으로 호출하지 않습니다. 로컬 모델 오류나
  미설치는 명시적인 실패로 끝냅니다.
- 일반 데모는 시작 화면에 Ollama 버전, 모델 태그·digest와 요청 컨텍스트를
  표시합니다. 평가용 원문 캡처는 모델 태그·전체 digest·요청 설정을 별도
  메타데이터에 남깁니다.
- Git 커밋, 운영체제·CPU·GPU, 양자화와 실행 위치는 현재 일반 데모 로그가
  자동 수집하지 않으므로 제출용 평가 원문 옆의 환경 기록으로 따로
  보존해야 합니다. 기록하지 않은 값을 실행 로그에 있다고 주장하지 않습니다.

자체 호스팅은 모델을 우리 환경에서 직접 실행한다는 뜻입니다. 제3자
상용 API에 계정으로 로그인하는 것은 자체 호스팅이 아닙니다.

## 외부 API 통합시험 예외

외부 상용 API는 `external_api_integration`이라는 별도 프로필에서 **모델
연동 기능을 시험할 때만** 사용합니다. 이 경로는 대회 기본 실행이나 장애
대체 경로가 아닙니다.

통합시험은 다음 조건을 모두 지킵니다.

- 사용자가 명시적으로 켜야 하며 기본값은 꺼짐입니다.
- 별도의 임시 JSONL을 사용하고 실제 `memory/memory.jsonl`을 열지
  않습니다.
- 공개 fixture 또는 인공 입력만 전송합니다.
- 사용자의 실제 기억, 개인정보, 비공개 문서와 비공개 소스 코드는
  전송하지 않습니다.
- API 키는 지정된 환경 변수에서만 읽습니다. 키 값, 계정 비밀번호,
  브라우저 세션을 CLI 인자·설정 파일·로그·기억·평가 산출물에 기록하지
  않습니다.
- API 오류 메시지와 응답 본문도 자격 증명이나 민감한 입력을 포함하지
  않도록 정리한 뒤 기록합니다.
- 공급자, 정확한 모델명, 시험 날짜, 네트워크 사용 여부를 남깁니다.
- 결과는 `contest_local_or_self_hosted` 결과와 분리하고 공식 시연
  성능·정확도·비용 집계에서 제외합니다.

이 예외는 외부 모델을 송련의 공식 두뇌로 인정하는 허가가 아니라, 송련이
모델 연동 프레임워크로서 정상적으로 연결되는지 확인하기 위한 좁은
시험 경계입니다.

통합시험에는 일반 웹 서비스 계정의 이메일·비밀번호나 로그인 세션이
아니라 공급자의 개발자 콘솔에서 별도로 발급한 API 키가 필요합니다. 예를
들어 기본 환경 변수 `OPENAI_API_KEY`를 현재 셸에 설정한 뒤 다음처럼
명시적으로 실행합니다.

```powershell
$env:OPENAI_API_KEY = "<개발자 콘솔에서 발급한 키>"
python -m demo `
  --external-api-integration `
  --external-api-base-url "https://provider.example/v1" `
  --external-api-model "provider/model-name" `
  "공개 또는 인공 입력으로 연결만 검사해 줘."
```

공급자 주소와 모델명은 해당 공급자의 공식 문서에 맞게 바꿉니다. 키를
다른 이름의 환경 변수에 넣었다면 `--external-api-key-env`에는 키 값이
아니라 그 **환경 변수 이름**만 전달합니다. 기본 실행은 폐기되는 임시
기억을 사용하며, 로그를 보존할 때도 `--memory .\.tmp\external-memory.jsonl`
같은 격리 경로를 지정합니다.

## Codex 계정 모델 체급 비교

`codex_account_integration`은 저장된 ChatGPT/Codex 로그인을 공식 Codex
Python SDK가 재사용하여 `gpt-5.6-sol`을 호출하는 별도 개발 시험입니다.
이는 API key를 쓰는 `external_api_integration`과 인증 방식만 다를 뿐,
대회 제출·시연·공식 성능 집계에는 포함되지 않는 외부 실행입니다.

- `--codex-account-integration`을 명시한 단발 실행만 허용합니다.
- 실제 `memory/memory.jsonl`을 거부하고 폐기되는 임시 로그를 씁니다.
- SDK에 토큰·이메일·브라우저 session을 전달하거나 저장하지 않고, 로컬에
  이미 저장된 Codex 인증은 SDK 자체가 처리합니다.
- 각 호출은 빈 임시 폴더의 ephemeral thread와 읽기 전용 sandbox에서
  실행하며 모든 승인을 거부합니다.
- 결과 trace에 shell, 파일 변경, MCP, 웹 검색, image, 하위 agent 같은
  부가 작업이 나타나면 그 모델 응답을 폐기합니다.
- Codex SDK는 순수 text model client가 아니라 agent runtime이므로, 이
  결과를 Ollama나 직접 API 결과와 같은 조건의 성능 비교로 주장하지
  않습니다.
- 심사 자료용 model-ceiling 실험은 `evals/model_ceiling_cases/`의 공개
  합성 fixture만 사용하고, 별도 evidence pack에서 `publishable: false`와
  `official_contest_score: false`를 강제합니다.

송련 전용 가상환경에서 선택 의존성을 설치한 뒤 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[codex]"
.\.venv\Scripts\python.exe -m demo `
  --codex-account-integration `
  --codex-account-model "gpt-5.6-sol" `
  --codex-reasoning-effort "medium" `
  "공개 또는 인공 입력으로 모델 체급 차이만 검사해 줘."
```

## 제출 전 확인표

- [ ] 시연 명령이 로컬 또는 자체 호스팅 Ollama만 호출한다.
- [ ] 네트워크를 끊어도 설치된 모델로 핵심 데모가 실행된다.
- [ ] `gemma4:26b` 태그와 모델 ID가 재현 기록에 남는다.
- [ ] 모델 출처·라이선스·양자화가 결과보고서 기술명세와 일치한다.
- [ ] 상용 API 자동 fallback 코드가 없다.
- [ ] 외부 API 통합시험 산출물이 공식 평가 집계에 섞이지 않는다.
- [ ] Codex 계정 통합시험 산출물이 공식 평가 집계에 섞이지 않는다.
- [ ] 저장소와 로그에 API 키·비밀번호·브라우저 세션이 없다.
- [ ] 실제 기억과 비공개 코드가 외부 API에 전달되지 않는다.
