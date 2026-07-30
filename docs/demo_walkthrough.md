# 송련 네 노드 데모 읽는 순서

이 문서는 `python -m demo`가 사용자 입력 하나를 어떻게 처리하는지 코드
순서대로 따라가기 위한 학습 안내서다. 기본 데모는 로컬 또는 자체 호스팅
Ollama의 오픈웨이트 `gemma4:26b`를 사용한다. 외부 API key는 필요 없지만,
Ollama 설치와 모델 다운로드는 먼저 해야 한다.

## 가장 먼저 실행하기

먼저 README의 `실행 방법`에 따라 Ollama, `gemma4:26b`, 가상환경을
준비한다. 깨끗한 복제부터 PowerShell·Bash별 전체 명령이 필요하면
[`reproducibility.md`](reproducibility.md)를 따른다. 준비가 끝나면 프로젝트
폴더에서 다음 명령을 실행한다.

```powershell
python -m demo --memory .\tmp\demo-memory.jsonl `
  "nodes/review.py를 실제 도구로 읽고 역할을 세 문장으로 설명해 줘."
```

`gemma4:26b`가 기본값이므로 `--model`은 생략했다. editable 설치로 생성된
`songryeon` 명령도 같은 CLI다.

```powershell
songryeon --memory .\tmp\demo-memory.jsonl `
  "nodes/review.py를 실제 도구로 읽고 역할을 세 문장으로 설명해 줘."
```

`songryeon`을 찾지 못하면 가상환경을 다시 활성화하거나 `python -m demo`를
사용한다. 질문을 생략하면 여러 번 입력할 수 있는 대화형 화면이 열린다.

```powershell
python -m demo --memory .\tmp\demo-memory.jsonl
```

`--memory`를 생략한 로컬 실행은 실제 원본인 `memory/memory.jsonl`에
기록한다. 따라서 학습·시험 중에는 위처럼 격리된 경로를 권장한다.

Linux Bash에서는 같은 명령을 다음처럼 실행한다.

```bash
python -m demo --memory ./tmp/demo-memory.jsonl \
  "nodes/review.py를 실제 도구로 읽고 역할을 세 문장으로 설명해 줘."
```

`qwen3:14b`는 이전 기본값이나 자동 대체 모델이 아니라 비교평가 기준선이다.
기준선을 재현할 때만 `ollama pull qwen3:14b` 후
`--model qwen3:14b`를 명시한다.

현재 모델·서버·컨텍스트·제한 시간 설정은 각각 `--model`, `--base-url`,
`--num-ctx`, `--timeout-seconds`, `--keep-alive`로 바꿀 수 있다. 정확한
기본값은 `python -m demo --help`에서 확인한다.

## 한 턴의 전체 흐름

```text
사용자 입력
  ↓
Node1: 필요한 Python 파일을 최대 3회 읽음
  ↓
Node1: 짧은 원문은 full / excerpt / omit, 긴 원문은 chunk / omit으로 선택
  ↓ 전부 omit이면
Node1: 후보 하나를 골라 full / excerpt로 최종 복구
  ↓
Node2: 선택된 증거가 충분한지 permit / reject
  ↓ permit
Node3: 답변 후보 작성
  ↓
Node4: 답변이 A를 왜곡했는지 permit / reject
  ↓ permit
최종 답변
```

Node2가 reject하면 Node1의 새 라운드로 돌아간다. Node4가 reject하면
Node3가 답변을 다시 쓴다. 두 검토 노드의 처음 세 reject만 적용되고 네 번째
reject는 원본에 기록한 뒤 코드가 한도를 초과한 reject로 처리한다. 이 경우
실행을 끝내기 위해 다음 단계로 진행하지만 permit으로 바꾸지는 않는다.
최종 화면에는 Node2라면 증거 검증 미완료, Node4라면 검열 permit 미획득
경고가 명시된다.

## 파일을 읽는 추천 순서

### 1. 화면 입출력

`demo/cli.py`

- Ollama가 켜져 있고 모델이 설치됐는지 확인한다.
- 사용자의 질문을 받는다.
- 진행 상황과 최종 답변을 출력한다.
- 노드 판단이나 라우팅 규칙은 이 파일에 넣지 않는다.

