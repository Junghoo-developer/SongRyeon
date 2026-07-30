# 최소 에이전트 루프 설명

이 문서는 현재 구현된 범위와 아직 구현하지 않은 범위를 구분하기 위한
학습용 설명입니다.

## 지금 실제로 되는 것

```text
Node1 도구 요청
  ↓
코드가 다음 도구 사용 횟수를 계산
  ↓
허용된 파일 도구 실행
  ↓
도구 원문을 tool_raw_* 절대정보로 먼저 저장
  ↓
저장 성공 후 도구 사용 횟수를 1 증가
  ↓
Node1이 이번 호출에서만 원문을 직접 검토
  ↓
짧은 원문: full / excerpt / omit
긴 원문: 결정론적 chunk_id / omit
+ 짧은 review + 다음 행동 반환
  ↓
코드가 원문을 정확히 복사하고 공개 기록 저장
  ↓
Node2 직전 성공 원문이 전부 omit이면 Node1이 하나를 최종 재선택
  ↓
Node1 계속 또는 Node2로 라우팅
```

결정론적 테스트는 Node1·Node2·Node4의 결정을 직접 만들어 코드 규칙을
검증합니다. 실제 기본 데모에서는 로컬 또는 자체 호스팅 Ollama의
`gemma4:26b`가 같은 계약의 JSON을 반환합니다. `qwen3:14b`는 비교평가용
기준선이며 자동 대체 모델이 아닙니다. 어느 모델을 쓰든 도구 실행, 저장,
횟수 제한과 라우팅은 Python 코드가 담당합니다.

## 파일별 책임

- `agent_tools/files.py`
  - Python 파일 상대경로 목록
  - UTF-8 Python 파일 원문 열람
  - 프로젝트 밖 경로, 캐시, 가상환경, 외부 문서 폴더 차단
  - 파일당 64 KiB 상한

- `nodes/retention.py`
  - 짧은 원문의 `full / excerpt / omit` 형식 검사
  - 긴 원문의 결정론적 `chunk_id / omit` 형식 검사
  - excerpt 또는 청크 범위 재계산과 정확한 원문 복사

- `nodes/actions.py`
  - Node1의 `use_tool / route_node2` 형식 검사

- `nodes/recovery.py`
  - 전부 omit된 후보 중 Node1이 고른 1부터 시작하는 후보 번호 검사

- `nodes/review.py`
  - Node2·Node4의 `permit / reject` 형식 검사

- `memory/tool_records.py`
  - 실제 도구 행동과 원문 저장
  - Node1의 상대 판단과 코드가 적용한 절대 사실 저장

- `memory/tool_source.py`
  - 숨김 원문의 ID·turn·A 분류와 중복 선택 재검사

- `memory/gate_records.py`
  - Node1의 다음 행동과 실제 라우팅 결과 저장
  - Node2·Node4 판단과 실제 라우팅 결과 저장

- `memory/agent_view.py`
  - 원본 줄 번호에서 공개 시야 전용 `memory_index` 파생
  - 턴 시작 시 최신 8,000자의 가장 오래된 공개 원자 ID 고정
  - 현재 턴 시작 순번과 직전 사용자 입력 하나를 별도로 고정
  - 같은 턴에서는 그 기준점부터 새 공개 원자까지 빠짐없이 유지
  - 숨김 원문은 기준점 계산과 에이전트 시야에서 모두 제외

- `runtime/state.py`
  - 사용자 턴 ID, Node1 라운드와 각 노드 카운터

- `runtime/tool_flow.py`
  - Node1 라운드당 도구 3회 제한
  - 도구 원문 저장 후 짧은 원문 선택 또는 긴 원문 청크 선택 적용

- `runtime/retention_recovery.py`
  - Node2로 가기 직전 현재 라운드의 성공 원문이 전부 omit인지 코드로 검사
  - 사용자 턴당 한 번만 기존 omit 원문 하나를 full/excerpt로 복구

- `runtime/gates.py`
  - Node2와 Node4의 반려 횟수 각각 3회 제한
  - Node2 반려 시 새 Node1 라운드 시작

