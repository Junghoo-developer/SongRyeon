# 송련 코어 코드 학습 안내

이 문서는 Python을 막 배우는 사람이 송련을 **직접 읽고 고칠 수 있게 되는
순서**를 제시한다. 처음부터 `runtime/runner.py` 전체를 이해하려 하지 않는다.
작은 데이터 하나가 생성되고, 저장되고, 공개되고, 노드 사이를 이동하는
순서대로 범위를 넓힌다.

## 먼저 기억할 세 문장

1. 모델은 요청하거나 판단하지만 실제 실행 사실을 직접 만들지 않는다.
2. `memory.jsonl`은 원본이고, 함수가 반환한 공개 필드만 에이전트 시야다.
3. A는 절대진리가 아니라 런타임이 직접 관측·적용한 값이다.

예를 들어 파일에 `지구는 평평하다`라는 문자열이 실제로 있다면 다음을
구분한다.

- `그 파일에 그 문자열이 있었다`: 파일 도구와 코드가 확인할 수 있는 A
- `지구는 평평하다`: 문자열이 표현하는 주장으로서 R

따라서 송련의 핵심은 문장의 진리를 자동 판정하는 것이 아니라, 관측된
증거와 모델의 주장을 같은 권위로 섞지 않는 데 있다.

## 1단계: 원자 기록 하나

읽을 파일:

1. `memory/record.py`
2. `tests/memory/test_record.py`

볼 질문:

- 함수 인자 네 개가 일곱 필드로 어떻게 늘어나는가?
- `information_class`와 `code_verifiable`은 어떻게 대응하는가?
- 이 함수가 파일을 직접 열지 않는 이유는 무엇인가?

실행:

```powershell
python -m pytest -q tests/memory/test_record.py
```

연습:

- 테스트의 `information_type`만 다른 문자열로 바꾸고 결과를 예상한다.
- `information_class="unknown"`일 때 왜 조용히 저장하지 않는지 설명한다.

## 2단계: 원본 JSONL 저장

읽을 파일:

1. `memory/store.py`
2. `tests/memory/test_store.py`

볼 질문:

- JSON 배열이 아니라 한 줄에 JSON 객체 하나를 쓰는 이유는 무엇인가?
- 여러 기록을 한 번의 byte 묶음으로 쓰는 이유는 무엇인가?
- 쓰기가 실패했을 때 `original_size`로 돌아가는 이유는 무엇인가?

실행:

```powershell
python -m pytest -q tests/memory/test_store.py
```

여기까지 이해하면 `입력 → 7필드 딕셔너리 → JSONL 한 줄`을 이해한 것이다.

## 3단계: 원본과 에이전트 시야

읽을 파일:

1. `memory/settings.py`
2. `memory/agent_view.py`
3. `tests/memory/test_agent_view.py`

먼저 아래 세 함수만 따라간다.

```text
load_agent_memory
  최신 원자를 완전한 기록 단위로 선택
        ↓
freeze_agent_memory_floor
  가장 오래된 선택 원자의 내부 ID를 책갈피로 고정
        ↓
load_frozen_agent_memory
  책갈피부터 턴 중 새로 생긴 공개 기록까지 반환
```

볼 질문:

- 글자 예산에 걸린 원자를 반으로 자르는가?
- `memory_index`가 원본 일곱 필드에 저장되지 않는 이유는 무엇인가?
- 턴 도중 새 기록이 늘어도 가장 오래된 원자가 사라지지 않는 이유는 무엇인가?
- `tool_raw_*`, `model_raw_*`는 어디에서 걸러지는가?

실행:

```powershell
python -m pytest -q tests/memory/test_agent_view.py
```

## 4단계: 모델 선택과 코드 적용의 분리

읽을 파일:

1. `nodes/retention.py`
2. `tests/nodes/test_decisions.py`
3. `memory/tool_records.py`
4. `memory/tool_source.py`
5. `tests/memory/test_tool_retention.py`

핵심 흐름:

```text
도구 원문
  ↓
Node1이 full / excerpt / chunk / omit 중 하나를 요청(R)
  ↓
코드가 위치·ID·원본 출처를 검증
  ↓
코드가 숨김 원문을 그대로 복사(A)
```

볼 질문:

- 모델이 선택 본문을 직접 다시 작성하지 못하게 한 곳은 어디인가?
- 긴 문서에서 모델이 문자 위치 대신 `chunk_id`를 고르는 이유는 무엇인가?
- `strip()`이나 줄 번호 추가조차 하지 않는 이유는 무엇인가?