### 2. 전체 노드 이동

`runtime/runner.py`

- 현재 노드가 Node1·2·3·4 중 어디인지 관리한다.
- 기존 도구 실행과 반려 횟수 함수를 순서대로 호출한다.
- 모델 답변을 기억에서 다시 검색하지 않고, 현재 Node3 답변 변수를 그대로
  최종 반환한다.

### 3. 각 노드의 모델 호출

`runtime/node_calls.py`

- 턴 시작 시 최신 8,000자에서 가장 오래된 공개 원자를 기준점으로 고정한다.
- 모든 노드는 턴이 끝날 때까지 그 기준점 이후의 공개 원자를 함께 본다.
- 새 기록이 생겨 8,000자를 넘어도 같은 턴 안에서는 기준점을 옮기지 않는다.
- 현재 사용자 요청은 오래된 기억에 밀려나도 잃지 않도록 별도로 함께 보낸다.
- 원본 줄 번호에서 만든 `memory_index`와 현재 턴 시작 순번도 함께 보낸다.
- 직전 사용자 입력 하나는 `더`, `계속` 같은 후속 요청 해석용으로 고정한다.
- 도구 원문은 `ask_node1_after_tool()`에만 전달된다.
- 전부 omit 복구에서는 후보 목록에 원문을 넣지 않고, Node1이 고른 원문
  하나만 `ask_node1_recovery_retention()`에 다시 전달한다.

### 4. 노드별 지침

`prompts/shared.py`, `prompts/node1.py`부터 `prompts/node4.py`

- 공통 A/R 규칙과 각 노드의 최소 역할을 읽을 수 있다.
- Node2는 증거를 고르지 않고 충분성만 검토한다.
- Node4는 문체가 아니라 A 왜곡과 R 세탁을 검사한다.

### 5. 모델 출력 계약

`nodes/schemas.py`, `nodes/parsing.py`

- Ollama에 전달하는 JSON Schema가 있다.
- parser는 누락된 key, 추가 key, 형변환, 잘못된 excerpt 범위를 거부한다.
- 최종 복구 parser는 `omit`을 거부한다. 짧은 원문은 `full/excerpt`,
  긴 원문은 코드가 만든 `chunk_id` 하나만 허용한다.
- 선택 본문은 최대 2,000자, Node3 답변은 최대 2,400자다.

### 6. Ollama와 검증 재요청

`llm/client.py`, `llm/structured.py`

- `client.py`는 HTTP 전송만 담당한다.
- `structured.py`는 JSON을 엄격히 검사한다.
- 잘못된 출력은 같은 노드에 오류를 알려 최대 세 번 다시 요청한다.
- 세 번 모두 실패하면 `NodeOutputError`로 중단하며 임의의 permit이나
  기본 답변으로 바꾸지 않는다.
- 연결 실패와 제한 시간 초과는 자동 재시도하지 않는다.

### 7. 원본 기록

`memory/conversation_records.py`, `memory/model_records.py`

- 사용자 입력과 Node3 답변 내용은 R이다.
- 누가 말했는지와 코드가 고른 최종 답변 ID는 A다.
- 모든 모델 prompt·response는 `model_raw_*`로 원본에 보존하지만 일반
  에이전트 시야에서는 숨긴다.

## 현재 데모의 의도적인 한계

- Node1 도구는 Python 파일 목록과 읽기뿐이다.
- 한 파일은 데모 실행에서 최대 16 KiB까지만 읽는다.
- 지식 DB 검색, 웹 검색, 파일 수정 도구는 없다.
- 기억 압축은 없다.
- 턴 중 시야 기준점은 움직이지 않으므로 긴 턴은 최초 8,000자를 넘어 자란다.
  현재는 모델 문맥 한도에 닿기 전 별도 압축이나 사전 중단을 하지 않는다.
- 여러 프로세스가 같은 기억을 동시에 쓰는 파일 잠금은 없다.

이 한계는 실패를 숨기기 위한 임시 우회가 아니다. 첫 데모에서 실제로 검증하는
범위를 작게 고정한 것이다. 다음 기능은 현재 흐름을 직접 읽고 테스트한 뒤
하나씩 추가한다.