- `runtime/node_calls.py`
  - 한 턴의 모든 노드가 같은 고정 시야 기준점을 사용
  - 턴 중 기록이 늘어도 앞 노드가 본 공개 원자를 뒤 노드에서 제거하지 않음

실패한 도구 요청도 `runtime/tool_flow.py`에서 도구 횟수에 포함합니다.
`workflow_records.py`와 `runtime/loop.py`는 구조 분리 전 import를 위한 얇은
호환 파일이며 새 로직을 추가하지 않습니다.

## 원문 선택 규칙

Node1은 선택 본문을 새로 작성하지 않습니다.

```text
full
→ 코드가 원문 전체를 그대로 복사

excerpt
→ Node1은 start와 end만 반환
→ 코드가 raw_text[start:end]를 그대로 복사

chunk
→ 2,000자를 넘는 원문을 코드가 줄 경계 우선으로 나눔
→ Node1은 표시된 chunk_id 하나만 반환
→ 코드가 같은 규칙으로 범위를 다시 계산해 원문을 그대로 복사

omit
→ 공개 본문을 만들지 않음
```

짧은 원문의 excerpt 위치는 UTF-8 byte 위치가 아니라 Python 문자열의 문자
위치입니다. 긴 원문에서는 모델이 문자 위치를 계산하지 않습니다. 코드는
`strip()`, 줄번호 추가, 줄바꿈 변경, 유니코드 정규화를 하지 않습니다.

선택 본문과 관련 기록 전체가 8,000자 시야 예산을 넘으면 자동으로 자르지
않고 결정을 거부합니다. Node1이 더 작은 excerpt, 청크 또는 omit을 선택해야
합니다.

저장 함수는 전달받은 본문을 그대로 A로 믿지 않습니다. 숨김 로그의
`information_id`와 `turn_id`를 다시 확인해 원문을 읽고, 그 저장된 원문에서
코드가 직접 선택합니다. 다른 기억 파일의 원문이나 가짜 ID는 거부합니다.
같은 도구 결과에 일반 보존 결정을 두 번 적용하는 것도 거부합니다. 유일한
예외는 코드가 현재 라운드의 성공 원문이 전부 omit됐음을 확인한 경우입니다.
이때만 기존 `omit` 기록을 수정하지 않고 Node1이 고른 원문 하나를 짧으면
`full/excerpt`, 길면 `chunk_id`로 한 번 추가합니다.

## 전부 omit 복구

Node1이 Node2로 가려는 순간 현재 라운드에 성공한 도구 결과가 있지만
`tool_result_content`가 하나도 없다면 코드가 복구 절차를 시작합니다.

```text
성공한 도구 원문이 모두 omit
→ 코드가 all-omit 상태를 A로 기록
→ Node1이 도구 정보와 이전 review를 보고 후보 번호 하나 선택
→ 선택한 원문 하나만 Node1에게 다시 공개
→ 짧은 원문은 full/excerpt, 긴 원문은 chunk_id 하나만 선택
→ 코드가 숨김 원문을 ID·turn으로 재검증해 정확히 복사
→ Node2
```

복구는 새 도구 호출이 아니므로 도구 횟수를 늘리지 않습니다. 후보 선택과
보존 review는 R이고, 코드가 감지한 all-omit 상태·적용 방식·정확한 복사
본문은 A입니다. 최초 `omit` 요청과 적용 기록은 덮어쓰지 않고 그대로 남습니다.

## Node1의 다음 행동

초기 Node1 출력은 `Node1Action`, 도구 결과를 본 뒤의 출력은
`Node1ToolDecision`으로 표현합니다.

```text
Node1Action
├─ use_tool
│  ├─ tool_name
│  ├─ arguments
│  └─ 짧은 reason
└─ route_node2
   └─ 짧은 reason

Node1ToolDecision
├─ RetentionDecision
└─ Node1Action
```

Node1이 요청한 행동과 이유는 R이며, 코드가 실제로 허용하거나 도구 상한
때문에 Node2로 강제 이동시킨 결과는 `runtime_route` A로 따로 기록합니다.

## A/R 기록