실행:

```powershell
python -m pytest -q tests/nodes/test_decisions.py
python -m pytest -q tests/memory/test_tool_retention.py
```

## 5단계: 유한한 노드 상태와 라우팅

읽을 파일:

1. `runtime/state.py`
2. `memory/gate_records.py`
3. `runtime/tool_flow.py`
4. `tests/runtime/test_tool_flow.py`
5. `runtime/gates.py`
6. `tests/runtime/test_gates.py`

볼 질문:

- 실패한 도구 요청도 횟수에 포함되는 이유는 무엇인가?
- 세 번째 도구 뒤 Node1이 또 도구를 원하면 누가 막는가?
- Node2의 첫 세 번 reject와 네 번째 reject는 어떻게 다른가?
- 네 번째 reject를 무시하는 것과 permit으로 바꾸는 것은 왜 다른가?

실행:

```powershell
python -m pytest -q tests/runtime/test_tool_flow.py
python -m pytest -q tests/runtime/test_gates.py
```

## 6단계: 모델 출력 계약

읽을 파일:

1. `nodes/schemas.py`
2. `nodes/parsing.py`
3. `llm/structured.py`
4. `tests/llm/test_structured.py`

볼 질문:

- JSON Schema와 Python parser를 둘 다 두는 이유는 무엇인가?
- Markdown 코드펜스와 중복 JSON key를 왜 거부하는가?
- 모델 출력 오류와 HTTP 전송 오류의 재시도 정책이 왜 다른가?
- 유효하지 않은 응답도 원본 로그에 남는가?

실행:

```powershell
python -m pytest -q tests/llm/test_structured.py
python -m pytest -q tests/nodes/test_parsing.py
```

## 7단계: 프롬프트와 전체 루프

읽을 파일:

1. `prompts/shared.py`
2. `prompts/node1.py`
3. `prompts/node2.py`
4. `prompts/node3.py`
5. `prompts/node4.py`
6. `runtime/node_calls.py`
7. `runtime/runner.py`

`runtime/node_calls.py`의 각 메서드는 아래 네 요소를 결합한다.

```text
프롬프트 생성기 + JSON Schema + parser + 출력 토큰 예산
```

그 다음 `runtime/runner.py`에서는 `current_node`의 변화만 먼저 표시하며
읽는다. 세부 함수로 들어갔다가 다시 돌아오는 방식보다 다음 경로를 종이에
한 번 적는 편이 쉽다.

```text
Node1 → Node2 검토 → Node3 → Node4 → final
   ↑ reject 1~3회        ↑ reject 1~3회
```

Node1은 사용자 요청에 필요한 증거를 모으고, Node2는 공개된 A가 현재 요청에
충분한지 검토한다. reject가 적용되면 Node1의 새 라운드가 시작된다.

실행:

```powershell
python -m pytest -q tests/runtime/test_runner.py
```

## 8단계: 실제 파일 도구와 CLI

마지막으로 아래를 읽는다.

1. `agent_tools/result.py`
2. `agent_tools/files.py`
3. `demo/cli.py`

파일 도구에서는 정상 동작보다 거부 조건을 먼저 찾는다.

- 프로젝트 루트 탈출
- 절대경로
- 심볼릭 링크 탈출
- 제외 폴더
- `.py` 이외 확장자
- 파일 크기 상한
- UTF-8이 아닌 파일

실행:

```powershell
python -m pytest -q tests/agent_tools/test_files.py
python -m pytest -q tests/demo/test_cli.py
```

## 코드를 직접 고칠 때의 작은 규칙

한 번에 한 책임만 바꾸고 그 폴더의 테스트부터 실행한다.

```text
변경 전: 관련 테스트를 읽고 현재 계약을 한 문장으로 적기
변경 중: 모델의 R 요청과 코드가 적용한 A를 구분하기
변경 후: 좁은 테스트 → 전체 테스트 순서로 실행하기
```

전체 검증:

```powershell
python -m pytest -q
```

막혔을 때는 함수 전체를 외우려 하지 말고 다음 네 가지를 적는다.

1. 입력 자료형
2. 반환 자료형
3. 이 함수가 바꾸는 상태나 파일
4. 실패할 때 발생시키는 예외

이 네 줄을 설명할 수 있으면 해당 함수의 뼈대는 이해한 것이다.