| 기록 | 분류 | 일반 시야 |
|---|---|---|
| 실제 실행 노드·도구·인자 | A | 공개 |
| 실제 도구 성공 여부와 횟수 | A | 공개 |
| `tool_raw_*` 도구 원문 | A | 숨김 |
| Node1 review와 보존 요청 | R | 공개 |
| 코드가 적용한 보존 방식 | A | 공개 |
| 코드가 복사한 선택 본문 | A | 공개 |
| all-omit 감지와 복구 적용 | A | 공개 |
| Node1의 복구 요청과 review | R | 공개 |
| Node1의 다음 행동과 이유 | R | 공개 |
| 코드가 적용한 실제 라우팅 | A | 공개 |
| Node2·Node4 결정과 이유 | R | 공개 |
| 코드가 적용한 검토 라우팅 | A | 공개 |

Node1 review는 다음 노드가 본문 없이도 판단을 이어갈 수 있도록 공개합니다.
대신 원문 전체를 review에 복사하는 일을 줄이기 위해 최대 500자로 제한합니다.
이 review는 어디까지나 상대정보이며, 정확한 원문 증거 역할을 하지 않습니다.
따라서 `omit`은 본문 A를 숨긴다는 뜻이지, Node1의 R 설명까지 비밀로 만든다는
뜻은 아닙니다.

## 횟수와 라우팅

Node1 도구 3회는 사용자 턴 전체가 아니라 **한 Node1 라운드** 기준입니다.

```text
Node1이 직접 route 선택
→ Node2

Node1이 세 번째 도구 사용
→ 다음 요청이 use_tool이어도 Node2

Node2 직전 현재 라운드의 성공 원문이 전부 omit
→ 사용자 턴당 한 번 Node1 최종 보존 재선택
→ 복구 뒤 Node2

Node2 permit
→ Node3

Node2 reject 1~3회
→ Node1 새 라운드, 라운드 도구 횟수 0으로 초기화

Node2 네 번째 reject
→ 시스템이 reject와 한도 초과를 기록하고 Node3
→ CLI가 증거 검증 미완료 경고 표시

Node4 permit
→ 최종 답변

Node4 reject 1~3회
→ Node3 재작성

Node4 네 번째 reject
→ 시스템이 reject와 한도 초과를 기록하고 최신 답변 반환
→ CLI가 검열 permit 미획득 경고 표시
```

따라서 Node2가 세 번 모두 반려하더라도 한 사용자 턴에서 실행 가능한 도구는
초기 라운드 3회와 보완 라운드 세 번의 각 3회를 합친 최대 12회입니다.
Node2와 Node4의 반려 카운터는 서로 독립적입니다. 한도 초과 뒤 진행은
검증 성공이나 permit이 아니며, `DemoTurnResult`의 각 `*_limit_exhausted` 값과
CLI 경고로 구분됩니다.

## 저장 실패

여러 원자 기록은 먼저 JSONL byte 묶음 하나로 만들어 한 번에 씁니다.
짧은 write나 디스크 오류가 발생하면 쓰기 전 파일 크기로 되돌립니다.
원래 크기 복구까지 실패하면 `MemoryLogCorruptionError`를 발생시킵니다.

현재는 로컬 단일 프로세스 데모를 전제로 합니다. 여러 프로세스가 동시에
기억을 쓸 때 필요한 파일 잠금과 중앙 writer는 이후 범위입니다.
도구 원문 로그 저장이 실패하면 카운터도 증가시키지 않고 해당 호출을
예외로 중단합니다.

## 현재 연결된 것

- 로컬·자체 호스팅 Ollama와 기본 `gemma4:26b` 구조화 출력
- 별도로 모델을 지정하는 `qwen3:14b` 비교 기준선
- Node1·Node2·Node3·Node4 최소 프롬프트
- 실제 한 턴을 끝까지 도는 제한된 while 루프
- 사용자 입력, Node3 답변과 숨김 모델 입출력 원본 기록

자세한 설치·실행·학습 순서는 `docs/demo_walkthrough.md`에 있습니다.

## 아직 없는 것

- 과거 기억·외부 DB 검색 도구
- 기억 압축
- Python 이외 파일 도구와 수정 도구
- 여러 writer의 동시 기록 잠금
